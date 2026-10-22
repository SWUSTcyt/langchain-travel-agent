"""离线基线测试。

不调用通义、不连接高德。预期按用户可见契约写，不从实现里抄结果。
"""

from __future__ import annotations

import os
import subprocess
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import middleware
from langchain_core.messages import HumanMessage


class _Runtime:
    def __init__(self):
        self.state = {}


class _ToolRuntime:
    def __init__(self, context=None):
        self.context = context
        self.state = {}


class _ToolRequest:
    """只提供 enforce_city_on_tools 实际读取的字段。"""

    def __init__(
        self, tool_call, *, trip=None, override_error: Exception | None = None
    ):
        self.tool_call = tool_call
        self.state = {"messages": []}
        self.runtime = _ToolRuntime(trip)
        self._override_error = override_error

    def override(self, **kwargs):
        if self._override_error is not None:
            raise self._override_error
        if "tool_call" not in kwargs:
            raise TypeError("override 只接受 tool_call")
        return _ToolRequest(kwargs["tool_call"], trip=self.runtime.context)


def _pin(text: str):
    """按单句算出本会话行程状态，并确认 before_model 能用它生成提示。"""
    trip = middleware.trip_state_from_texts([text])
    middleware.pin_cities_and_adcodes.before_model(
        {"messages": [HumanMessage(content=text)]},
        _ToolRuntime(trip),
    )
    return trip


def _run(tool_call, *, trip=None, override_error: Exception | None = None):
    seen = []

    def handler(req):
        seen.append(req)
        return "called"

    middleware.enforce_city_on_tools.wrap_tool_call(
        _ToolRequest(tool_call, trip=trip, override_error=override_error),
        handler,
    )
    return seen


class ExtractCitiesTest(unittest.TestCase):
    def test_keeps_order_and_drops_duplicates(self):
        # 用户一句话里点了两个城市，并重复了其中一个
        self.assertEqual(
            middleware.extract_cities("先去成都，再去杭州，最后还是成都"),
            ["成都", "杭州"],
        )

    def test_unknown_city_and_empty_text_yield_nothing(self):
        self.assertEqual(middleware.extract_cities("我想去丽江"), [])
        self.assertEqual(middleware.extract_cities(""), [])
        self.assertEqual(middleware.extract_cities(None), [])


class MaskCoordTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # ui 在导入时会创建真实 Agent。这里换成空模块，避免连模型和地图。
        fake = types.ModuleType("agent")
        fake.agent = object()
        sys.modules["agent"] = fake
        import ui

        cls.ui = ui

    def test_coordinate_keeps_three_decimal_places(self):
        raw = "104.065735,30.659462"
        masked = self.ui._mask_coord(raw)
        self.assertEqual(masked, "104.066,30.659")
        self.assertNotIn(raw, masked)

    def test_non_coordinate_is_unchanged(self):
        self.assertEqual(self.ui._mask_coord("春熙路"), "春熙路")
        self.assertEqual(self.ui._mask_coord("12,abc"), "12,abc")

    def test_tool_log_does_not_keep_full_precision(self):
        raw = "104.065735,30.659462"
        summary = self.ui._event_to_summary(
            {
                "tool": {"name": "maps_direction_driving"},
                "tool_input": {
                    "city": "成都",
                    "origin": raw,
                    "destination": "104.081534,30.657101",
                },
            }
        )
        self.assertNotIn(raw, summary)
        self.assertIn("104.066,30.659", summary)
        self.assertIn("city=成都", summary)


class CityInjectionTest(unittest.TestCase):
    def test_named_city_is_injected_before_map_tool_runs(self):
        trip = _pin("帮我看看成都今天天气")
        self.assertEqual(trip.cities, ("成都",))

        seen = _run(
            {
                "name": "maps_weather",
                "args": {"city": "杭州", "adcode": "330100"},
                "id": "call-1",
                "type": "tool_call",
            },
            trip=trip,
        )

        self.assertEqual(len(seen), 1)
        args = seen[0].tool_call["args"]
        self.assertEqual(args["city"], "成都")
        self.assertEqual(args["cityd"], "成都")
        self.assertNotEqual(args.get("adcode"), "330100")

    def test_non_map_tool_is_not_rewritten(self):
        trip = _pin("成都两日游")
        original = {"name": "calculator", "args": {"expression": "1+1"}, "id": "c2"}
        seen = _run(original, trip=trip)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].tool_call, original)

    def test_map_tool_not_called_when_city_injection_fails(self):
        # 用户已经点名城市。注入失败时，地图工具不应再拿着错误参数执行。
        trip = _pin("成都天气")
        seen = _run(
            {"name": "maps_text_search", "args": {"keywords": "火锅"}, "id": "c3"},
            trip=trip,
            override_error=RuntimeError("override 失败"),
        )
        self.assertEqual(seen, [])

    def test_tool_error_is_not_reported_as_city_injection_failure(self):
        # 城市已写好，是工具自己出错。不能被说成「城市注入失败」，也不能再调一次工具。
        trip = _pin("成都天气")
        calls = []

        def broken(req):
            calls.append(req)
            raise ValueError("高德超限")

        with self.assertRaises(ValueError):
            middleware.enforce_city_on_tools.wrap_tool_call(
                _ToolRequest(
                    {"name": "maps_weather", "args": {}, "id": "c4"}, trip=trip
                ),
                broken,
            )
        self.assertEqual(len(calls), 1)


class ToolFailureTextTest(unittest.TestCase):
    """地图工具出错时，交给模型的必须是失败，不能鼓励它当成查到了接着答。"""

    def _assert_visible_failure(self, text: str) -> None:
        self.assertIn("工具执行失败", text)
        self.assertNotIn("直接回答", text)
        self.assertNotIn("基于已知信息", text)

    def test_timeout_is_reported_as_failure(self):
        import tools

        async def slow():
            raise TimeoutError("timed out")

        self._assert_visible_failure(tools._safe_run_coro(slow))

    def test_quota_error_is_reported_as_failure(self):
        import tools

        async def quota():
            raise RuntimeError("CUQPS_HAS_EXCEEDED_THE_LIMIT")

        self._assert_visible_failure(tools._safe_run_coro(quota))

    def test_successful_result_is_returned_unchanged(self):
        import tools

        async def weather():
            return '{"city":"成都","weather":"多云"}'

        self.assertEqual(
            tools._safe_run_coro(weather), '{"city":"成都","weather":"多云"}'
        )


class NoKeyNoModelTest(unittest.TestCase):
    def test_importing_ui_without_key_does_not_construct_model(self):
        script = r"""
import os
os.environ["DASHSCOPE_API_KEY"] = ""

import langchain_openai
import tools

constructed = []

class Sentinel:
    def __init__(self, *args, **kwargs):
        constructed.append(kwargs.get("model"))

    def bind_tools(self, _tools):
        return self

def load_tools_called():
    raise AssertionError("load_tools called")

langchain_openai.ChatOpenAI = Sentinel
tools.load_tools = load_tools_called

try:
    import ui
except RuntimeError as exc:
    message = str(exc)
else:
    raise SystemExit("missing RuntimeError")

if "DASHSCOPE_API_KEY" not in message:
    raise SystemExit("unexpected error: " + message)
if constructed:
    raise SystemExit("model constructed")
print("NO_MODEL_CALL")
"""
        env = os.environ.copy()
        env["DASHSCOPE_API_KEY"] = ""
        env["PYTHONPATH"] = str(ROOT)
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        self.assertIn("NO_MODEL_CALL", completed.stdout, output)
        self.assertEqual(completed.returncode, 0, output)
        self.assertNotIn("sk-", output)


if __name__ == "__main__":
    unittest.main()
