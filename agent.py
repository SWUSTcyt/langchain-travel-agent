"""Agent 创建与配置（绑定 MCP 工具与中间件）"""

import logging

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODEL_NAME, Config
from tools import load_tools, get_global_tools
from turn_context import TripState
from middleware import (
    pin_cities_and_adcodes,
    inject_budget_status,
    ensure_single_system_first,
    track_tool_budget,
    enforce_city_on_tools,
    pin_query_from_messages,
    cost_guard,
    fix_tool_calls_in_aimessage,
    strip_unasked_cities,
)

logger = logging.getLogger(__name__)


class QwenChat(ChatOpenAI):
    """千问兼容接口。官方 ChatOpenAI 会丢掉 reasoning_content，这里补回给界面。"""

    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)
        response_dict = (
            response if isinstance(response, dict) else response.model_dump()
        )
        choices = response_dict.get("choices") or []
        if not choices:
            return result
        message = choices[0].get("message") or {}
        reasoning = message.get("reasoning_content")
        if reasoning:
            result.generations[0].message.additional_kwargs["reasoning_content"] = (
                reasoning
            )
        return result

    def _convert_chunk_to_generation_chunk(
        self, chunk, default_chunk_class, base_generation_info
    ):
        generation = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        if generation is None:
            return None
        choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices") or []
        if not choices:
            return generation
        delta = choices[0].get("delta") or {}
        reasoning = delta.get("reasoning_content")
        if reasoning:
            generation.message.additional_kwargs["reasoning_content"] = reasoning
        return generation


def create_travel_agent():
    """创建并返回旅行规划 Agent 实例"""

    if not DASHSCOPE_API_KEY:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置，请检查 .env 或环境变量")

    # 1) 加载工具（MCP -> LangChain Tools）
    tools = load_tools()

    # 2) 千问 3.8 flash，走兼容接口。思考开关由 cost_guard 按请求写入 extra_body。
    qwen = QwenChat(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
        model=MODEL_NAME,
        temperature=0.7,
        top_p=0.8,
        max_tokens=Config.MAX_OUTPUT_TOKENS,
        streaming=True,
    )

    qwen = qwen.bind_tools(tools)

    # 3) 挂载中间件
    agent = create_agent(
        model=qwen,
        tools=tools,
        context_schema=TripState,
        middleware=[
            # before_model
            pin_cities_and_adcodes,
            inject_budget_status,
            ensure_single_system_first,
            # wrap_tool_call
            track_tool_budget,
            enforce_city_on_tools,
            # wrap_model_call
            pin_query_from_messages,
            cost_guard,
            # after_model
            fix_tool_calls_in_aimessage,
            strip_unasked_cities,
        ],
    )

    logger.info(
        "[Agent] 旅行规划 Agent 创建完成，已绑定 %d 个工具",
        len(get_global_tools()),
    )
    return agent


# 默认导出一个全局 agent，方便 ui.py 直接使用
agent = create_travel_agent()
