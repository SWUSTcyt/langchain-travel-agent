
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
    # 详细行程还要在文末附 json，1200 会把代码块截断，解析不出来
    MAX_OUTPUT_TOKENS: int = 4096
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
# Web 端 JS 与 MCP 的 key 分开。缺省时地图区显示「地图暂不可用」。
AMAP_JS_KEY: str = os.getenv("AMAP_JS_KEY") or ""
AMAP_JS_SECURITY_CODE: str = os.getenv("AMAP_JS_SECURITY_CODE") or ""

# qwen-turbo 已于 2026-10-10 下线。新模型走兼容接口，不用旧的 Generation 接口。
MODEL_NAME: str = "qwen3.8-flash"
DASHSCOPE_BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL") or (
    "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
