"""LangChain Agent 中间件集合

- before_model 中间件
- wrap_model_call 中间件
- wrap_tool_call 中间件
- after_model 中间件
"""

import logging
import re
from typing import Callable

from langchain.agents.middleware import (
    AgentState,
    ModelRequest,
    ModelResponse,
    before_model,
    after_model,
    wrap_model_call,
    wrap_tool_call,
)
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    BaseMessage,
)

from config import Config
from tools import get_tool_names_sorted, get_global_tools

logger = logging.getLogger(__name__)

# 模块级缓存：存储当前轮次的目标城市（供 wrap_tool_call 中间件使用）
_target_cities_cache: set = set()
_original_input_cache: str = ""


# === 工具函数 ===

def msg_is_human(m) -> bool:
    """兼容 BaseMessage / dict 的 human 判断"""
    try:
        if isinstance(m, BaseMessage):
            t = getattr(m, "type", None) or getattr(m, "role", None)
            return t == "human"
        if isinstance(m, dict):
            r = (m.get("role") or "").lower()
            return r in ("user", "human")
    except Exception:
        pass
    return False


def msg_text(m) -> str:
    """统一抽取消息文本（content 可能是 str 或 list）"""
    if isinstance(m, BaseMessage):
        c = getattr(m, "content", "")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            parts = []
            for p in c:
                if isinstance(p, dict):
                    if p.get("type") == "text" and "text" in p:
                        parts.append(str(p["text"]))
                    elif "text" in p:
                        parts.append(str(p["text"]))
                elif isinstance(p, str):
                    parts.append(p)
            return "\n".join(parts)
        return str(c or "")

    if isinstance(m, dict):
        c = m.get("content", "")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            parts = []
            for p in c:
                if isinstance(p, dict) and "text" in p:
                    parts.append(str(p["text"]))
                elif isinstance(p, str):
                    parts.append(p)
            return "\n".join(parts)
        return str(c or "")

    return ""


# 城市名称正则（可扩展）
CITY_REGEX = (
    r"(?:北京|上海|杭州|苏州|成都|重庆|广州|深圳|西安|南京|武汉|长沙|青岛|厦门|天津|"
    r"昆明|大连|合肥|沈阳|哈尔滨|长春|石家庄|太原|郑州|济南|南昌|福州|南宁|海口|贵阳|银川|"
    r"乌鲁木齐|拉萨|西宁)"
)


def extract_cities(text: str) -> list[str]:
    hits = re.findall(CITY_REGEX, text or "", flags=re.U)
    # 去重保序
    return list(dict.fromkeys(hits))


def _ensure_system_first_in_messages(messages: list) -> list:
    """确保仅保留首个 SystemMessage 且置顶"""
    sys_first = None
    normalized = []
    for m in messages:
        if isinstance(m, SystemMessage):
            if sys_first is None:
                sys_first = m
            continue
        if isinstance(m, dict) and (m.get("role") or "").lower() == "system":
            if sys_first is None:
                sys_first = SystemMessage(content=m.get("content", "") or "")
            continue
        normalized.append(m)
    if sys_first is None:
        return messages
    return [sys_first] + normalized


# === before_model 中间件 ===

@before_model
def pin_cities_and_adcodes(state: AgentState, runtime) -> dict | None:
    """每轮基于本轮 human 解析城市，写入 runtime.state，并注入 system 提示"""
    query = ""
    cities: list[str] = []

    state_keys = list(state.keys()) if isinstance(state, dict) else []
    all_msgs = state.get("messages", []) if isinstance(state, dict) else []

    # 方式1：messages 中最后一条 human
    human_msgs = [m for m in all_msgs if msg_is_human(m) or isinstance(m, HumanMessage)]
    if human_msgs:
        query = msg_text(human_msgs[-1]) or ""

    # 方式2：state["input"]
    if not query and isinstance(state, dict) and "input" in state:
        query = str(state["input"] or "")

    # 方式3：runtime.state["__original_input__"]
    if not query:
        try:
            query = (runtime.state.get("__original_input__", "") or "").strip()
        except Exception:
            pass

    # 提取城市
    cities = extract_cities(query) if query else []

    # 写入模块级缓存
    global _target_cities_cache, _original_input_cache
    _target_cities_cache = set(cities)
    _original_input_cache = query

    logger.info(
        "[PinCities] 提取城市: %s",
        cities if cities else "(未提取到)",
    )

    if cities:
        city_tips = (
            f"\n【强制约束】本轮用户指定城市：{', '.join(cities)}。"
            f"仅在这些城市范围内规划；所有 MCP 工具调用必须携带匹配的 city/cityd。"
            f"禁止使用其他城市的 adcode 或坐标；若出现其他城市名，将被视为错误并强制重写。"
        )
    else:
        city_tips = "\n【强制约束】请从用户问题中判断目标城市；禁止跨城或引入未出现的城市。"

    messages_info = (
        f"messages数量：{len(state.get('messages', []))}"
        if "messages" in state
        else "无messages"
    )
    first_msg_preview = ""
    try:
        if all_msgs:
            first_txt = msg_text(all_msgs[0])
            first_msg_preview = (
                f"；首条消息预览：{first_txt[:50] if first_txt else '(空)'}"
            )
    except Exception:
        pass

    debug_info = (
        f"\n【DEBUG】原始查询：{query[:100] if query else '(空)'}；"
        f"提取城市：{', '.join(cities) if cities else '(未提取到)'}；"
        f"state键：{state_keys[:5] if state_keys else 'N/A'}；"
        f"{messages_info}{first_msg_preview}"
    )

    sys_msg = SystemMessage(
        content=(
            "你是旅行规划助手。需要本地信息时优先使用 MCP(amap-maps) 的工具："
            "maps_text_search（搜索POI）/ maps_direction_*（路线规划）/ maps_weather（天气查询）。"
            "风格：\"轻松不赶\"；"
            "输出包含可验证的检索要点（如POI名、路线段、adcode等）。"
            "\n【并行调用策略】强烈建议在同一轮中并行调用多个工具以提升效率："
            "\n- 示例：同时调用 maps_text_search（获取景点）+ maps_direction_driving（规划路线）+ maps_weather（查询天气）"
            "\n- 优势：一次性收集完整信息，减少往返轮次"
            "\n【停止条件-必须遵守】满足以下任一条件时，必须立即停止调用工具，直接给出最终答案："
            "\n1. 已获取关键信息：目标城市、2-3个POI、基本路线信息"
            f"\n2. 工具调用达到{Config.MAX_TOOL_ROUNDS}回合上限（严格限制，因启用并行调用）"
            "\n3. 收到\"强制停止\"提示"
            "\n【执行要求】达到停止条件后，必须直接输出文本答案，禁止继续调用工具。若信息不足，说明\"仍需补充的信息\"。"
            "\n【参数要求】调用地图工具时，必须传入 city 参数（如 city=\"成都\"），否则工具会报错。"
            + city_tips
            + debug_info
        )
    )

    new_messages = [sys_msg] + [
        m
        for m in state["messages"]
        if not isinstance(m, SystemMessage)
        and not (isinstance(m, dict) and (m.get("role") or "").lower() == "system")
    ]
    return {"messages": new_messages}


@before_model
def ensure_single_system_first(state: AgentState, runtime) -> dict | None:
    """确保仅有一个 SystemMessage 且在首位"""
    try:
        msgs = list(state.get("messages", []))
        if not msgs:
            return None

        sys_first = None
        normalized = []

        for m in msgs:
            if isinstance(m, SystemMessage):
                if sys_first is None:
                    sys_first = m
                continue

            if isinstance(m, dict) and (m.get("role") or "").lower() == "system":
                if sys_first is None:
                    sys_first = SystemMessage(content=m.get("content", "") or "")
                continue

            normalized.append(m)

        if sys_first is None:
            return {"messages": normalized}

        return {"messages": [sys_first] + normalized}
    except Exception:
        return None


@before_model
def inject_budget_status(state: AgentState, runtime) -> dict | None:
    """在模型调用前检查工具预算，并注入预算提示"""
    try:
        tool_rounds = runtime.state.get("tool_rounds", 0)

        runtime.state["_tools_in_round"] = set()
        logger.info(
            "[Budget] 模型调用前：已完成 %d/%d 轮，清空本轮工具集合",
            tool_rounds,
            Config.MAX_TOOL_ROUNDS,
        )

        budget_tip = ""
        if tool_rounds >= Config.MAX_TOOL_ROUNDS:
            budget_tip = (
                f"\n【强制停止】工具预算已耗尽（{tool_rounds}/{Config.MAX_TOOL_ROUNDS}）。"
                "禁止再调用任何工具！立即基于已知信息给出最终答案。"
            )

        if budget_tip:
            msgs = list(state["messages"])
            system_msgs = [m for m in msgs if isinstance(m, SystemMessage)]
            other_msgs = [
                m
                for m in msgs
                if not isinstance(m, SystemMessage)
                and not (isinstance(m, dict) and (m.get("role") or "").lower() == "system")
            ]
            if system_msgs:
                new_system = SystemMessage(content=system_msgs[0].content + budget_tip)
                return {"messages": [new_system] + other_msgs}
    except Exception:
        pass

    return None


# === wrap_tool_call 中间件 ===

@wrap_tool_call
def track_tool_budget(req, handler):
    """追踪工具调用轮次并在超限时阻止执行（并行调用同一轮只计一次）"""
    try:
        if hasattr(req, "runtime") and hasattr(req.runtime, "state"):
            current_round = req.runtime.state.get("tool_rounds", 0)
            tools_in_current_round = req.runtime.state.get("_tools_in_round", set())
            last_batch_prefix = req.runtime.state.get("_last_batch_prefix", None)

            tc = getattr(req, "tool_call", None)
            call_id = getattr(tc, "id", None) if tc else None

            batch_prefix = None
            if call_id:
                if "_split_" in str(call_id):
                    batch_prefix = str(call_id).rsplit("_split_", 1)[0]
                else:
                    batch_prefix = str(call_id)

            if batch_prefix and batch_prefix != last_batch_prefix:
                if tools_in_current_round:
                    logger.info(
                        "[Budget] 上一批次完成，共 %d 个工具",
                        len(tools_in_current_round),
                    )

                current_round += 1
                req.runtime.state["tool_rounds"] = current_round
                req.runtime.state["_tools_in_round"] = {call_id}
                req.runtime.state["_last_batch_prefix"] = batch_prefix
                logger.info(
                    "[Budget] 🔄 开始第 %d 轮工具调用（上限 %d 轮）",
                    current_round,
                    Config.MAX_TOOL_ROUNDS,
                )
            elif call_id and call_id not in tools_in_current_round:
                tools_in_current_round.add(call_id)
                req.runtime.state["_tools_in_round"] = tools_in_current_round
                logger.info(
                    "[Budget] 当前批次新增工具，共 %d 个",
                    len(tools_in_current_round),
                )

            if current_round > Config.MAX_TOOL_ROUNDS:
                logger.warning(
                    "[Budget] ⛔ 预算已耗尽（%d/%d），强制阻止工具调用",
                    current_round - 1,
                    Config.MAX_TOOL_ROUNDS,
                )
                return ToolMessage(
                    tool_call_id=call_id or "call_budget_exceeded",
                    content=(
                        '{"error":"预算已耗尽",'
                        f'"message":"工具调用已达到{Config.MAX_TOOL_ROUNDS}轮上限，请直接给出最终答案。"}}'
                    ),
                    name="budget_guard",
                )
    except Exception as e:
        logger.warning("[Budget] 工具预算计数异常（继续执行）：%s", e)

    return handler(req)


@wrap_tool_call
def enforce_city_on_tools(req, handler):
    """工具调用时强制 city/adcode 匹配目标城市集（仅改参数，不改工具名）"""
    try:
        tool_name = ""
        tc = req.tool_call if hasattr(req, "tool_call") else None
        if tc is None:
            return handler(req)

        # 获取工具名
        if isinstance(tc, dict):
            tool_name = (tc.get("name") or tc.get("function", {}).get("name") or "").lower()
        elif hasattr(tc, "name"):
            tool_name = (tc.name or "").lower()

        # 仅对地图相关工具生效
        if not any(
            k in tool_name for k in ("map", "amap", "poi", "route", "weather", "direction", "distance")
        ):
            return handler(req)

        # 获取目标城市（从模块级缓存读取）
        cities = _target_cities_cache

        if not cities:
            logger.debug("[EnforceCity] target_cities 为空，跳过注入（工具: %s）", tool_name)
            return handler(req)

        pinned_city = next(iter(cities))

        # 从 tool_call 中提取参数
        params = {}
        if isinstance(tc, dict):
            params = dict(tc.get("args") or {})
        elif hasattr(tc, "args") and isinstance(tc.args, dict):
            params = dict(tc.args)

        # 注入城市参数
        params["city"] = pinned_city
        params["cityd"] = pinned_city
        if "adcode" in params:
            params["adcode"] = ""

        # 用正确的 API 修改 tool_call（只支持 tool_call 参数）
        if isinstance(tc, dict):
            modified_call = {**tc, "args": params}
        else:
            # tc 是对象（如 ToolCall dataclass），需要构造新的 dict
            modified_call = {
                "name": getattr(tc, "name", ""),
                "args": params,
                "id": getattr(tc, "id", ""),
                "type": getattr(tc, "type", "tool_call"),
            }

        req = req.override(tool_call=modified_call)
        logger.info(
            "[EnforceCity] 工具 %s 已注入 city=%s",
            tool_name,
            pinned_city,
        )

    except Exception as e:
        logger.warning("[EnforceCity] 城市注入异常（继续执行）：%s", e)

    return handler(req)


# === wrap_model_call 中间件 ===

@wrap_model_call
def pin_query_from_messages(
    req: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """从 req.messages 找最后一条 human，同步到 runtime.state"""
    try:
        msgs = list(req.messages) if hasattr(req, "messages") else []
        last_human = None
        for m in reversed(msgs):
            if msg_is_human(m) or isinstance(m, HumanMessage):
                last_human = m
                break
        if last_human:
            q = msg_text(last_human)
            if q and hasattr(req, "runtime") and hasattr(req.runtime, "state"):
                req.runtime.state["__original_input__"] = q
                if not req.runtime.state.get("target_cities"):
                    req.runtime.state["target_cities"] = set(extract_cities(q))
                    req.runtime.state["target_cities_source_text"] = q
    except Exception:
        pass
    return handler(req)


@wrap_model_call
def cost_guard(
    req: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """模型调用前的成本护栏，同时确保 SystemMessage 仍在首位"""
    try:
        msgs = list(req.messages) if hasattr(req, "messages") else []
        if msgs:
            fixed = _ensure_system_first_in_messages(msgs)
            if fixed != msgs:
                req = req.override(messages=fixed)
    except Exception:
        pass

    guarded = req.override(
        model_settings={
            "max_output_tokens": Config.MAX_OUTPUT_TOKENS,
            "incremental_output": Config.INCREMENTAL_OUTPUT,
            "enable_thinking": Config.ENABLE_THINKING,
        }
    )
    return handler(guarded)


# === after_model 中间件 ===

@after_model
def fix_tool_calls_in_aimessage(resp, handler):
    """修正 AIMessage 中被拼接的工具名，支持拆分为多个 tool_call"""
    try:
        messages = None
        if hasattr(resp, "result") and resp.result:
            messages = resp.result
        elif isinstance(resp, dict) and "messages" in resp:
            messages = resp["messages"]
        elif isinstance(resp, list):
            messages = resp
        else:
            logger.warning("[FixAIMsg] 无法获取消息列表，跳过修正")
            return resp

        ai_msg = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                ai_msg = msg
                break

        if not ai_msg or not getattr(ai_msg, "tool_calls", None):
            return resp

        logger.info(
            "[FixAIMsg] 找到 AIMessage，有 %d 个工具调用",
            len(ai_msg.tool_calls),
        )

        tool_names = list(get_tool_names_sorted())

        if not tool_names and hasattr(resp, "request") and hasattr(
            resp.request, "tools"
        ):
            tool_names = sorted(
                [t.name for t in resp.request.tools if hasattr(t, "name")],
                key=len,
                reverse=True,
            )

        if not tool_names:
            logger.warning("[FixAIMsg] 无法获取工具列表，跳过修正")
            return resp

        fixed_calls = []
        import json
        import copy

        for tc in ai_msg.tool_calls:
            if isinstance(tc, dict):
                name = tc.get("name", "")
            else:
                name = getattr(tc, "name", "")

            if name in tool_names:
                fixed_calls.append(tc)
                continue

            matched_tools = []
            remaining = name
            while remaining:
                found = False
                for valid_name in tool_names:
                    if remaining.startswith(valid_name):
                        matched_tools.append(valid_name)
                        remaining = remaining[len(valid_name) :]
                        found = True
                        break
                if not found:
                    break

            if matched_tools:
                logger.info(
                    "[FixAIMsg] 检测到拼接工具名：'%s' -> %s",
                    name,
                    matched_tools,
                )

                original_tool_calls = []
                if hasattr(ai_msg, "additional_kwargs") and "tool_calls" in (
                    ai_msg.additional_kwargs or {}
                ):
                    original_tool_calls = ai_msg.additional_kwargs.get(
                        "tool_calls", []
                    )

                for i, tool_name in enumerate(matched_tools):
                    if isinstance(tc, dict):
                        tc_copy = tc.copy()
                        tc_copy["name"] = tool_name
                        if "id" in tc_copy:
                            tc_copy["id"] = f"{tc_copy['id']}_split_{i}"

                        if i < len(original_tool_calls):
                            orig_call = original_tool_calls[i]
                            if (
                                "function" in orig_call
                                and "arguments" in orig_call["function"]
                            ):
                                args_str = orig_call["function"]["arguments"]
                                try:
                                    tc_copy["args"] = (
                                        json.loads(args_str)
                                        if isinstance(args_str, str)
                                        else args_str
                                    )
                                except Exception:
                                    tc_copy["args"] = {}
                        fixed_calls.append(tc_copy)
                    else:
                        tc_copy = copy.deepcopy(tc)
                        tc_copy.name = tool_name
                        if hasattr(tc_copy, "id"):
                            tc_copy.id = f"{tc_copy.id}_split_{i}"

                        if i < len(original_tool_calls):
                            orig_call = original_tool_calls[i]
                            if (
                                "function" in orig_call
                                and "arguments" in orig_call["function"]
                            ):
                                args_str = orig_call["function"]["arguments"]
                                try:
                                    tc_copy.args = (
                                        json.loads(args_str)
                                        if isinstance(args_str, str)
                                        else args_str
                                    )
                                except Exception:
                                    pass
                        fixed_calls.append(tc_copy)
            else:
                logger.warning("[FixAIMsg] 无法修正工具名：'%s'", name)
                fixed_calls.append(tc)

        ai_msg.tool_calls = fixed_calls

        fixed_tool_names = []
        for tc in fixed_calls:
            if isinstance(tc, dict):
                fixed_tool_names.append(tc.get("name", "?"))
            else:
                fixed_tool_names.append(getattr(tc, "name", "?"))

        logger.info(
            "[FixAIMsg] ✅ 修正完成，共 %d 个工具：%s",
            len(fixed_calls),
            ", ".join(fixed_tool_names),
        )

        return resp
    except Exception as e:
        import traceback

        logger.warning(
            "[FixAIMsg] 修正失败（继续执行）：%s\n%s",
            e,
            traceback.format_exc(),
        )
        return resp


@after_model
def strip_unasked_cities(
    resp: ModelResponse, handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """产出后检查，如果出现了用户未提到的城市 / 外地标识，进行提示"""
    try:
        text = ""
        if hasattr(resp, "result") and resp.result:
            last = resp.result[-1]
            text = last.content if hasattr(last, "content") else str(last)
        elif hasattr(resp, "content"):
            text = resp.content
        else:
            return resp
    except Exception:
        return resp

    cities = set()
    try:
        if hasattr(resp, "request") and hasattr(resp.request, "runtime"):
            cities = set(
                resp.request.runtime.state.get("target_cities") or []
            )
        elif hasattr(resp, "request") and hasattr(resp.request, "state"):
            cities = set(resp.request.state.get("target_cities") or [])
    except Exception:
        cities = set()

    if not cities:
        return resp

    mentioned = set(extract_cities(text))
    unasked = mentioned - cities

    target_city = next(iter(cities))
    indicators = Config.CITY_INDICATORS.get(target_city, [])
    for indicator in indicators:
        if indicator in text:
            unasked.add(indicator)
            break

    if unasked:
        try:
            if hasattr(resp, "request") and hasattr(resp.request, "runtime"):
                if resp.request.runtime.state.get("__rewrite_done__"):
                    return resp
                resp.request.runtime.state["__rewrite_done__"] = True
        except Exception:
            pass

        try:
            target_city_list = ", ".join(sorted(cities))
            unasked_list = ", ".join(sorted(unasked))

            if hasattr(resp, "result") and resp.result:
                for msg in reversed(resp.result):
                    if isinstance(msg, AIMessage) and hasattr(msg, "content"):
                        msg.content += (
                            f"\n\n【自动修正】已检测到未指定城市：{unasked_list}。"
                            f"已自动剔除此类内容，请确认是否需要补充 {target_city_list} 范围内的等价地点。"
                        )
                        break
            return resp
        except Exception:
            return resp

    return resp
