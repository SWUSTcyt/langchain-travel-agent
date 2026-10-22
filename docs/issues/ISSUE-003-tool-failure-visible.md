# Issue: 地图工具执行失败必须可见

> 状态：2026-10-20 用户确认后实施。离线部分完成；真实高德失败下的最终措辞未验证（P2，pending_external）。

spec: SPEC-002
accepts: AC-008

## 任务描述

只改地图工具失败时交给模型的文本。成功时的返回保持原样。

- 文件：`tools.py` 的 `_safe_run_coro`。它现在捕获异常后返回普通句子，其中有「或基于已知信息直接回答」。
- 改完的返回必须同时满足：含有固定失败标记 `工具执行失败`；不含「直接回答」；不含「基于已知信息」。异常原文可以截断，沿用现在的长度上限。
- 不改城市注入、行程状态、界面布局。
- 测试：在 `tests/test_offline_baseline.py` 增加一条。让被包装的工具抛出超时或高德额度错误，断言返回文本满足上面三条，且成功调用仍返回工具自己的原文。

指回 Agent 方案「运行边界」：工具失败必须留下可见失败，不能当成成功观测。

## 规格未写、合理用户会踩

| 输入或情况 | 合理用户期望 | 落到哪条测试 |
|---|---|---|
| 工具超时 | 当成没查到，不鼓励模型编一段天气 | 新增失败测试 |
| 高德返回额度超限 | 同上 | 同一条测试的第二种异常 |
| 工具正常返回一段天气 | 原文原样交回，不被包成失败 | 新增测试的成功分支 |
| 失败后用户已经发出的那句还在界面上 | 不清空对话 | 不改 `ui.py`；现有清空只发生在用户点清空 |

## 输入 / 输出

- **输入：** 地图工具抛出的异常，或工具的正常返回值
- **输出：** 失败时是带失败标记的文本；成功时是工具原文

## 依赖条件

- [x] 无前置 Issue。SPEC-002 已 Frozen。

| dependency_type | blocking_level | evidence_required | substitute_allowed | owner | rollback_if_missing |
|---|---|---|---|---|---|
| code | hard | `tests/test_offline_baseline.py` 新断言通过，且原 23 项仍通过 | 否 | 实现者 | 不合入 |
| vendor-terms | soft | 真实高德失败时，页面回答含「没查到」 | 是，离线异常代替「工具文本已是失败」；代替不了「模型最终措辞」 | 实现者 | 真实高德没失败则该条标 pending_external，不把离线通过写成整页已验收 |

## 证据合同

```yaml
evidence_contract:
  claim: "地图工具抛错时，交给模型的文本是失败，且不鼓励它把失败当成已查到"
  evidence_level: "E0"
  source_of_truth: "tests/test_offline_baseline.py 的断言输出"
  required_fields: ["失败标记", "禁止出现的句子", "成功返回未被改写"]
  disqualifiers: ["只改了文案但测试没先失败过", "用模型的口头总结代替断言"]
  fail_closed_state: "unverified"
  model_call_allowed_when: "离线断言已经通过之后，才允许用真实高德看最终回答是否写了没查到；高德没有失败则这条停在 pending_external"
  human_owner: "实现者"
  expires_or_review_due_at: null
```

## 验收标准

### P0（阻塞必修，不满足不合入）

- [x] 现有 `tests/test_offline_baseline.py` 与 `tests/test_turn_context.py` 全部通过。证据：共 26 项 `OK`。

### P1（本次必修）

- [x] 新增测试在改代码前失败，改后通过，覆盖超时和额度超限两种异常，以及成功返回不被改写。证据：`ToolFailureTextTest` 改前 2 个 FAIL（文本含「直接回答」），改后通过。
- [x] 失败文本含 `工具执行失败`，且不含「直接回答」「基于已知信息」。证据：同上。

### P2（可后续 PR，记为 follow-up）

- [ ] 真实页面上制造一次高德失败，看最终回答是否写明没查到。未做：无法稳定制造高德失败，标 pending_external。

### P3（可忽略，记录不追踪）

- [ ] 无

## 参考

- `docs/spec/travel-agent.md` AC-008
- `docs/milestones/M1-tool-failure-visible.md`
