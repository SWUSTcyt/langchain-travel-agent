
"""配置管理与常量集中定义"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """项目级别配置常量"""

    # 工具调用预算（轮次）
    # 启用并行调用后，1 轮即可完成大部分查询（POI + 路线 + 天气）
    MAX_TOOL_ROUNDS: int = 1

    # 模型输出配置
    MAX_OUTPUT_TOKENS: int = 1200
    ENABLE_THINKING: bool = True
    INCREMENTAL_OUTPUT: bool = True

    # 异步工具超时（秒）
    ASYNC_TOOL_TIMEOUT: int = 10

    # 城市标识映射 / “外地”指示，用于 strip_unasked_cities 额外检查
    CITY_INDICATORS = {
        "成都": ["杭州", "西湖", "330100", "330102", "北京", "110000", "上海", "310000"],
        "杭州": ["成都", "510100", "北京", "110000", "上海", "310000"],
        "北京": ["杭州", "330100", "成都", "510100", "上海", "310000"],
    }


# 环境变量（对外暴露，方便其它模块直接使用）
DASHSCOPE_API_KEY: str | None = os.getenv("DASHSCOPE_API_KEY")
AMAP_MCP_URL: str | None = os.getenv("AMAP_MCP_URL")
