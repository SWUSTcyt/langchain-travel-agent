"""工具失败文本的三种用法。不调用模型，也不连接地图。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tools  # noqa: E402


def example_timeout_is_failure():
    """超时交给模型的是失败，不是「基于已知信息直接回答」。"""

    async def slow():
        raise TimeoutError("timed out")

    text = tools._safe_run_coro(slow)
    assert "工具执行失败" in text
    assert "直接回答" not in text
    assert "基于已知信息" not in text


def example_quota_is_failure():
    """高德额度超限同样是失败。"""

    async def quota():
        raise RuntimeError("CUQPS_HAS_EXCEEDED_THE_LIMIT")

    text = tools._safe_run_coro(quota)
    assert "工具执行失败" in text
    assert "没查到" in text


def example_success_unchanged():
    """成功时原文原样交回。"""

    async def weather():
        return '{"city":"成都","weather":"多云"}'

    assert tools._safe_run_coro(weather) == '{"city":"成都","weather":"多云"}'


if __name__ == "__main__":
    example_timeout_is_failure()
    example_quota_is_failure()
    example_success_unchanged()
    print("examples ok")
