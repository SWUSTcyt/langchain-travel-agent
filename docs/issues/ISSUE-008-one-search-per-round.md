# Issue: 同一轮地点搜索最多一次

> 状态：已确认并实现。P0、P1 离线通过。P2 真实一轮日志 pending_external。

spec: SPEC-005
accepts: 运行边界里的工具预算。ISSUE-007 的 P2。

## 任务描述

同一轮里，`maps_text_search` 只放行第一次。第二次及以后不调用高德，返回说明，让模型用已有结果写行程。

- 文件：`middleware.py` 的 `track_tool_budget`。现有逻辑只按工具名拦截路线、地理编码和详情，不限制搜索次数。
- `maps_weather` 是否同样最多一次：本次默认一起限制。若你只要限制搜索、天气仍可多次，确认时说明。
- 不改坐标补全、地图颜色、提问页。
- 测试：在 `tests/test_turn_context.py` 增加。第一次 `maps_text_search` 会调用处理函数；同一轮第二次不调用，返回文本含「已经搜过」或同等固定说法。`maps_weather` 按上面的决定写同一条或单独一条。

## 规格未写、合理用户会踩

| 输入或情况 | 合理用户期望 | 落到哪条测试 |
|---|---|---|
| 同一轮第 2 次地点搜索 | 不到高德，用第一次的结果继续写 | 新增第二次搜索测试 |
| 下一轮新问题再搜一次 | 允许，不沿用上一轮的「已经搜过」 | 新增新一轮可再搜 |
| 同一轮第 2 次天气 | 与搜索相同，最多一次 | 同一组测试，除非确认天气不限制 |
| 第一次搜索还没返回就又发起一次 | 仍算第二次，不发出 | 与第二次搜索同一条 |

## 输入 / 输出

- **输入：** 同一轮里的多次 `maps_text_search`（以及按确认范围的 `maps_weather`）
- **输出：** 第一次照常执行；其后返回固定说明，处理函数不被调用

## 依赖条件

- [x] ISSUE-007 的种类拦截已在代码里。本任务只加次数。

| dependency_type | blocking_level | evidence_required | substitute_allowed | owner | rollback_if_missing |
|---|---|---|---|---|---|
| code | hard | `tests/test_turn_context.py` 新断言通过，已有 `ToolBudgetTest` 不回退 | 否 | 实现者 | 不合入 |

## 证据合同

```yaml
evidence_contract:
  claim: "同一轮第二次地点搜索不会调用处理函数"
  evidence_level: "E0"
  source_of_truth: "tests/test_turn_context.py 中第二次调用的 handler 次数为 0"
  required_fields: ["第几次", "工具名", "handler 是否被调用", "返回文本"]
  disqualifiers: ["只改提示词", "用真实模型口头少搜了代替断言"]
  fail_closed_state: "unverified"
  model_call_allowed_when: "离线断言通过之后，才看真实一轮日志里的搜索次数；日志没有则该条 pending_external"
  human_owner: "实现者"
  expires_or_review_due_at: null
```

## 验收标准

### P0（阻塞必修，不满足不合入）

- [x] 同一轮第二次 `maps_text_search` 不调用处理函数，返回文本说明已经搜过。证据：`test_second_text_search_in_same_round_is_not_sent`，handler 只收到第一次，返回含「已经搜过」。
- [x] 新的一轮可以再搜一次。证据：`test_new_round_can_search_again`，新的 runtime 状态再次放行。
- [x] `ToolBudgetTest` 原有两条仍通过。证据：`tests.test_turn_context.ToolBudgetTest` 5 项 OK；`tests.test_turn_context`、`tests.test_offline_baseline`、`tests.test_itinerary`、`tests.test_itinerary_view` 共 58 项 OK。

### P1（本次必修）

- [x] `maps_weather` 同一轮最多一次。证据：`test_second_weather_in_same_round_is_not_sent`，返回含「已经查过」。

### P2（可后续 PR，记为 follow-up）

- [ ] 真实一轮日志里地点搜索只有 1 次。pending_external：离线断言已过，还没有重启后的真实一轮日志。

### P3（可忽略，记录不追踪）

- [ ] 无

## 参考

- `docs/issues/ISSUE-007-tool-call-scope.md`
- `middleware.py` 的 `track_tool_budget`
