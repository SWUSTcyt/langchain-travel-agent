"""本轮上下文的三种用法。不调用模型，也不连接地图。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from middleware import trip_state_from_texts  # noqa: E402
from turn_context import build_model_messages, session_user_texts  # noqa: E402


def example_first_turn():
    """第一句没有上一轮，模型只看到当前这句。"""
    messages = build_model_messages([], "成都今天天气")
    assert [item.content for item in messages] == ["成都今天天气"]


def example_followup_keeps_days():
    """「改成两天」只更新天数，城市和节奏沿用本会话更早的说法。"""
    history = [
        {"role": "user", "content": "成都 2 天，轻松不赶"},
        {"role": "assistant", "content": "## 最终答案\n\n成都两日游"},
        {"role": "user", "content": "加个美食"},
        {"role": "assistant", "content": "## 最终答案\n\n加了火锅"},
    ]
    trip = trip_state_from_texts(session_user_texts(history, "改成三天"))
    assert trip.cities == ("成都",)
    assert "三天" in trip.constraints_line()
    assert "轻松不赶" in trip.constraints_line()


def example_window_drops_reasoning():
    """上一轮只留最终答案，思考过程留在屏幕上。"""
    history = [
        {"role": "user", "content": "成都今天天气"},
        {
            "role": "assistant",
            "content": "<details>思考过程</details>\n\n## 最终答案\n\n成都今天晴",
        },
        {"role": "user", "content": "改成两天"},
    ]
    messages = build_model_messages(history, "改成两天")
    assert [item.content for item in messages] == [
        "成都今天天气",
        "成都今天晴",
        "改成两天",
    ]


if __name__ == "__main__":
    example_first_turn()
    example_followup_keeps_days()
    example_window_drops_reasoning()
    print("examples ok")
