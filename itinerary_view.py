"""把结构化行程画成文字 HTML 和地图数据。不调用模型，也不读取密钥以外的环境。"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from itinerary import Itinerary


# 相邻两天拉开色相，避免当天的线和另一天的点用成同一个颜色。
_COLORS = ("#0f7c9c", "#ea580c", "#7c3aed", "#be123c", "#15803d", "#1d4ed8", "#a16207")
_JS_PATH = Path(__file__).resolve().parent / "assets" / "trip-map.js"


def map_payload(itinerary: Itinerary | None, js_key: str | None = None, *, turn_id: str | None = None) -> dict:
    """没有 Web 端 JS key 时不带坐标。某一天少于两个点时不给路线。"""
    if not (js_key or "").strip():
        return {"available": False, "message": "地图暂不可用", "days": []}
    if itinerary is None:
        # 还没问、或这一句的地点还没回来：中国范围的空地图，不带上一座城市的点。
        return {
            "available": True,
            "message": "还没有地点。",
            "days": [],
            "center": [104.2, 35.8],
            "zoom": 4,
        }
    days = []
    for index, day in enumerate(itinerary.days):
        stops = []
        for stop_index, stop in enumerate(day.stops):
            if stop.lng is None or stop.lat is None:
                continue
            stops.append(
                {
                    "name": stop.name,
                    "lng": stop.lng,
                    "lat": stop.lat,
                    "id": f"{turn_id}-stop-{index}-{stop_index}" if turn_id else f"stop-{index}-{stop_index}",
                    "order": len(stops) + 1,
                    "from": stops[-1]["name"] if stops else "",
                    "slot": stop.slot,
                    "how": stop.how,
                }
            )
        path = [[item["lng"], item["lat"]] for item in stops] if len(stops) >= 2 else []
        days.append(
            {
                "stops": stops,
                "path": path,
                "color": _COLORS[index % len(_COLORS)],
            }
        )
    return {
        "available": True,
        "message": "点某一天，只画这一天的先后顺序。",
        "days": days,
    }


def render_itinerary_html(
    itinerary: Itinerary | None,
    fallback_text: str = "",
    *,
    turn_id: str | None = None,
) -> str:
    """有行程就画出天数和每一站。没有行程时只保留这段文字。

    带上 turn_id 后，天数和站点编号只属于这一张卡，不会和另一次问答撞在一起。
    """
    if itinerary is None:
        text = (fallback_text or "").strip()
        if not text:
            return (
                '<div class="trip-text empty-ask">'
                '<p class="ask">这次行程</p>'
                "<h1>想去哪里，待几天？</h1>"
                '<p class="lead">说一个城市和天数。结果会按天列出怎么走，地图只画你选中那一天，从第一站连到最后一站。</p>'
                f"{_example_picks(False)}</div>"
            )
        return f'<article class="trip-answer">{html.escape(text)}</article>'

    tabs = ['<div class="tabs" role="tablist">']
    sections = []
    prefix = f"{html.escape(turn_id)}-" if turn_id else ""
    turn_attr = f' data-turn="{html.escape(turn_id)}"' if turn_id else ""
    for index, day in enumerate(itinerary.days):
        pressed = "true" if index == 0 else "false"
        tabs.append(
            f'<button type="button" data-day="{index}"{turn_attr} aria-pressed="{pressed}">'
            f"第 {index + 1} 天</button>"
        )
        title = " → ".join(stop.name for stop in day.stops)
        faded = "" if index == 0 else " faded"
        rows = "".join(
            _stop_html(stop, f"{prefix}stop-{index}-{stop_index}")
            for stop_index, stop in enumerate(day.stops)
        )
        sections.append(
            f'<section class="day{faded}" id="{prefix}day-{index}">'
            f"<h2>第 {index + 1} 天 · {html.escape(title)}</h2>{rows}</section>"
        )
    tabs.append("</div>")
    return '<div class="trip-text">' + "".join(tabs) + "".join(sections) + "</div>"


def render_map_html(payload: dict, *, show: bool = True) -> str:
    """右栏一直留着。没有 key 时写明暂不可用，不把这一栏收起来。"""
    if not show:
        return '<div class="map-hidden" hidden></div>'
    if not payload.get("available"):
        message = html.escape(payload.get("message") or "地图暂不可用")
        return f'<div id="trip-map" class="map-fallback">{message}</div>'
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    legend = html.escape(payload.get("message") or "")
    return (
        '<div id="trip-map" class="map-canvas"></div>'
        f'<p id="trip-map-legend">{legend}</p>'
        f'<textarea id="trip-map-data" hidden readonly>{data}</textarea>'
    )


def map_card_mode(payload: dict | None) -> str:
    """hidden：完全没有载荷。message：没有 key，右栏说明原因。map：空的默认图或有点的行程图。"""
    if not payload:
        return "hidden"
    if not payload.get("available"):
        return "message"
    return "map"


def payload_has_stops(text: str | None) -> bool:
    """这段地图 JSON 里是否已经有坐标点。默认图和空字符串都算没有。"""
    if not text:
        return False
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return False
    return any((day.get("stops") or []) for day in (data.get("days") or []))


def next_map_payload(
    itinerary: Itinerary | None,
    js_key: str | None,
    *,
    has_text: bool,
    previous: str | None = None,
    finished: bool = False,
):
    """有新行程就换成这张图。

    这一句还在查时，返回没有点的默认图，不留上一座城市。
    这一句结束了却没有新行程（只问天气，或没查到）：有上一张就放回去，没有就停在默认图。
    """
    if itinerary is not None:
        return map_payload_text(itinerary, js_key)
    if finished:
        if payload_has_stops(previous):
            return previous
        return map_payload_text(None, js_key)
    if has_text:
        return map_payload_text(None, js_key)
    return None


def map_payload_text(itinerary: Itinerary | None, js_key: str | None = None) -> str:
    """给页面上那个固定地图读的 JSON。地图容器不跟着这段文字一起换掉。"""
    return json.dumps(map_payload(itinerary, js_key=js_key), ensure_ascii=False)


def _payload_stops(payload: dict | None) -> bool:
    if not payload:
        return False
    return any((day.get("stops") or []) for day in (payload.get("days") or []))


def freeze_exchange(turn_id, question, answer, text_itinerary, map_itinerary, js_key) -> dict:
    """一句结束时存下这一次。有几天行程才是卡片，坐标一起冻住。"""
    if text_itinerary is None:
        return {
            "id": turn_id,
            "kind": "text",
            "question": question or "",
            "answer": answer or "",
        }
    payload = map_payload(text_itinerary, js_key, turn_id=turn_id)
    if not _payload_stops(payload) and map_itinerary is not None:
        payload = map_payload(map_itinerary, js_key, turn_id=turn_id)
    payload = dict(payload)
    payload["turnId"] = turn_id
    payload["question"] = question or ""
    payload["selectedDay"] = 0
    return {
        "id": turn_id,
        "kind": "itinerary",
        "question": question or "",
        "answer": answer or "",
        "body_html": render_itinerary_html(text_itinerary, turn_id=turn_id),
        "payload": payload,
    }


def exchange_map_text(record) -> str | None:
    """这张行程卡要交给地图的 JSON。普通回答没有这份坐标。"""
    if not record or record.get("kind") != "itinerary" or not record.get("payload"):
        return None
    return json.dumps(record["payload"], ensure_ascii=False)


def last_itinerary_id(items) -> str | None:
    """从后往前找最近一张行程卡。只问天气不会变成新的选中项。"""
    for item in reversed(list(items or [])):
        if item.get("kind") == "itinerary":
            return item.get("id")
    return None


def next_turn_id(items) -> str:
    """下一张卡的编号。只认 t 加数字，避免和天数混用。"""
    highest = 0
    for item in items or []:
        raw = str(item.get("id") or "")
        if raw.startswith("t") and raw[1:].isdigit():
            highest = max(highest, int(raw[1:]))
    return f"t{highest + 1}"


def _example_picks(follow: bool) -> str:
    """三张示例。有对话以后贴在聊天框最下面，不重复开场大标题。"""
    extra = " picks-follow" if follow else ""
    lead = '<p class="ask">还可以这样问</p>' if follow else ""
    return (
        f'<div class="picks{extra}">'
        f"{lead}"
        '<button type="button" data-fill="成都三天，轻松不赶"><b>成都 · 三天</b><span>巷子、茶馆，不赶路</span></button>'
        '<button type="button" data-fill="杭州一天，西湖边走走"><b>杭州 · 一天</b><span>西湖边上慢慢走</span></button>'
        '<button type="button" data-fill="北京三日游"><b>北京 · 三天</b><span>城里的经典路线</span></button>'
        "</div>"
    )


def conversation_html(items, *, selected_id=None, pending_question: str = "", js_key: str = "") -> str:
    """左列聊天框从打开就在。新的问答加进同一个框。"""
    if not items and not (pending_question or "").strip():
        inner = render_itinerary_html(None)
    else:
        parts = [_exchange_html(item, selected=item.get("id") == selected_id, js_key=js_key) for item in items]
        if (pending_question or "").strip():
            parts.append(render_pending_html(pending_question))
        parts.append(_example_picks(True))
        inner = "".join(parts)
    return f'<div class="trip-thread" id="ta-chat-log">{inner}</div>'


def _exchange_html(item: dict, *, selected: bool, js_key: str) -> str:
    question = html.escape(item.get("question") or "")
    head = f'<p class="who">你</p><p class="said">{question}</p>'
    if item.get("kind") != "itinerary":
        answer = html.escape(item.get("answer") or "")
        return (
            f'<article class="turn-note">{head}'
            f'<p class="who">回答</p><div class="trip-answer">{answer}</div></article>'
        )
    turn_id = html.escape(str(item.get("id") or ""))
    body = item.get("body_html") or ""
    payload = dict(item.get("payload") or {})
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    picked = "true" if selected else "false"
    return (
        f'<article class="turn-card" data-turn="{turn_id}" data-selected="{picked}">'
        f"{head}<p class=\"who\">回答</p>{body}"
        f'<textarea class="turn-map" hidden readonly>{data}</textarea></article>'
    )


def render_pending_html(question: str) -> str:
    """发出去之后、答案回来之前，把原话留在主区域，避免只剩下输入框占位符。"""
    text = html.escape((question or "").strip())
    return (
        '<div class="trip-text pending">'
        '<p class="ask">正在查</p>'
        f"<h1>{text}</h1>"
        "<section class=\"day\">"
        "<p>正在查这座城市的地点和天气。结果出来后，这里换成每天的安排，右边标出从哪一站到下一站。</p>"
        "</section></div>"
    )


def render_turn(itinerary: Itinerary | None, text: str, js_key: str | None = None):
    """返回左栏 HTML 和右栏 HTML。"""
    payload = map_payload(itinerary, js_key=js_key)
    return (
        render_itinerary_html(itinerary, fallback_text=text),
        render_map_html(payload, show=True),
    )


def page_head(js_key: str | None, security_code: str | None) -> str:
    """注入地图脚本。没有 key 时不请求高德。"""
    client = _JS_PATH.read_text(encoding="utf-8")
    client_tag = f"<script>\n{client}\n</script>"
    key = (js_key or "").strip()
    if not key or re.fullmatch(r"[A-Za-z0-9_-]+", key) is None:
        return client_tag
    security = json.dumps(security_code or "")
    return (
        f"<script>window._AMapSecurityConfig={{securityJsCode:{security}}};</script>"
        f'<script src="https://webapi.amap.com/maps?v=2.0&key={key}"></script>'
        + client_tag
    )


def _stop_html(stop, stop_id: str) -> str:
    how = f'<p class="go">怎么去：{html.escape(stop.how)}</p>' if stop.how else ""
    tip = f'<p class="tip">提醒：{html.escape(stop.tip)}</p>' if stop.tip else ""
    return (
        f'<div class="stop" id="{stop_id}">'
        f'<span class="when">{html.escape(stop.slot)}</span>'
        f"<div><b>{html.escape(stop.name)}</b>"
        f"<p>{html.escape(stop.what)}</p>{how}{tip}</div></div>"
    )
