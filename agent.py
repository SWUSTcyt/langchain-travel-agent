"""Agent 创建与配置（绑定 MCP 工具与中间件）"""

import logging

from langchain.agents import create_agent
from langchain_community.chat_models.tongyi import ChatTongyi

from config import DASHSCOPE_API_KEY, Config
from tools import load_tools, get_global_tools
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


def create_travel_agent():
    """创建并返回旅行规划 Agent 实例"""

    if not DASHSCOPE_API_KEY:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置，请检查 .env 或环境变量")

    # 1) 加载工具（MCP -> LangChain Tools）
    tools = load_tools()

    # 2) 配置 Qwen 模型（支持“深度思考”+ 流式输出）
    qwen = ChatTongyi(
        dashscope_api_key=DASHSCOPE_API_KEY,
        model="qwen-turbo-latest",
        streaming=True,
        model_kwargs={
            "enable_thinking": Config.ENABLE_THINKING,
            "incremental_output": Config.INCREMENTAL_OUTPUT,
            "temperature": 0.7,
            "top_p": 0.8,
            "max_output_tokens": Config.MAX_OUTPUT_TOKENS,
        },
    )

    qwen = qwen.bind_tools(tools)

    # 3) 挂载中间件
    agent = create_agent(
        model=qwen,
        tools=tools,
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
