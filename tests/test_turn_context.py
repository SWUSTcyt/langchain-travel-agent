"""本轮上下文：状态沿用、只带上一轮最终答案、不带工具原文、会话之间不串。"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import middleware
from langchain_core.messages import HumanMessage, SystemMessage
from turn_context import build_model_messages, visible_answer


class _Runtime:
    def __init__(self, context=None):
        self.state = {}
        self.context = context


class _ToolRequest:
    def __init__(self, tool_call, context=None):
        self.tool_call = tool_call
        self.state = {"messages": []}
        self.runtime = _Runtime(context)

    def override(self, **kwargs):
        return _ToolRequest(kwargs["tool_call"], self.runtime.context)


def _trip(*texts: str):
    return middleware.trip_state_from_texts(list(texts))


class ToolBudgetTest(unittest.TestCase):
    def test_extra_map_tools_are_not_sent_out(self):
        called = []
        result = middleware.track_tool_budget.wrap_tool_call(
            _ToolRequest({"name": "maps_direction_driving", "args": {}, "id": "d1"}),
            lambda req: called.append(req) or "sent",
        )
        self.assertEqual(called, [])
        self.assertIn("不用调用", result.content)

    def test_text_search_is_still_sent_out(self):
        called = []
        result = middleware.track_tool_budget.wrap_tool_call(
            _ToolRequest({"name": "maps_text_search", "args": {"keywords": "故宫"}, "id": "s1"}),
            lambda req: called.append(req.tool_call["name"]) or "sent",
        )
        self.assertEqual(called, ["maps_text_search"])
        self.assertEqual(result, "sent")

    def test_second_text_search_in_same_round_is_not_sent(self):
        called = []
        first = _ToolRequest({"name": "maps_text_search", "args": {}, "id": "s1"})
        second = _ToolRequest({"name": "maps_text_search", "args": {}, "id": "s2"})
        second.runtime = first.runtime

        middleware.track_tool_budget.wrap_tool_call(
            first, lambda req: called.append(req.tool_call["id"]) or "sent"
        )
        result = middleware.track_tool_budget.wrap_tool_call(
            second, lambda req: called.append(req.tool_call["id"]) or "sent"
        )
        self.assertEqual(called, ["s1"])
        self.assertIn("已经搜过", result.content)

    def test_new_round_can_search_again(self):
        called = []
        first = _ToolRequest({"name": "maps_text_search", "args": {}, "id": "s1"})
        middleware.track_tool_budget.wrap_tool_call(
            first, lambda req: called.append(req.tool_call["id"]) or "sent"
        )
        again = _ToolRequest({"name": "maps_text_search", "args": {}, "id": "s9"})
        result = middleware.track_tool_budget.wrap_tool_call(
            again, lambda req: called.append(req.tool_call["id"]) or "sent"
        )
        self.assertEqual(result, "sent")
        self.assertEqual(called, ["s1", "s9"])

    def test_second_weather_in_same_round_is_not_sent(self):
        called = []
        first = _ToolRequest({"name": "maps_weather", "args": {}, "id": "w1"})
        second = _ToolRequest({"name": "maps_weather", "args": {}, "id": "w2"})
        second.runtime = first.runtime
        middleware.track_tool_budget.wrap_tool_call(
            first, lambda req: called.append(req.tool_call["id"]) or "sent"
        )
        result = middleware.track_tool_budget.wrap_tool_call(
            second, lambda req: called.append(req.tool_call["id"]) or "sent"
        )
        self.assertEqual(called, ["w1"])
        self.assertIn("已经查过", result.content)


def _tool_city(args: dict, trip) -> str | None:
    seen = []
    middleware.enforce_city_on_tools.wrap_tool_call(
        _ToolRequest({"name": "maps_weather", "args": args, "id": "c1"}, trip),
        lambda req: seen.append(req) or "called",
    )
    return seen[0].tool_call["args"].get("city") if seen else None


def _system_prompt(text: str, trip) -> str:
    result = middleware.pin_cities_and_adcodes.before_model(
        {"messages": [HumanMessage(content=text)]},
        _Runtime(trip),
    )
    first = result["messages"][0]
    assert isinstance(first, SystemMessage)
    return first.content


class KeepCityTest(unittest.TestCase):
    def test_followup_without_city_keeps_previous_city_and_updates_days(self):
        trip = _trip("成都今天天气", "改成两天")
        self.assertEqual(trip.cities, ("成都",))
        self.assertIn("两天", trip.constraints_line())
        prompt = _system_prompt("改成两天", trip)
        self.assertIn("沿用上一轮城市：成都", prompt)
        self.assertIn("两天", prompt)

    def test_new_city_replaces_old_city(self):
        trip = _trip("成都今天天气", "改去杭州")
        self.assertEqual(trip.cities, ("杭州",))
        self.assertTrue(trip.cities_from_current)

    def test_city_survives_a_followup_that_names_no_city(self):
        trip = _trip("成都三天", "加个美食", "改成两天")
        self.assertEqual(trip.cities, ("成都",))
        self.assertEqual(trip.days, "两天")

    def test_unlisted_city_named_now_is_not_overwritten_by_previous_city(self):
        # 丽江不在内置城市表里。模型给了丽江，不能被改成上一轮的成都。
        trip = _trip("成都两天", "丽江今天天气")
        self.assertEqual(_tool_city({"city": "丽江"}, trip), "丽江")

    def test_carried_city_fills_tool_when_model_gives_none(self):
        trip = _trip("成都两天", "改成三天")
        self.assertEqual(_tool_city({"keywords": "火锅"}, trip), "成都")

    def test_city_named_now_is_still_forced(self):
        trip = _trip("成都今天天气")
        self.assertEqual(_tool_city({"city": "杭州"}, trip), "成都")


class DaysTest(unittest.TestCase):
    def test_ordinal_day_is_not_trip_length(self):
        trip = _trip("成都，第一天去宽窄巷子，第二天去熊猫基地，一共三天")
        self.assertEqual(trip.days, "三天")

    def test_ordinal_only_sets_no_days(self):
        self.assertIsNone(_trip("第十二天想去哪").days)
        self.assertIsNone(_trip("第3天去哪").days)

    def test_plain_days_still_parsed(self):
        self.assertEqual(_trip("成都 3 天").days, "3天")
        self.assertEqual(_trip("改成两天").days, "两天")


class TurnMessagesTest(unittest.TestCase):
    def test_only_previous_final_answer_is_kept(self):
        history = [
            {"role": "user", "content": "北京三天"},
            {"role": "assistant", "content": "## 最终答案\n\n北京那天很冷"},
            {"role": "tool", "content": "{\"raw\":\"不应该进入下一轮\"}"},
            {"role": "user", "content": "成都今天天气"},
            {
                "role": "assistant",
                "content": (
                    "<details><summary>思考</summary>\n先查天气，不要把这段送回去\n</details>"
                    "\n\n---\n\n## 最终答案\n\n成都今天晴"
                ),
            },
            {"role": "user", "content": "改成两天"},
            {"role": "assistant", "content": ""},
        ]
        messages = build_model_messages(history, "改成两天")
        contents = [message.content for message in messages]
        self.assertEqual(contents, ["成都今天天气", "成都今天晴", "改成两天"])
        blob = "\n".join(contents)
        self.assertNotIn("思考", blob)
        self.assertNotIn("北京", blob)
        self.assertNotIn("raw", blob)

    def test_reasoning_without_final_answer_is_dropped(self):
        self.assertEqual(visible_answer("<details>只有思考</details>"), "")


class StreamAnswerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class _Agent:
            def __init__(self):
                self.seen = []

            def stream(self, payload, config=None, context=None):
                self.seen.append((payload, context))
                return iter(())

            def invoke(self, payload, config=None, context=None):
                self.seen.append((payload, context))
                return {"messages": []}

        fake_agent = types.ModuleType("agent")
        fake_agent.agent = _Agent()
        sys.modules["agent"] = fake_agent
        import importlib

        if "ui" in sys.modules:
            ui = importlib.reload(sys.modules["ui"])
        else:
            import ui
        cls.ui = ui

    def setUp(self):
        self.holder = type(sys.modules["agent"].agent)()
        self.ui.agent = self.holder

    def test_stream_answer_sends_that_window(self):
        history = [
            {"role": "user", "content": "成都今天天气"},
            {"role": "assistant", "content": "## 最终答案\n\n成都今天晴"},
            {"role": "user", "content": "改成两天"},
            {"role": "assistant", "content": ""},
        ]
        list(self.ui.stream_answer("改成两天", history, False))
        payload, context = self.holder.seen[0]
        contents = [message.content for message in payload["messages"]]
        self.assertEqual(contents, ["成都今天天气", "成都今天晴", "改成两天"])
        self.assertEqual(context.cities, ("成都",))
        self.assertEqual(context.days, "两天")

    def test_new_session_does_not_inherit_other_session_city(self):
        session_a = [
            {"role": "user", "content": "成都两天"},
            {"role": "assistant", "content": "## 最终答案\n\n成都行程"},
        ]
        list(self.ui.stream_answer("改成三天", session_a, False))
        list(self.ui.stream_answer("推荐几个景点", [], False))
        _, context_a = self.holder.seen[0]
        _, context_b = self.holder.seen[-1]
        self.assertEqual(context_a.cities, ("成都",))
        self.assertEqual(context_b.cities, ())
        self.assertIsNone(context_b.days)


if __name__ == "__main__":
    unittest.main()
