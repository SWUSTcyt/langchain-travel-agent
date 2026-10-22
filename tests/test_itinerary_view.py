"""文字行程和地图数据：没钥匙不出图，单站不画线，没有行程就只留文字。"""

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


def _trip():
    return itinerary.Itinerary(
        days=(
            itinerary.Day(
                stops=(
                    itinerary.Stop("上午", "宽窄巷子", "逛巷子", "地铁", "早去", 104.055, 30.670),
                    itinerary.Stop("下午", "人民公园", "喝茶", "步行", "", 104.060, 30.660),
                )
            ),
            itinerary.Day(
                stops=(
                    itinerary.Stop("上午", "青城山", "爬山", "城际", "下午回城", 103.567, 30.900),
                )
            ),
        )
    )


class MapPayloadTest(unittest.TestCase):
    def test_map_payload_without_key(self):
        payload = itinerary_view.map_payload(_trip(), js_key="")
        self.assertFalse(payload["available"])
        self.assertIn("暂不可用", payload["message"])
        self.assertEqual(payload["days"], [])

    def test_single_stop_day_has_no_line(self):
        payload = itinerary_view.map_payload(_trip(), js_key="test-js-key")
        self.assertTrue(payload["available"])
        self.assertEqual(len(payload["days"][0]["path"]), 2)
        self.assertEqual(payload["days"][1]["path"], [])
        self.assertEqual(payload["days"][1]["stops"][0]["name"], "青城山")
        self.assertEqual(payload["days"][0]["stops"][0]["order"], 1)
        self.assertEqual(payload["days"][0]["stops"][0]["from"], "")
        self.assertEqual(payload["days"][0]["stops"][1]["from"], "宽窄巷子")
        self.assertNotEqual(payload["days"][0]["color"], payload["days"][1]["color"])

    def test_stop_without_coords_is_omitted_from_map(self):
        parsed = itinerary.Itinerary(
            days=(
                itinerary.Day(
                    stops=(
                        itinerary.Stop("上午", "宽窄巷子", "逛", "地铁", "", 104.055, 30.670),
                        itinerary.Stop("下午", "人民公园", "喝茶", "步行", "", None, None),
                    )
                ),
            )
        )
        payload = itinerary_view.map_payload(parsed, js_key="test-js-key")
        self.assertEqual(len(payload["days"][0]["stops"]), 1)
        self.assertEqual(payload["days"][0]["path"], [])


class RenderTest(unittest.TestCase):
    def test_none_itinerary_keeps_the_map_column(self):
        html, map_html = itinerary_view.render_turn(None, "只问了天气。", js_key="test-js-key")
        self.assertIn("只问了天气。", html)
        self.assertNotIn("data-day", html)
        self.assertNotIn("map-hidden", map_html)
        self.assertIn("还没有地点", map_html)

    def test_missing_key_keeps_column_with_message(self):
        _html, map_html = itinerary_view.render_turn(None, "只问了天气。", js_key="")
        self.assertNotIn("map-hidden", map_html)
        self.assertIn("暂不可用", map_html)

    def test_days_have_tabs_and_stop_ids(self):
        html, map_html = itinerary_view.render_turn(_trip(), "成都三天", js_key="test-js-key")
        self.assertIn("宽窄巷子", html)
        self.assertIn("怎么去", html)
        self.assertIn('data-day="1"', html)
        self.assertIn('id="stop-1-0"', html)
        self.assertIn("青城山", html)
        self.assertIn("trip-map-data", map_html)
        self.assertNotIn("test-js-key", html)
        self.assertNotIn("test-js-key", map_html)

    def test_hangzhou_payload_replaces_chengdu_numbers(self):
        hangzhou = itinerary.Itinerary(
            days=(
                itinerary.Day(
                    stops=(
                        itinerary.Stop("上午", "西湖", "逛", "步行", "", 120.121, 30.223),
                        itinerary.Stop("下午", "断桥", "看桥", "步行", "", 120.149, 30.260),
                    )
                ),
            )
        )
        text = itinerary_view.next_map_payload(hangzhou, "test-js-key", has_text=True)
        self.assertIn("120.121", text)
        self.assertNotIn("104.", text)
        self.assertIsNone(
            itinerary_view.next_map_payload(None, "test-js-key", has_text=False)
        )

    def test_open_page_uses_empty_china_map(self):
        payload = itinerary_view.map_payload(None, js_key="test-js-key")
        self.assertTrue(payload["available"])
        self.assertEqual(payload["days"], [])
        self.assertIn("还没有地点", payload["message"])
        self.assertGreaterEqual(payload["center"][0], 73)
        self.assertLessEqual(payload["center"][0], 135)
        self.assertGreaterEqual(payload["center"][1], 18)
        self.assertLessEqual(payload["center"][1], 54)
        self.assertLessEqual(payload["zoom"], 5)
        self.assertEqual(itinerary_view.map_card_mode(payload), "map")
        css = (ROOT / "assets" / "custom.css").read_text(encoding="utf-8")
        self.assertNotIn("#ta-map-card.map-off { display: none", css)

    def test_waiting_question_drops_previous_city(self):
        previous = itinerary_view.map_payload_text(_trip(), "test-js-key")
        waiting = itinerary_view.next_map_payload(
            None, "test-js-key", has_text=True, previous=previous, finished=False
        )
        self.assertIn("还没有地点", waiting)
        self.assertNotIn("104.055", waiting)
        self.assertNotIn("宽窄巷子", waiting)

    def test_failed_or_weather_restores_previous_trip(self):
        previous = itinerary_view.map_payload_text(_trip(), "test-js-key")
        restored = itinerary_view.next_map_payload(
            None, "test-js-key", has_text=True, previous=previous, finished=True
        )
        self.assertIn("104.055", restored)
        self.assertIn("宽窄巷子", restored)
        self.assertEqual(itinerary_view.map_card_mode(json.loads(restored)), "map")
        empty = itinerary_view.next_map_payload(
            None, "test-js-key", has_text=True, previous="", finished=True
        )
        self.assertIn("还没有地点", empty)
        self.assertNotIn("104.055", empty)
        self.assertNotIn("宽窄巷子", empty)

    def test_two_cards_do_not_share_day_ids(self):
        chengdu = _trip()
        hangzhou = itinerary.Itinerary(
            days=(
                itinerary.Day(
                    stops=(
                        itinerary.Stop("上午", "西湖", "逛", "步行", "", 120.121, 30.223),
                    )
                ),
            )
        )
        html = itinerary_view.conversation_html(
            [
                itinerary_view.freeze_exchange("t1", "成都三天", "成都", chengdu, chengdu, "k"),
                itinerary_view.freeze_exchange("t2", "杭州一天", "杭州", hangzhou, hangzhou, "k"),
            ],
            selected_id="t2",
            js_key="k",
        )
        self.assertIn('data-turn="t1"', html)
        self.assertIn('data-turn="t2" data-selected="true"', html)
        self.assertIn('id="t1-day-1"', html)
        self.assertIn('id="t2-day-0"', html)
        self.assertIn('id="t1-stop-0-0"', html)
        self.assertNotIn('id="day-0"', html)
        self.assertIn("120.121", html)
        self.assertIn("104.055", html)
        t1 = html.split('data-turn="t2"', 1)[0]
        self.assertNotIn("120.121", t1)

    def test_weather_reply_is_not_a_day_card(self):
        html = itinerary_view.conversation_html(
            [
                itinerary_view.freeze_exchange("t1", "成都三天", "成都", _trip(), _trip(), "k"),
                itinerary_view.freeze_exchange("t2", "丽江今天天气", "今天多云。", None, None, "k"),
            ],
            selected_id="t1",
            js_key="k",
        )
        weather = html.split('class="turn-note"', 1)[1]
        self.assertIn("今天多云", weather)
        self.assertNotIn("data-day", weather)
        self.assertIn('data-turn="t1" data-selected="true"', html)

    def test_pending_keeps_the_previous_card(self):
        html = itinerary_view.conversation_html(
            [itinerary_view.freeze_exchange("t1", "成都三天", "成都", _trip(), _trip(), "k")],
            selected_id=None,
            pending_question="杭州一天",
            js_key="k",
        )
        self.assertIn("宽窄巷子", html)
        self.assertIn("杭州一天", html)
        self.assertIn("正在查", html)
        self.assertNotIn('data-selected="true"', html)

    def test_day_click_uses_the_card_and_does_not_destroy_the_map(self):
        js = (ROOT / "assets" / "trip-map.js").read_text(encoding="utf-8")
        body = js.split("function selectDay", 1)[1].split("function findDayButton", 1)[0]
        self.assertIn("scope", body)
        self.assertNotIn("destroyMap", body)
        self.assertIn(".turn-card", js)
        self.assertIn("closest", js)

    def test_ask_row_sits_in_the_left_column(self):
        ui = (ROOT / "ui.py").read_text(encoding="utf-8")
        text = ui.find('elem_id="ta-text-card"')
        ask = ui.find('elem_id="ta-ask-row"')
        map_card = ui.find('elem_id="ta-map-card"')
        self.assertLess(text, ask)
        self.assertLess(ask, map_card)

    def test_chat_log_is_there_before_any_question(self):
        empty = itinerary_view.conversation_html([], js_key="k")
        self.assertIn('id="ta-chat-log"', empty)
        css = (ROOT / "assets" / "custom.css").read_text(encoding="utf-8")
        box = css.split("#ta-chat-log", 1)[1].split("}", 1)[0]
        self.assertIn("border", box)
        self.assertIn("100vh", box)
        first = itinerary_view.freeze_exchange("t1", "成都三天", "成都", _trip(), _trip(), "k")
        second = itinerary_view.freeze_exchange("t2", "杭州一天", "杭州", None, None, "k")
        filled = itinerary_view.conversation_html([first, second], selected_id="t1", js_key="k")
        self.assertEqual(filled.count('id="ta-chat-log"'), 1)
        self.assertIn("成都三天", filled)
        self.assertIn("杭州一天", filled)
        self.assertIn('data-fill="北京三日游"', filled)
        self.assertLess(filled.index("成都三天"), filled.index('data-fill="北京三日游"'))
        self.assertNotIn("想去哪里", filled)
        empty_title = empty.index("想去哪里")
        self.assertLess(empty_title, empty.index('data-fill="北京三日游"'))

    def test_last_day_with_two_stops_has_a_line(self):
        trip = itinerary.Itinerary(
            days=(
                itinerary.Day(
                    stops=(
                        itinerary.Stop("上午", "宽窄巷子", "逛", "地铁", "", 104.055, 30.670),
                    )
                ),
                itinerary.Day(
                    stops=(
                        itinerary.Stop("上午", "西湖", "逛", "步行", "", 120.121, 30.223),
                        itinerary.Stop("下午", "断桥", "看桥", "步行", "", 120.149, 30.260),
                    )
                ),
            )
        )
        payload = itinerary_view.map_payload(trip, js_key="test-js-key")
        self.assertEqual(payload["days"][0]["path"], [])
        self.assertEqual(len(payload["days"][0]["stops"]), 1)
        self.assertEqual(len(payload["days"][1]["path"]), 2)
        draw = (ROOT / "assets" / "trip-map.js").read_text(encoding="utf-8")
        draw = draw.split("function draw", 1)[1].split("function selectDay", 1)[0]
        self.assertIn("stops.length >= 2", draw)
        line = (ROOT / "assets" / "trip-map.js").read_text(encoding="utf-8")
        line = line.split("function addLine", 1)[1].split("function draw", 1)[0]
        self.assertNotIn("strokeWeight: 14", line)
        self.assertNotIn("#ffffff", line)

    def test_pin_has_no_large_white_plate(self):
        css = (ROOT / "assets" / "custom.css").read_text(encoding="utf-8")
        pin = css.split(".map-pin {", 1)[1].split("}", 1)[0]
        self.assertNotIn("#fff", pin)
        self.assertIn("transparent", pin)

    def test_pin_shows_number_not_place_name(self):
        js = (ROOT / "assets" / "trip-map.js").read_text(encoding="utf-8")
        marker = js.split("function markerHtml", 1)[1].split("function esc", 1)[0]
        popup = js.split("function popupHtml", 1)[1].split("function addLine", 1)[0]
        self.assertNotIn("stop.name", marker)
        self.assertIn("background:' + color", marker)
        self.assertNotIn("currentColor", marker)
        self.assertIn("stop.order", marker)
        self.assertIn("stop.name", popup)

    def test_pending_shows_the_sent_question(self):
        html = itinerary_view.render_pending_html("成都三天，轻松不赶")
        self.assertIn("正在查", html)
        self.assertIn("成都三天，轻松不赶", html)
        self.assertNotIn("这句话已经发出去了", html)
        self.assertNotIn("轻松一点", html)

    def test_page_head_omits_amap_when_key_missing(self):
        head = itinerary_view.page_head("", "")
        self.assertNotIn("webapi.amap.com", head)

    def test_page_head_uses_given_key(self):
        head = itinerary_view.page_head("test-js-key", "test-security")
        self.assertIn("test-js-key", head)
        self.assertIn("test-security", head)
        self.assertIn("webapi.amap.com", head)
