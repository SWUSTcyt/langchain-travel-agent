"""文字页和地图数据的三种用法。不调用模型，也不连接地图。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import itinerary  # noqa: E402
import itinerary_view  # noqa: E402


def _one_day(*stops):
    return itinerary.Itinerary(days=(itinerary.Day(stops=tuple(stops)),))


def example_two_stops_get_a_line():
    """两个有坐标的地点会给出路线上的两个点。"""
    parsed = _one_day(
        itinerary.Stop("上午", "宽窄巷子", "逛", "地铁", "", 104.055, 30.670),
        itinerary.Stop("下午", "人民公园", "喝茶", "步行", "", 104.060, 30.660),
    )
    payload = itinerary_view.map_payload(parsed, js_key="demo-key")
    assert payload["available"] is True
    assert len(payload["days"][0]["path"]) == 2


def example_one_stop_has_no_line():
    """只有一站时标点，不画线。"""
    parsed = _one_day(
        itinerary.Stop("上午", "青城山", "爬山", "城际", "", 103.567, 30.900)
    )
    payload = itinerary_view.map_payload(parsed, js_key="demo-key")
    assert payload["days"][0]["path"] == []
    assert payload["days"][0]["stops"][0]["name"] == "青城山"


def example_missing_key_keeps_the_column():
    """没有 JS key 时右栏仍在，写明地图暂不可用，文字还在。"""
    text_html, map_html = itinerary_view.render_turn(None, "今天多云。", js_key="")
    assert "今天多云。" in text_html
    assert "map-hidden" not in map_html
    assert "暂不可用" in map_html
    assert itinerary_view.map_payload(_one_day(
        itinerary.Stop("上午", "宽窄巷子", "逛", "地铁", "", 104.055, 30.670)
    ), js_key="")["available"] is False


def example_waiting_drops_the_previous_city():
    """新问题的地点还没回来时，地图先回到没有点的默认图。"""
    previous = itinerary_view.map_payload_text(_one_day(
        itinerary.Stop("上午", "宽窄巷子", "逛", "地铁", "", 104.055, 30.670)
    ), "demo-key")
    waiting = itinerary_view.next_map_payload(
        None, "demo-key", has_text=True, previous=previous, finished=False
    )
    assert "还没有地点" in waiting
    assert "104.055" not in waiting
    restored = itinerary_view.next_map_payload(
        None, "demo-key", has_text=True, previous=previous, finished=True
    )
    assert "104.055" in restored


def example_two_trips_keep_separate_days():
    """成都和杭州两张卡的第 1 天编号不同，后一张被标成选中。"""
    chengdu = _one_day(
        itinerary.Stop("上午", "宽窄巷子", "逛", "地铁", "", 104.055, 30.670),
        itinerary.Stop("下午", "人民公园", "喝茶", "步行", "", 104.060, 30.660),
    )
    hangzhou = _one_day(
        itinerary.Stop("上午", "西湖", "逛", "步行", "", 120.121, 30.223),
    )
    html = itinerary_view.conversation_html(
        [
            itinerary_view.freeze_exchange("t1", "成都三天", "成都", chengdu, chengdu, "demo-key"),
            itinerary_view.freeze_exchange("t2", "杭州一天", "杭州", hangzhou, hangzhou, "demo-key"),
        ],
        selected_id="t2",
        js_key="demo-key",
    )
    assert 'id="t1-day-0"' in html
    assert 'id="t2-day-0"' in html
    assert 'data-turn="t2" data-selected="true"' in html


if __name__ == "__main__":
    example_two_stops_get_a_line()
    example_one_stop_has_no_line()
    example_missing_key_keeps_the_column()
    example_waiting_drops_the_previous_city()
    example_two_trips_keep_separate_days()
    print("examples ok")
