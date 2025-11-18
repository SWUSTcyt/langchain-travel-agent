
"""MCP 工具加载和 LangChain 工具包装"""

import asyncio
import logging
import threading
from concurrent.futures import Future
from typing import List, Iterable, Tuple

import anyio
from langchain_core.tools import Tool, StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import AMAP_MCP_URL, Config

logger = logging.getLogger(__name__)

# 全局缓存：工具列表 / 工具名（按长度降序，用于最长前缀匹配）
_GLOBAL_TOOLS: List = []
_TOOL_NAME_SET: Tuple[str, ...] | None = None

# 异步事件循环线程（用于 MCP 异步工具）
_ASYNC_LOOP: asyncio.AbstractEventLoop | None = None
_ASYNC_LOOP_THREAD: threading.Thread | None = None
_ASYNC_LOOP_LOCK = threading.Lock()


# ======== 异步工具 -> 同步包装 相关 ========

def _ensure_async_loop() -> asyncio.AbstractEventLoop | None:
    """确保常驻事件循环已启动（线程安全），失败则返回 None"""
    global _ASYNC_LOOP, _ASYNC_LOOP_THREAD

    if _ASYNC_LOOP and _ASYNC_LOOP.is_running():
        return _ASYNC_LOOP

    with _ASYNC_LOOP_LOCK:
        if _ASYNC_LOOP and _ASYNC_LOOP.is_running():
            return _ASYNC_LOOP

        try:
            loop = asyncio.new_event_loop()
        except Exception as e:
            logger.warning("[AsyncLoop] 创建新事件循环失败，将回退到 anyio.run()：%s", e)
            return None

        def _runner(lp: asyncio.AbstractEventLoop):
            asyncio.set_event_loop(lp)
            lp.run_forever()

        thread = threading.Thread(
            target=_runner,
            args=(loop,),
            daemon=True,
            name="AsyncToolLoop",
        )
        thread.start()
        _ASYNC_LOOP = loop
        _ASYNC_LOOP_THREAD = thread
        logger.info("[AsyncLoop] 常驻事件循环线程已启动")
        return _ASYNC_LOOP


def _run_coroutine_sync(coro_func, *args, **kwargs):
    """在常驻事件循环上同步执行协程函数；若失败则回退到 anyio.run"""
    loop = _ensure_async_loop()
    if loop:
        try:
            fut: Future = asyncio.run_coroutine_threadsafe(
                coro_func(*args, **kwargs), loop
            )
            return fut.result(timeout=Config.ASYNC_TOOL_TIMEOUT)
        except Exception as e:
            logger.warning(
                "[AsyncLoop] 执行协程失败/超时，回退到 anyio.run()：%s", e
            )

    async def _runner():
        return await coro_func(*args, **kwargs)

    return anyio.run(_runner)


def wrap_async_tool_to_sync(t):
    """把 MCP 异步工具 t 包成同步 LangChain Tool/StructuredTool

    - 若工具定义 args_schema -> StructuredTool（kwargs 形态）
    - 否则 -> Tool（单一入参）
    """
    # 已有同步 func，直接返回
    if getattr(t, "func", None):
        return t

    name = getattr(t, "name", "tool")
    desc = getattr(t, "description", "") or ""
    args_schema = getattr(t, "args_schema", None)

    coroutine = getattr(t, "coroutine", None)

    # 情况 1：没有 coroutine，用 ainvoke 兜底
    if not coroutine:
        if hasattr(t, "ainvoke"):
            if args_schema is not None:

                def _sync(**kwargs):
                    return _run_coroutine_sync(t.ainvoke, kwargs)

                return StructuredTool.from_function(
                    func=_sync,
                    name=name,
                    description=desc,
                    args_schema=args_schema,
                )

            else:

                def _sync(tool_input):
                    return _run_coroutine_sync(t.ainvoke, tool_input)

                return Tool.from_function(
                    func=_sync,
                    name=name,
                    description=desc,
                )

        # 没有 coroutine / ainvoke：原样返回
        return t

    # 情况 2：有 coroutine
    if args_schema is not None:

        def _sync(**kwargs):
            return _run_coroutine_sync(coroutine, **kwargs)

        return StructuredTool.from_function(
            func=_sync,
            name=name,
            description=desc,
            args_schema=args_schema,
        )

    else:

        def _sync(tool_input):
            return _run_coroutine_sync(coroutine, tool_input)

        return Tool.from_function(
            func=_sync,
            name=name,
            description=desc,
        )


# ======== MCP 客户端与工具初始化 ========

def init_mcp_client() -> MultiServerMCPClient:
    """初始化 MCP MultiServer 客户端"""
    if not AMAP_MCP_URL:
        raise RuntimeError("AMAP_MCP_URL 未配置，请检查 .env 或环境变量")

    client = MultiServerMCPClient(
        {
            "amap-maps": {
                "transport": "sse",
                "url": AMAP_MCP_URL,
            }
        }
    )
    return client


def load_tools() -> List:
    """拉取 MCP 工具并进行同步包装 & 预热"""
    global _GLOBAL_TOOLS, _TOOL_NAME_SET

    client = init_mcp_client()
    raw_tools = asyncio.run(client.get_tools())

    tools = [wrap_async_tool_to_sync(t) for t in raw_tools]
    _GLOBAL_TOOLS = tools
    _TOOL_NAME_SET = None  # 下次使用时重新构建

    logger.info("[初始化] 已加载 MCP 工具：%d 个", len(_GLOBAL_TOOLS))

    # 预热：尝试调用一次天气工具，减少首次延迟
    try:
        for tool in tools:
            if "weather" in tool.name.lower():
                try:
                    tool.run({"city": "北京"})
                    logger.info("[预热] MCP 工具 '%s' 预热完成", tool.name)
                    break
                except Exception as e:
                    logger.debug("[预热] 工具 '%s' 预热失败（忽略）：%s", tool.name, e)
    except Exception as e:
        logger.debug("[预热] MCP 预热异常（忽略）：%s", e)

    # 调试：打印工具列表
    print("=" * 60)
    print("已加载的工具列表：")
    for i, tool in enumerate(tools, 1):
        print(f"  {i}. {tool.name}")
    print("=" * 60)

    return tools


# ======== 对外提供的工具查询 API ========

def get_global_tools() -> List:
    """获取全局工具列表（给 agent / 中间件使用）"""
    return _GLOBAL_TOOLS or []


def get_tool_names_sorted() -> Iterable[str]:
    """获取排序后的工具名列表（按长度降序，最长前缀优先）"""
    global _TOOL_NAME_SET
    if _TOOL_NAME_SET is None and _GLOBAL_TOOLS:
        _TOOL_NAME_SET = tuple(
            sorted(
                [t.name for t in _GLOBAL_TOOLS if hasattr(t, "name")],
                key=len,
                reverse=True,
            )
        )
    return _TOOL_NAME_SET or ()
