"""结构化行程：坐标只来自本轮地图搜索，模型自己写的坐标不算数。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import itinerary
import itinerary_view
from langchain_core.messages import HumanMessage, SystemMessage


POI_PAYLOAD = """{
  "pois": [
    {"name": "宽窄巷子", "location": "104.055,30.670", "cityname": "成都市"},
    {"name": "大熊猫基地", "location": "104.145,30.735", "cityname": "成都市"},
    {"name": "海底捞", "location": "104.066,30.572", "cityname": "成都市"},
    {"name": "海底捞", "location": "100.233,26.872", "cityname": "丽江市"}
  ]
}"""


def _search(content: str, name: str = "maps_text_search"):
    return {"name": name, "content": content}


def _answer(days: list[dict], extra_stop_fields: dict | None = None) -> str:
    import json

    if extra_stop_fields:
        for day in days:
            for stop in day["stops"]:
                stop.update(extra_stop_fields)
    block = json.dumps({"days": days}, ensure_ascii=False)
    return f"成都三天，轻松不赶。\n\n```json\n{block}\n```"


class ParseItineraryTest(unittest.TestCase):
    def test_missing_json_returns_none(self):
        """删掉代码块解析就应失败。模型没附 JSON 时不能编出行程。"""
        self.assertIsNone(itinerary.parse_itinerary("今天成都多云，9 到 23 度。"))

    def test_broken_json_returns_none(self):
        text = "看一下。\n```json\n{不是json\n```"
        self.assertIsNone(itinerary.parse_itinerary(text))

    def test_three_days_keep_slot_and_name(self):
        text = _answer(
            [
                {"stops": [{"slot": "上午", "name": "宽窄巷子", "what": "逛巷子", "how": "地铁", "tip": "早去"}]},
                {"stops": [{"slot": "下午", "name": "人民公园", "what": "喝茶", "how": "步行", "tip": ""}]},
                {"stops": [{"slot": "晚上", "name": "锦里", "what": "吃饭", "how": "打车", "tip": "看关门时间"}]},
            ]
        )
        parsed = itinerary.parse_itinerary(text)
        self.assertEqual(len(parsed.days), 3)
        self.assertEqual(parsed.days[0].stops[0].slot, "上午")
        self.assertEqual(parsed.days[0].stops[0].name, "宽窄巷子")
        self.assertEqual(parsed.days[2].stops[0].how, "打车")


class AttachCoordsTest(unittest.TestCase):
    def test_unmatched_place_has_no_coords(self):
        text = _answer(
            [{"stops": [{"slot": "上午", "name": "人民公园", "what": "喝茶", "how": "步行", "tip": ""}]}]
        )
        parsed = itinerary.attach_coords(
            itinerary.parse_itinerary(text),
            itinerary.extract_pois([_search(POI_PAYLOAD)]),
            city="成都",
        )
        stop = parsed.days[0].stops[0]
        self.assertIsNone(stop.lng)
        self.assertIsNone(stop.lat)

    def test_model_coords_are_ignored(self):
        """模型在 JSON 里写的经纬度必须丢掉，只用工具返回。"""
        text = _answer(
            [{"stops": [{"slot": "上午", "name": "宽窄巷子", "what": "逛", "how": "地铁", "tip": ""}]}],
            {"lng": 1.0, "lat": 2.0},
        )
        parsed = itinerary.parse_itinerary(text)
        self.assertIsNone(parsed.days[0].stops[0].lng)
        attached = itinerary.attach_coords(
            parsed,
            itinerary.extract_pois([_search(POI_PAYLOAD)]),
            city="成都",
        )
        stop = attached.days[0].stops[0]
        self.assertAlmostEqual(stop.lng, 104.055, places=3)
        self.assertAlmostEqual(stop.lat, 30.670, places=3)

    def test_ambiguous_name_not_mapped(self):
        payload = """{"pois": [
            {"name": "海底捞", "location": "104.066,30.572", "cityname": "成都市"},
            {"name": "海底捞", "location": "104.080,30.660", "cityname": "成都市"}
        ]}"""
        text = _answer(
            [{"stops": [{"slot": "晚上", "name": "海底捞", "what": "吃饭", "how": "打车", "tip": ""}]}]
        )
        attached = itinerary.attach_coords(
            itinerary.parse_itinerary(text),
            itinerary.extract_pois([_search(payload)]),
            city="成都",
        )
        stop = attached.days[0].stops[0]
        self.assertIsNone(stop.lng)
        self.assertIsNone(stop.lat)

    def test_same_name_in_another_city_uses_this_city(self):
        text = _answer(
            [{"stops": [{"slot": "晚上", "name": "海底捞", "what": "吃饭", "how": "打车", "tip": ""}]}]
        )
        attached = itinerary.attach_coords(
            itinerary.parse_itinerary(text),
            itinerary.extract_pois([_search(POI_PAYLOAD)]),
            city="成都",
        )
        stop = attached.days[0].stops[0]
        self.assertAlmostEqual(stop.lng, 104.066, places=3)
        self.assertAlmostEqual(stop.lat, 30.572, places=3)

    def test_weather_tool_is_not_a_poi_source(self):
        weather = _search('{"city":"成都","weather":"多云"}', name="maps_weather")
        self.assertEqual(itinerary.extract_pois([weather]), [])


class DetailCoordTest(unittest.TestCase):
    """关键词搜索没有坐标。详情里的 location 才能上图。"""

    def test_search_without_location_needs_detail(self):
        search = (
            '{"pois":[{"id":"B1","name":"杭州西湖风景名胜区","address":"龙井路1号"},'
            '{"id":"B2","name":"断桥残雪","address":"北山街"}]}'
        )
        self.assertEqual(itinerary.extract_pois([{"name": "maps_text_search", "content": search}]), [])
        refs = itinerary.extract_place_refs([{"name": "maps_text_search", "content": (search, None)}])
        self.assertEqual([ref.poi_id for ref in refs], ["B1", "B2"])

    def test_one_day_hangzhou_gets_line_not_chengdu(self):
        search = (
            '{"pois":[{"id":"B1","name":"杭州西湖风景名胜区"},'
            '{"id":"B2","name":"断桥残雪"},'
            '{"id":"B3","name":"杭州西湖风景名胜区-苏堤春晓"}]}'
        )
        answer = _answer(
            [
                {
                    "stops": [
                        {"slot": "上午", "name": "杭州西湖风景名胜区", "what": "逛", "how": "步行", "tip": ""},
                        {"slot": "下午", "name": "断桥残雪", "what": "看桥", "how": "步行", "tip": ""},
                    ]
                }
            ]
        )
        details = {
            "B1": '{"id":"B1","name":"杭州西湖风景名胜区","location":"120.121,30.223","city":"杭州市"}',
            "B2": '{"id":"B2","name":"断桥残雪","location":"120.149,30.260","city":"杭州市"}',
        }
        called = []

        def fetch(poi_id):
            called.append(poi_id)
            return details[poi_id]

        _display, parsed, _map_itinerary = itinerary.finalize_turn(
            answer,
            [{"name": "maps_text_search", "content": search}],
            city="杭州",
            fetch_detail=fetch,
        )
        self.assertEqual(sorted(called), ["B1", "B2"])
        stops = parsed.days[0].stops
        self.assertGreater(stops[0].lng, 115)
        self.assertGreater(stops[1].lng, 115)
        self.assertLess(stops[0].lng, 122)
        payload = itinerary_view.map_payload(parsed, js_key="test-js-key")
        self.assertEqual(itinerary_view.map_card_mode(payload), "map")
        self.assertEqual(len(payload["days"][0]["path"]), 2)
        blob = json.dumps(payload)
        self.assertNotIn("104.055", blob)

    def test_third_day_is_not_left_without_coordinates(self):
        pois = []
        days = []
        details = {}
        for day_index in range(3):
            stops = []
            for stop_index in range(3):
                poi_id = f"D{day_index}{stop_index}"
                name = f"地点{day_index}{stop_index}"
                lng = 116.3 + day_index * 0.05 + stop_index * 0.01
                lat = 39.9 + stop_index * 0.01
                pois.append({"id": poi_id, "name": name})
                details[poi_id] = (
                    f'{{"id":"{poi_id}","name":"{name}",'
                    f'"location":"{lng:.3f},{lat:.3f}","city":"北京市"}}'
                )
                stops.append(
                    {"slot": "上午", "name": name, "what": "逛", "how": "步行", "tip": ""}
                )
            days.append({"stops": stops})
        called = []

        def fetch(poi_id):
            called.append(poi_id)
            return details[poi_id]

        _display, parsed, _map_itinerary = itinerary.finalize_turn(
            _answer(days),
            [{"name": "maps_text_search", "content": json.dumps({"pois": pois})}],
            city="北京",
            fetch_detail=fetch,
        )
        self.assertIn("D20", called[:6])
        self.assertIn("D21", called[:6])
        payload = itinerary_view.map_payload(parsed, js_key="test-js-key")
        self.assertEqual(len(payload["days"][2]["stops"]), 3)
        self.assertEqual(len(payload["days"][2]["path"]), 3)

    def test_missing_day_three_name_is_searched_once_then_detailed(self):
        search = (
            '{"pois":[{"id":"B1","name":"故宫博物院"},'
            '{"id":"B2","name":"天坛公园"}]}'
        )
        answer = _answer(
            [
                {"stops": [{"slot": "上午", "name": "故宫博物院", "what": "逛", "how": "步行", "tip": ""}]},
                {"stops": [{"slot": "上午", "name": "天坛公园", "what": "逛", "how": "步行", "tip": ""}]},
                {"stops": [{"slot": "上午", "name": "景山公园", "what": "逛", "how": "步行", "tip": ""}]},
            ]
        )
        details = {
            "B1": '{"id":"B1","name":"故宫博物院","location":"116.397,39.918","city":"北京市"}',
            "B2": '{"id":"B2","name":"天坛公园","location":"116.411,39.882","city":"北京市"}',
            "J1": '{"id":"J1","name":"景山公园","location":"116.396,39.926","city":"北京市"}',
        }
        log = []

        def fetch_detail(poi_id):
            log.append(("detail", poi_id))
            return details[poi_id]

        def fetch_search(name):
            log.append(("search", name))
            return '{"pois":[{"id":"J1","name":"景山公园"}]}'

        _display, parsed, _map_itinerary = itinerary.finalize_turn(
            answer,
            [{"name": "maps_text_search", "content": search}],
            city="北京",
            fetch_detail=fetch_detail,
            fetch_search=fetch_search,
        )
        self.assertEqual(
            log,
            [("detail", "B1"), ("detail", "B2"), ("search", "景山公园"), ("detail", "J1")],
        )
        self.assertAlmostEqual(parsed.days[2].stops[0].lng, 116.396)
        payload = itinerary_view.map_payload(parsed, js_key="test-js-key")
        self.assertEqual(len(payload["days"][2]["path"]), 0)
        self.assertEqual(len(payload["days"][2]["stops"]), 1)

    def test_ambiguous_followup_search_does_not_fetch_detail(self):
        answer = _answer(
            [{"stops": [{"slot": "上午", "name": "景山", "what": "逛", "how": "步行", "tip": ""}]}]
        )
        log = []

        def fetch_detail(poi_id):
            log.append(("detail", poi_id))
            return "{}"

        def fetch_search(name):
            log.append(("search", name))
            return (
                '{"pois":[{"id":"J1","name":"景山公园"},'
                '{"id":"J2","name":"景山公园南门"}]}'
            )

        _display, parsed, _map_itinerary = itinerary.finalize_turn(
            answer,
            [{"name": "maps_text_search", "content": '{"pois":[]}'}],
            city="北京",
            fetch_detail=fetch_detail,
            fetch_search=fetch_search,
        )
        self.assertEqual(log, [("search", "景山")])
        self.assertIsNone(parsed.days[0].stops[0].lng)

    def test_host_lookups_stop_at_twelve_and_rotate_days(self):
        days = []
        for day_index in range(3):
            stops = []
            for stop_index in range(5):
                stops.append(
                    {
                        "slot": "上午",
                        "name": f"点{day_index}-{stop_index}",
                        "what": "逛",
                        "how": "步行",
                        "tip": "",
                    }
                )
            days.append({"stops": stops})
        log = []

        def fetch_search(name):
            log.append(("search", name))
            return json.dumps({"pois": [{"id": "id-" + name, "name": name}]})

        def fetch_detail(poi_id):
            log.append(("detail", poi_id))
            lng = 116.3
            return (
                f'{{"id":"{poi_id}","name":"{poi_id[3:]}",'
                f'"location":"{lng},39.9","city":"北京市"}}'
            )

        itinerary.finalize_turn(
            _answer(days),
            [{"name": "maps_text_search", "content": '{"pois":[]}'}],
            city="北京",
            fetch_detail=fetch_detail,
            fetch_search=fetch_search,
        )
        self.assertEqual(len(log), 12)
        self.assertIn(("search", "点2-0"), log)
        self.assertNotIn(("search", "点0-4"), log)
        search_at = log.index(("search", "点2-0"))
        self.assertLess(search_at, log.index(("detail", "id-点2-0")))

    def test_ambiguous_short_name_does_not_steal_a_coord(self):
        search = (
            '{"pois":[{"id":"B1","name":"杭州西湖风景名胜区"},'
            '{"id":"B3","name":"杭州西湖风景名胜区-苏堤春晓"}]}'
        )
        answer = _answer(
            [{"stops": [{"slot": "上午", "name": "西湖", "what": "逛", "how": "步行", "tip": ""}]}]
        )
        details = {
            "B1": '{"id":"B1","name":"杭州西湖风景名胜区","location":"120.121,30.223","city":"杭州市"}',
            "B3": '{"id":"B3","name":"杭州西湖风景名胜区-苏堤春晓","location":"120.130,30.240","city":"杭州市"}',
        }

        _display, parsed, map_itinerary = itinerary.finalize_turn(
            answer,
            [{"name": "maps_text_search", "content": search}],
            city="杭州",
            fetch_detail=lambda poi_id: details[poi_id],
        )
        self.assertIsNone(parsed.days[0].stops[0].lng)
        payload = itinerary_view.map_payload(map_itinerary, js_key="test-js-key")
        self.assertEqual(itinerary_view.map_card_mode(payload), "map")
        self.assertGreater(payload["days"][0]["stops"][0]["lng"], 115)

    def test_prose_without_json_still_maps_searched_places(self):
        search = '{"pois":[{"id":"P1","name":"故宫博物院"},{"id":"P2","name":"天坛公园"}]}'
        details = {
            "P1": '{"id":"P1","name":"故宫博物院","location":"116.397,39.918","city":"北京市"}',
            "P2": '{"id":"P2","name":"天坛公园","location":"116.411,39.882","city":"北京市"}',
        }
        display, text_itinerary, map_itinerary = itinerary.finalize_turn(
            "北京三日游，轻松看看。",
            [{"name": "maps_text_search", "content": search}],
            city="北京",
            fetch_detail=lambda poi_id: details[poi_id],
        )
        self.assertIn("北京三日游", display)
        self.assertIsNone(text_itinerary)
        payload = itinerary_view.map_payload(map_itinerary, js_key="test-js-key")
        self.assertEqual(itinerary_view.map_card_mode(payload), "map")
        self.assertEqual(len(payload["days"][0]["path"]), 2)
        self.assertGreater(payload["days"][0]["stops"][0]["lng"], 115)
        self.assertLess(payload["days"][0]["stops"][0]["lng"], 118)

    def test_geo_result_is_a_point(self):
        content = (
            '{"return":[{"city":"北京市","district":"东城区","street":"景山前街",'
            '"number":"4号","location":"116.397,39.918"}]}'
        )
        pois = itinerary.extract_pois([{"name": "maps_geo", "content": content}])
        self.assertEqual(len(pois), 1)
        self.assertAlmostEqual(pois[0].lng, 116.397, places=3)
        self.assertIn("景山前街", pois[0].name)


class FinalizeTurnTest(unittest.TestCase):
    def test_display_text_drops_json_and_keeps_prose(self):
        text = _answer(
            [{"stops": [{"slot": "上午", "name": "宽窄巷子", "what": "逛", "how": "地铁", "tip": "早去"}]}]
        )
        display, parsed, _map_itinerary = itinerary.finalize_turn(
            text, [_search(POI_PAYLOAD)], city="成都"
        )
        self.assertNotIn("```", display)
        self.assertIn("成都三天", display)
        self.assertAlmostEqual(parsed.days[0].stops[0].lng, 104.055, places=3)

    def test_unclosed_fence_is_hidden_and_not_parsed(self):
        display, parsed, _map_itinerary = itinerary.finalize_turn("上午去公园。\n```json\n{\"days\":[", [], city="成都")
        self.assertIsNone(parsed)
        self.assertIn("上午去公园", display)
        self.assertNotIn("```", display)

    def test_missing_block_keeps_text_and_itinerary_none(self):
        display, parsed, _map_itinerary = itinerary.finalize_turn("只问了天气。", [], city="成都")
        self.assertEqual(display, "只问了天气。")
        self.assertIsNone(parsed)


class PromptContractTest(unittest.TestCase):
    def test_system_prompt_requires_json_without_coords(self):
        import middleware

        class _Runtime:
            def __init__(self):
                self.state = {}
                self.context = middleware.trip_state_from_texts(["成都三天"])

        result = middleware.pin_cities_and_adcodes.before_model(
            {"messages": [HumanMessage(content="成都三天")]},
            _Runtime(),
        )
        content = result["messages"][0].content
        self.assertIsInstance(result["messages"][0], SystemMessage)
        self.assertIn("days", content)
        self.assertIn("坐标", content)
        self.assertIn("只问天气", content)
        self.assertIn("不要调用 maps_geo", content)


class StreamHandsOffTest(unittest.TestCase):
    def test_stream_answer_strips_json_and_returns_coords(self):
        """流式回答交给界面的是正文加行程，不是带坐标的代码块。"""
        import types

        from langchain_core.messages import AIMessage

        text = _answer(
            [
                {"stops": [{"slot": "上午", "name": "宽窄巷子", "what": "逛", "how": "地铁", "tip": "早去"}]},
                {"stops": [{"slot": "下午", "name": "大熊猫基地", "what": "看熊猫", "how": "打车", "tip": ""}]},
                {"stops": [{"slot": "晚上", "name": "锦里", "what": "吃饭", "how": "步行", "tip": "看关门"}]},
            ]
        )

        class _Agent:
            def stream(self, payload, config=None, context=None):
                return iter(
                    [
                        {"tools": {"messages": [_search(POI_PAYLOAD)]}},
                        {"model": {"messages": [AIMessage(content=text)]}},
                    ]
                )

            def invoke(self, payload, config=None, context=None):
                raise AssertionError("已经有最终答案，不应再 invoke")

        scripted = _Agent()
        if "agent" not in sys.modules:
            fake = types.ModuleType("agent")
            sys.modules["agent"] = fake
        sys.modules["agent"].agent = scripted
        if "ui" in sys.modules:
            ui = sys.modules["ui"]
        else:
            import ui
        ui.agent = scripted

        rows = list(ui.stream_answer("成都三天", [], False))
        _reasoning, display, _logs, _raw, parsed, _map_itinerary = rows[-1]
        self.assertNotIn("```", display)
        self.assertIn("成都三天", display)
        self.assertEqual(len(parsed.days), 3)
        self.assertAlmostEqual(parsed.days[0].stops[0].lng, 104.055, places=3)
        self.assertIsNone(parsed.days[2].stops[0].lng)
