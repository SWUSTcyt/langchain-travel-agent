# Issue: 结果页作为唯一页面，点上不铺长名字

> 状态：已确认并实现。P0、P1 离线通过。P2 已在浏览器核对刚打开的页面和一条长地名。

spec: SPEC-006（Frozen）
accepts: 用户 2026-10-22 要求只留结果页，并解决杭州点名挡住地图。

## 任务描述

打开就是左边文字、右边地图，不再因为没行程把地图藏起来、把页面收成中间一条。提问仍用现在这一页底部的输入框。

- 还没有地点时，右边画一张默认图：中国范围，没有点、没有线，图例写「还没有地点」。
- 新问题一开始回到这张默认图。查到新地点后整张换成新点。不把上一座城市留在图上。
- 这次没查到：恢复上一张行程图。本来没有行程则停在默认图。
- 只问天气：地图栏仍在。已有行程就留着，没有就显示默认图。
- 三张示例留在左边，不单独成页。没有 JS key 时右边仍占一栏，写「地图暂不可用」。
- 地图标记只显示序号。地点全名不放在常驻标记上。点击后的气泡仍写出全名、从哪来、怎么去。
- 不改坐标补全、按天颜色、工具次数。

涉及：`itinerary_view.py` 的空地图与 `next_map_payload`，`assets/trip-map.js` 的标记 HTML，`assets/custom.css` 里 `map-off` 把地图栏藏起来并收窄页面的规则，`ui.py` 提交时清图的时机。测试加在现有 `tests/test_itinerary_view.py`，标记文本可在对 `trip-map.js` 的断言或抽出的小函数上测。

## 规格未写、合理用户会踩

| 输入或情况 | 合理用户期望 | 落到哪条测试 |
|---|---|---|
| 刚打开，还没提问 | 右边已是地图，不是另一张提问页 | 默认图可见，地图栏不是隐藏 |
| 上一张是成都，这句问杭州，地点还没回来 | 图上不再是成都的点 | 新问题开始时载荷是默认图，不含成都坐标 |
| 杭州地点名字很长 | 名字不铺在地图上挡住别的点 | 常驻标记 HTML 不含地点全名，气泡含全名 |
| 这句没查到 | 刚才的行程图还在 | 失败时载荷回到上一张，而不是停在默认图 |
| 只问天气，而且已经有行程 | 地图栏不消失 | 天气回答不把地图栏标成隐藏 |

## 输入 / 输出

- **输入：** 空行程、新问题进行中、查到地点、查询失败、只问天气、长地点名
- **输出：** 地图栏一直在；无地点时是默认图；有地点时换点；标记常驻内容只有序号

## 依赖条件

- [x] 结果页布局和按天标记已在。本任务只改空状态和标记上的文字。

| dependency_type | blocking_level | evidence_required | substitute_allowed | owner | rollback_if_missing |
|---|---|---|---|---|---|
| code | hard | `tests/test_itinerary_view.py` 新断言通过 | 否 | 实现者 | 不合入 |
| deployment | soft | 浏览器里刚打开时右边是地图，长名字不在点上 | 是，离线断言可先过；浏览器未看则该条 pending_external | 实现者 | 不把离线通过写成页面已核对 |

## 证据合同

```yaml
evidence_contract:
  claim: "无地点时地图栏仍在且是默认图；常驻标记不含地点全名"
  evidence_level: "E0"
  source_of_truth: "tests/test_itinerary_view.py 对默认载荷和标记 HTML 的断言"
  required_fields: ["地图栏是否隐藏", "默认图有没有点", "标记文本", "气泡是否含全名"]
  disqualifiers: ["只改提示词", "用截图印象代替断言"]
  fail_closed_state: "unverified"
  model_call_allowed_when: "离线断言通过之后，才在浏览器看刚打开的页面和一条带长地名的地图；没看则该条 pending_external"
  human_owner: "实现者"
  expires_or_review_due_at: null
```

## 验收标准

### P0（阻塞必修，不满足不合入）

- [x] 刚打开或还没有地点时，地图栏不隐藏，内容是没有点的默认图。证据：`test_open_page_uses_empty_china_map`；浏览器 1366 宽时文字约 713px、地图约 526px，图例「还没有地点。」，地图栏没有 `map-off`。
- [x] 新问题在新地点回来之前，地图不是上一座城市的点。证据：`test_waiting_question_drops_previous_city`，等待中的载荷不含 104.055 和「宽窄巷子」。
- [x] 常驻标记只有序号。地点全名只出现在点击后的气泡里。证据：`test_pin_shows_number_not_place_name`。浏览器里长地名的两个点文本是「1」「2」，宽 28px；点击后气泡含「断桥残雪」。

### P1（本次必修）

- [x] 这次没查到时，恢复上一张行程图。证据：`test_failed_or_weather_restores_previous_trip`，结束且没有新行程时载荷回到 104.055。
- [x] 只问天气不把地图栏藏起来。证据：同一测试里恢复后的 `map_card_mode` 为 `map`；`test_none_itinerary_keeps_the_map_column` 不含 `map-hidden`。

### P2（可后续 PR，记为 follow-up）

- [x] 浏览器里看刚打开的页面，以及一条杭州长地名。见上面 P0 的浏览器测量。不是再跑一遍真实模型。

### P3（可忽略，记录不追踪）

- [ ] 无

## 参考

- `docs/spec/trip-map-single-page.md`
- `docs/spec/trip-map-ui.md` 的 AC-004、AC-005
