# Issue: 结构化行程与坐标匹配

> 状态：2026-10-20 用户确认后实施。

spec: SPEC-005
accepts: AC-101, AC-102, AC-105

## 任务描述

- 新模块 `itinerary.py`：
  - `extract_pois(tool_messages) -> list[Poi]`：从本轮 `maps_text_search` 返回里取名称、坐标（`location` 字段 "lng,lat"）、城市。
  - `parse_itinerary(answer_text: str) -> Itinerary | None`：从模型最终答案里读出结构化行程。
  - `attach_coords(itinerary, pois) -> Itinerary`：按地点名匹配坐标，匹配不到坐标为 None。
- 结构化输出的取法：让模型在最终答案末尾附一个 ```json 代码块（天、时段、地点名、做什么、怎么去、提醒），宿主解析并从展示文字里移除该代码块。不用 `response_format` 强制结构化，原因是它会改变现有流式输出和工具循环；若代码块缺失或解析失败，返回 None。
- 系统提示词（`middleware.py` `pin_cities_and_adcodes`）加一段输出格式说明；只问天气类问题不附代码块。
- `ui.py` 的 `stream_answer` 在最终答案后计算一份结构化行程，交给界面（界面接入在 ISSUE-005）。

指回 SPEC-005「谁做决定」：坐标只来自本轮工具返回。

## 规格未写、合理用户会踩

| 输入或情况 | 合理用户期望 | 落到哪条测试 |
|---|---|---|
| 模型没附 JSON 代码块 | 文字照常，没有地图 | `test_missing_json_returns_none` |
| 地点名在工具返回里找不到 | 该地点无坐标 | `test_unmatched_place_has_no_coords` |
| 模型在 JSON 里自己写了坐标 | 忽略模型的坐标 | `test_model_coords_are_ignored` |
| 同名地点两条 | 取本城市的那条；仍有多条时不上图 | `test_ambiguous_name_not_mapped` |

## 输入 / 输出

- 输入：模型最终答案文本；本轮工具消息
- 输出：`Itinerary(days=[Day(stops=[Stop(slot, name, what, how, tip, lng, lat)])])` 或 None

## 验收标准

### P0

- [x] 上表四条测试先失败后通过。证据：`tests/test_itinerary.py` 改前因缺少 `itinerary` 模块失败，改后通过。
- [x] 原有 26 项不回退。证据：加上新测试后共 38 项 `OK`。

### P1

- [ ] 真实「成都三天」能解析出三天，且至少一半地点拿到坐标（E2，失败记录原因）。未做：留到页面第一条真实路径一起验。

### P2

- [ ] 匹配率统计写进开发者日志
