# Issue: 模型只查地点和天气，坐标由系统补

> 状态：补记。代码在 2026-10-21 已先写进工作区。本文件不能当作「先定标准再写代码」的证据。用户 2026-10-21 追问流程后补上。

spec: SPEC-005
accepts: 坐标只来自工具（AC-102）

## 任务描述

模型每轮只能打到高德的两个工具。坐标不让模型查。

- 文件：`middleware.py` 的 `track_tool_budget`。工具名是 `maps_geo`、`maps_search_detail`、`maps_around_search`、`maps_regeocode`、`maps_ip_location`，或以 `maps_direction` 开头时，直接返回说明，不调用 `handler`。
- `maps_text_search` 和 `maps_weather` 仍交给原来的处理。
- 同一轮里允许多次 `maps_text_search`。这次没有加上「搜索最多 1 次」的硬限制。
- 文件：`itinerary.py` 的 `collect_pois`。关键词搜索没有坐标时，系统按返回的 id 调用 `maps_search_detail`，最多 6 次。
- 系统提示词写明只用上述两个工具。提示词不是拦截本身。

## 规格未写、合理用户会踩

| 输入或情况 | 合理用户期望 | 落到哪条测试 |
|---|---|---|
| 模型仍发起路线规划 | 请求不到高德 | `test_extra_map_tools_are_not_sent_out` |
| 模型发起一次地点搜索 | 搜索照常发出 | `test_text_search_is_still_sent_out` |
| 搜索结果没有 location | 用地详情里的坐标上图 | `test_one_day_hangzhou_gets_line_not_chengdu` |
| 回答没有 json，但搜索有两个地点 | 地图仍有点和线 | `test_prose_without_json_still_maps_searched_places` |
| 同一轮里模型连发 5 次地点搜索 | 这 5 次仍会打到高德 | 无测试。本次未做次数硬限制 |

## 输入 / 输出

- **输入：** 模型发出的工具名；关键词搜索返回的地点 id
- **输出：** 被禁工具得到一段「不用调用」的文本；允许的工具走原逻辑；地图用详情坐标

## 依赖条件

- [x] SPEC-005 已 Frozen。代码先于本 Issue。

| dependency_type | blocking_level | evidence_required | substitute_allowed | owner | rollback_if_missing |
|---|---|---|---|---|---|
| code | hard | `tests/test_turn_context.py` 的 `ToolBudgetTest` 通过 | 否 | 实现者 | 不合入 |
| vendor-terms | soft | 真实一轮里高德请求不再包含路线规划 | 是，离线断言代替「请求没发出」；代替不了「额度不再超限」 | 实现者 | 额度仍超限则该条 pending_external |

## 证据合同

```yaml
evidence_contract:
  claim: "路线规划、地理编码、地点详情不会由模型打到高德；地点搜索仍会打到"
  evidence_level: "E0"
  source_of_truth: "tests/test_turn_context.py ToolBudgetTest 的断言：被禁工具的 handler 调用次数为 0，搜索工具的 handler 被调用"
  required_fields: ["工具名", "handler 是否被调用", "返回文本含不用调用"]
  disqualifiers: ["只改了提示词没有断言 handler", "把同一轮里搜索次数变少写成已经限制"]
  fail_closed_state: "unverified"
  model_call_allowed_when: "离线断言通过之后，才用真实页面看一轮里实际打了哪些工具；额度超限不能写成优化已生效"
  human_owner: "实现者"
  expires_or_review_due_at: null
```

## 验收标准

### P0（阻塞必修，不满足不合入）

- [x] `maps_direction_driving` 的处理函数不被调用，返回文本含「不用调用」。证据：`ToolBudgetTest.test_extra_map_tools_are_not_sent_out`，2026-10-21 通过。
- [x] `maps_text_search` 仍会调用处理函数。证据：`ToolBudgetTest.test_text_search_is_still_sent_out`，同次通过。

### P1（本次必修）

- [x] 搜索 JSON 没有 location 时，用详情坐标连出线，且不是成都的经度。证据：`DetailCoordTest.test_one_day_hangzhou_gets_line_not_chengdu`。
- [x] 没有 json 代码块时，地图仍用搜索到的地点。证据：`test_prose_without_json_still_maps_searched_places`。
- [ ] 真实一轮「北京三日游」的日志里，高德请求只有地点搜索和天气，没有路线规划。未做：最近一次真实日志仍是改拦截之前的。标 pending_external。

### P2（可后续 PR，记为 follow-up）

- [ ] 同一轮 `maps_text_search` 最多 1 次。现在没有这条硬限制。

### P3（可忽略，记录不追踪）

- [ ] 无

## 参考

- `docs/spec/travel-agent-v2.md` AC-102
- `docs/issues-log.md` 2026-10-21 条目
