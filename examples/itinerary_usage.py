"""结构化行程的三种用法。不调用模型，也不连接地图。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import itinerary  # noqa: E402


def example_match_tool_coords():
    """地点名对上本轮搜索结果时，坐标用工具的，不用模型写的。"""
    answer = (
        "上午去宽窄巷子。\n\n```json\n"
        + json.dumps(
            {
                "days": [
                    {
                        "stops": [
                            {
                                "slot": "上午",
                                "name": "宽窄巷子",
                                "what": "逛巷子",
                                "how": "地铁",
                                "tip": "早去",
                                "lng": 1,
                                "lat": 2,
                            }
                        ]
                    }
                ]
            },
            ensure_ascii=False,
        )
        + "\n```"
    )
    tools = [
        {
            "name": "maps_text_search",
            "content": json.dumps(
                {"pois": [{"name": "宽窄巷子", "location": "104.055,30.670", "cityname": "成都市"}]}
            ),
        }
    ]
    display, parsed, _map_itinerary = itinerary.finalize_turn(answer, tools, city="成都")
    assert "```" not in display
    assert abs(parsed.days[0].stops[0].lng - 104.055) < 0.001


def example_unknown_place_stays_off_map():
    """工具没返回这个地点时，文字保留，坐标为空。"""
    answer = (
        "下午喝茶。\n\n```json\n"
        '{"days":[{"stops":[{"slot":"下午","name":"人民公园","what":"喝茶","how":"步行","tip":""}]}]}'
        "\n```"
    )
    _display, parsed, _map_itinerary = itinerary.finalize_turn(answer, [], city="成都")
    assert parsed.days[0].stops[0].lng is None


def example_weather_only_has_no_itinerary():
    """没附代码块就不当成新行程。"""
    display, parsed, _map_itinerary = itinerary.finalize_turn("丽江今天多云。", [], city="丽江")
    assert display == "丽江今天多云。"
    assert parsed is None


if __name__ == "__main__":
    example_match_tool_coords()
    example_unknown_place_stays_off_map()
    example_weather_only_has_no_itinerary()
    print("examples ok")
