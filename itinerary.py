"""从最终答案和高德搜索结果整理结构化行程。坐标只来自工具，不来自模型。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


ITINERARY_PROMPT = (
    "\n【行程结构】若本轮是在安排或修改行程，在最终答案正文之后另起一行，"
    "附一个 json 代码块，格式为："
    '\n```json\n{"days":[{"stops":[{"slot":"上午","name":"地点名",'
    '"what":"做什么","how":"怎么去","tip":"提醒"}]}]}\n```\n'
    "json 里不要写坐标。地点名必须来自本轮 maps_text_search 的结果。"
    "只问天气、不改行程时，不要附这个代码块。"
)

_SEARCH_TOOL = "maps_text_search"


@dataclass(frozen=True)
class Poi:
    name: str
    lng: float
    lat: float
    city: str


@dataclass(frozen=True)
class PlaceRef:
    """关键词搜索返回的地点。这个接口没有坐标，坐标要再查详情。"""

    name: str
    poi_id: str


@dataclass(frozen=True)
class Stop:
    slot: str
    name: str
    what: str
    how: str
    tip: str
    lng: float | None = None
    lat: float | None = None


@dataclass(frozen=True)
class Day:
    stops: tuple[Stop, ...]


@dataclass(frozen=True)
class Itinerary:
    days: tuple[Day, ...]


_DETAIL_TOOL = "maps_search_detail"
_GEO_TOOL = "maps_geo"
_DETAIL_LIMIT = 6
_HOST_LOOKUP_LIMIT = 12


def extract_pois(tool_messages) -> list[Poi]:
    """从详情、地理编码，或已经带 location 的搜索结果里取坐标。"""
    found: list[Poi] = []
    for message in tool_messages or []:
        tool_name = _message_name(message)
        payload = _load_json(_unwrap_content(_message_content(message)))
        if tool_name == _GEO_TOOL:
            found.extend(_pois_from_geo(payload))
            continue
        if tool_name not in (_SEARCH_TOOL, _DETAIL_TOOL):
            continue
        for item in _poi_items(payload):
            poi = _poi_from_item(item)
            if poi is not None:
                found.append(poi)
    return found


def extract_place_refs(tool_messages) -> list[PlaceRef]:
    """关键词搜索里的 id 和名称，用来按名称再查详情坐标。"""
    found: list[PlaceRef] = []
    for message in tool_messages or []:
        if _message_name(message) != _SEARCH_TOOL:
            continue
        payload = _load_json(_unwrap_content(_message_content(message)))
        for item in _poi_items(payload):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            poi_id = str(item.get("id") or "").strip()
            if name and poi_id:
                found.append(PlaceRef(name=name, poi_id=poi_id))
    return found


class _HostBudget:
    """页面自己补搜和查详情共用的次数。一条一条扣，不并发。"""

    def __init__(self, limit: int):
        self.left = limit
        self.seen_ids: set[str] = set()

    def take(self) -> bool:
        if self.left <= 0:
            return False
        self.left -= 1
        return True


def collect_pois(
    tool_messages,
    parsed: Itinerary | None,
    fetch_detail=None,
    fetch_search=None,
) -> list[Poi]:
    """先用工具里已有的坐标。名字没对上时按地点名再搜一次，唯一命中才查详情。"""
    pois = extract_pois(tool_messages)
    if fetch_detail is None:
        return pois
    refs = extract_place_refs(tool_messages)
    budget = _HostBudget(_HOST_LOOKUP_LIMIT)
    if parsed is not None:
        pois = _fill_stop_coords(pois, parsed, refs, fetch_detail, fetch_search, budget)
    if len([poi for poi in pois if poi.lng is not None]) < 2:
        rest = [ref.poi_id for ref in refs if ref.poi_id not in budget.seen_ids]
        pois = _fetch_details(pois, rest, fetch_detail, budget)
    return pois


def _fill_stop_coords(pois, parsed, refs, fetch_detail, fetch_search, budget: _HostBudget):
    """按天轮流：已有唯一编号就查详情，没有就补搜一次。"""
    queues: list[list[tuple[str, str]]] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for day in parsed.days:
        queue: list[tuple[str, str]] = []
        for stop in day.stops:
            name = (stop.name or "").strip()
            ref = _ref_for_stop(name, refs)
            if ref is not None and ref.poi_id not in seen_ids:
                queue.append(("detail", ref.poi_id))
                seen_ids.add(ref.poi_id)
            elif ref is None and fetch_search is not None and name and name not in seen_names:
                queue.append(("search", name))
                seen_names.add(name)
        queues.append(queue)
    while budget.left > 0 and any(queues):
        progressed = False
        for queue in queues:
            if budget.left <= 0 or not queue:
                continue
            kind, value = queue.pop(0)
            progressed = True
            if kind == "detail":
                pois = _fetch_details(pois, [value], fetch_detail, budget)
                continue
            if not budget.take():
                break
            try:
                content = fetch_search(value)
            except Exception:
                continue
            found = extract_place_refs([{"name": _SEARCH_TOOL, "content": content}])
            matched = _ref_for_stop(value, found)
            if matched is not None and matched.poi_id not in budget.seen_ids:
                queue.insert(0, ("detail", matched.poi_id))
        if not progressed:
            break
    return pois


def _fetch_details(pois: list[Poi], poi_ids: list[str], fetch_detail, budget: _HostBudget) -> list[Poi]:
    found = list(pois)
    for poi_id in poi_ids:
        if poi_id in budget.seen_ids or not budget.take():
            continue
        budget.seen_ids.add(poi_id)
        try:
            content = fetch_detail(poi_id)
        except Exception:
            continue
        found.extend(extract_pois([{"name": _DETAIL_TOOL, "content": content}]))
    return found


def parse_itinerary(answer_text: str) -> Itinerary | None:
    """读最终答案末尾的 json 代码块。没有、损坏、或没有有效地点时返回 None。"""
    raw, _ = _split_json_fence(answer_text or "")
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    days_raw = payload.get("days")
    if not isinstance(days_raw, list) or not days_raw:
        return None
    days: list[Day] = []
    for day in days_raw:
        stops = _stops_from_day(day)
        if stops is None:
            return None
        days.append(Day(tuple(stops)))
    if not any(day.stops for day in days):
        return None
    return Itinerary(tuple(days))


def attach_coords(parsed: Itinerary, pois: list[Poi], city: str | None = None) -> Itinerary:
    """按地点名补坐标。同城同名多条、或对不上城市时不上图。模型写过的坐标不保留。"""
    index = _coord_index(pois, city)
    days = []
    for day in parsed.days:
        stops = []
        for stop in day.stops:
            lng, lat = index.get(stop.name.strip(), (None, None))
            stops.append(
                Stop(stop.slot, stop.name, stop.what, stop.how, stop.tip, lng, lat)
            )
        days.append(Day(tuple(stops)))
    return Itinerary(tuple(days))


def finalize_turn(
    answer_text: str,
    tool_messages,
    city: str | None = None,
    fetch_detail=None,
    fetch_search=None,
):
    """返回展示文字、给左边看的行程、给地图用的行程。

    模型没写出结构，或地点名对不上时，地图仍用这次查到的坐标，不再整块消失。
    """
    _, display = _split_json_fence(answer_text or "")
    parsed = parse_itinerary(answer_text)
    pois = collect_pois(
        tool_messages,
        parsed,
        fetch_detail=fetch_detail,
        fetch_search=fetch_search,
    )
    text_itinerary = attach_coords(parsed, pois, city=city) if parsed is not None else None
    map_itinerary = text_itinerary if _has_coords(text_itinerary) else _itinerary_from_pois(pois, city)
    return display, text_itinerary, map_itinerary


def tool_messages_from_events(events) -> list:
    """从 agent.stream 的事件里取出工具消息。"""
    found = []
    for event in events or []:
        if not isinstance(event, dict):
            continue
        for key in ("tools", "tool"):
            blob = event.get(key)
            if isinstance(blob, dict):
                messages = blob.get("messages")
                if isinstance(messages, list):
                    found.extend(messages)
            elif isinstance(blob, list):
                found.extend(blob)
    return found


def _stops_from_day(day) -> list[Stop] | None:
    if not isinstance(day, dict):
        return None
    raw_stops = day.get("stops")
    if not isinstance(raw_stops, list):
        return None
    stops: list[Stop] = []
    for item in raw_stops:
        if not isinstance(item, dict):
            return None
        name = str(item.get("name") or "").strip()
        if not name:
            return None
        stops.append(
            Stop(
                slot=str(item.get("slot") or "").strip(),
                name=name,
                what=str(item.get("what") or "").strip(),
                how=str(item.get("how") or "").strip(),
                tip=str(item.get("tip") or "").strip(),
            )
        )
    return stops


def _coord_index(pois: list[Poi], city: str | None) -> dict[str, tuple[float, float]]:
    grouped: dict[str, list[Poi]] = {}
    for poi in pois:
        grouped.setdefault(poi.name.strip(), []).append(poi)
    wanted = _city_names(city)
    chosen: dict[str, tuple[float, float]] = {}
    for name, group in grouped.items():
        pool = group
        if wanted:
            pool = [poi for poi in group if any(_same_city(poi.city, item) for item in wanted)]
        coords = {(poi.lng, poi.lat) for poi in pool}
        if len(coords) == 1:
            chosen[name] = next(iter(coords))
    return chosen


def _city_names(city: str | None) -> tuple[str, ...]:
    if city is None:
        return ()
    if isinstance(city, str):
        text = city.strip()
        return (text,) if text else ()
    names = []
    for item in city:
        text = str(item or "").strip()
        if text:
            names.append(text)
    return tuple(names)


def _same_city(left: str, right: str) -> bool:
    a, b = _norm_city(left), _norm_city(right)
    return bool(a and b and a == b)


def _norm_city(name: str) -> str:
    text = (name or "").strip()
    if text.endswith("市"):
        text = text[:-1]
    return text


def _split_json_fence(text: str) -> tuple[str | None, str]:
    match = None
    for found in re.finditer(r"```json\s*", text, flags=re.IGNORECASE):
        match = found
    if match is None:
        return None, text
    end = text.find("```", match.end())
    if end < 0:
        # 代码块还没写完时先不展示，避免半截 JSON 出现在正文里
        return None, text[: match.start()].strip()
    raw = text[match.end() : end].strip()
    display = (text[: match.start()] + text[end + 3 :]).strip()
    return raw, display


def _has_coords(parsed: Itinerary | None) -> bool:
    if parsed is None:
        return False
    return any(stop.lng is not None and stop.lat is not None for day in parsed.days for stop in day.stops)


def _itinerary_from_pois(pois: list[Poi], city: str | None) -> Itinerary | None:
    """把这次查到的坐标收成一天，让地图先画出来。"""
    stops: list[Stop] = []
    seen: set[str] = set()
    for poi in pois:
        if city and poi.city and not _same_city(poi.city, city):
            continue
        if poi.name in seen:
            continue
        seen.add(poi.name)
        stops.append(Stop("", poi.name, "", "", "", poi.lng, poi.lat))
        if len(stops) >= _DETAIL_LIMIT:
            break
    if not stops:
        return None
    return Itinerary((Day(tuple(stops)),))


def _pois_from_geo(payload) -> list[Poi]:
    rows = payload.get("return") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    found: list[Poi] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        coords = _parse_location(item.get("location"))
        if coords is None:
            continue
        name = _geo_label(item)
        if not name:
            continue
        city = str(item.get("city") or "").strip()
        found.append(Poi(name=name, lng=coords[0], lat=coords[1], city=city))
    return found


def _geo_label(item: dict) -> str:
    parts: list[str] = []
    for key in ("name", "district", "street"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    number = item.get("number")
    if isinstance(number, str) and number.strip():
        parts.append(number.strip())
    if parts:
        return "".join(parts)
    city = item.get("city")
    return city.strip() if isinstance(city, str) else ""


def _ref_for_stop(stop_name: str, refs: list[PlaceRef]) -> PlaceRef | None:
    name = (stop_name or "").strip()
    if not name:
        return None
    exact = [ref for ref in refs if ref.name == name]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    contained = [ref for ref in refs if name in ref.name]
    if len(contained) == 1:
        return contained[0]
    return None


def _message_name(message) -> str:
    if isinstance(message, dict):
        return str(message.get("name") or "")
    return str(getattr(message, "name", "") or "")


def _message_content(message):
    if isinstance(message, dict):
        return message.get("content")
    return getattr(message, "content", None)


def _unwrap_content(content):
    if isinstance(content, tuple):
        return _unwrap_content(content[0]) if content else ""
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict) and "text" in item:
                texts.append(str(item["text"]))
        if texts:
            return "\n".join(texts)
    return content


def _load_json(content):
    if isinstance(content, (dict, list)):
        return content
    if not isinstance(content, str):
        return None
    text = content.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    decoder = json.JSONDecoder()
    while start != -1:
        try:
            payload, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
            continue
        if isinstance(payload, dict):
            return payload
        start = text.find("{", start + 1)
    return None


def _poi_items(payload) -> list:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    pois = payload.get("pois")
    if isinstance(pois, list):
        return pois
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("pois"), list):
        return data["pois"]
    if payload.get("name") and payload.get("location"):
        return [payload]
    return []


def _poi_from_item(item) -> Poi | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get("name") or "").strip()
    coords = _parse_location(item.get("location"))
    if not name or coords is None:
        return None
    city = str(item.get("cityname") or item.get("city") or "").strip()
    return Poi(name=name, lng=coords[0], lat=coords[1], city=city)


def _parse_location(location) -> tuple[float, float] | None:
    if not isinstance(location, str) or "," not in location:
        return None
    left, right = location.split(",", 1)
    try:
        lng, lat = float(left), float(right)
    except ValueError:
        return None
    if not (-180 <= lng <= 180 and -90 <= lat <= 90):
        return None
    return lng, lat
