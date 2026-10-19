"""一轮模型上下文。

只保留：行程里还生效的城市/天数/节奏、上一轮用户原话、上一轮最终答案、当前这句。
不放入整段屏幕历史、思考过程 HTML、调试日志，也不重放上一轮的工具原文。

行程状态每轮从本会话的用户原话重新算出，不存进程级变量，多个浏览器会话互不影响。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage

# 前面紧跟「第」或数字时是序数（第一天、第十二天、第3天），不是行程天数。
_DAYS_RE = re.compile(
    r"(?<![第\d一二三四五六七八九十两])"
    r"(\d+\s*天|[一二三四五六七八九十两]{1,3}\s*天)"
    r"|(周末|一日游|两日游)"
)


@dataclass(frozen=True)
class TripState:
    """本会话当前仍生效的行程字段。作为 agent 运行上下文传给中间件。"""

    cities: tuple[str, ...] = ()
    # 城市是否由当前这句点名；False 表示沿用更早的轮次
    cities_from_current: bool = False
    days: str | None = None
    pace: str | None = None

    def constraints_line(self) -> str:
        parts = []
        if self.days:
            parts.append(f"行程天数：{self.days}")
        if self.pace:
            parts.append(f"节奏：{self.pace}")
        return "。".join(parts)


def parse_days(text: str) -> str | None:
    """取句中第一个行程天数；序数词不算。"""
    found = _DAYS_RE.search(text or "")
    if not found:
        return None
    return re.sub(r"\s+", "", found.group(1) or found.group(2))


def parse_pace(text: str) -> str | None:
    if "轻松" in (text or "") or "不赶" in (text or ""):
        return "轻松不赶"
    return None


def session_user_texts(history: list | None, current_text: str) -> list[str]:
    """本会话按时间顺序的用户原话，当前这句在最后。只用来算行程状态，不进模型上下文。"""
    texts = []
    for message in history or []:
        if not isinstance(message, dict):
            continue
        if message.get("role") not in ("user", "human"):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            texts.append(content.strip())
    if texts and texts[-1] == (current_text or "").strip():
        texts.pop()
    texts.append(current_text or "")
    return texts


def visible_answer(content: str) -> str:
    """从界面消息里只取出最终答案。思考过程和日志不能进下一轮。"""
    text = content or ""
    marker = "## 最终答案"
    if marker in text:
        text = text.split(marker, 1)[1]
        text = re.sub(r"^[\s\-]*", "", text).strip()
        return text
    if "<details" in text:
        return ""
    return text.strip()


def previous_exchange(history: list | None, current_text: str) -> tuple[str | None, str | None]:
    """只取紧邻的上一轮：用户原话 + 最终答案。更早的轮次和工具原文都不要。"""
    items = []
    for message in history or []:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role not in ("user", "assistant", "human"):
            continue
        items.append(message)

    if items and items[-1].get("role") == "assistant" and not (items[-1].get("content") or "").strip():
        items.pop()
    if (
        items
        and items[-1].get("role") in ("user", "human")
        and (items[-1].get("content") or "") == current_text
    ):
        items.pop()

    prior_answer = None
    prior_user = None
    if items and items[-1].get("role") == "assistant":
        prior_answer = visible_answer(items[-1].get("content") or "")
        items.pop()
    if items and items[-1].get("role") in ("user", "human"):
        prior_user = (items[-1].get("content") or "").strip()

    if not prior_user or not prior_answer:
        return None, None
    return prior_user, prior_answer


def build_model_messages(history: list | None, current_text: str) -> list:
    """组装本轮模型输入。当前这句一定在最后。"""
    prior_user, prior_answer = previous_exchange(history, current_text)
    messages = []
    if prior_user and prior_answer:
        messages.append(HumanMessage(content=prior_user))
        messages.append(AIMessage(content=prior_answer))
    messages.append(HumanMessage(content=current_text))
    return messages
