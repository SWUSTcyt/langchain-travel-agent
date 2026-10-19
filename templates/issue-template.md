# Issue: [标题]

<!-- 以下两行可选：Spec 有编号 AC 时填，便于 Review 逐项给证据 -->
<!-- spec: SPEC-001 -->
<!-- accepts: AC-001, AC-002 -->

## 任务描述

<!-- 一个 Agent 能独立完成的粒度。只写决策：文件、签名、规格里的值、测试断言。不写函数体。 -->

## 规格未写、合理用户会踩

<!-- 从本 Spec 已承诺的能力推出来的情况，最多 5 条。检查过、没有：写一行「无（已检查）」，空表等于没做。不要借此加规格没承诺的新功能。 -->

| 输入或情况 | 合理用户期望 | 落到哪条测试 |
|---|---|---|
| | | |

## 输入 / 输出

- **输入：**
- **输出：**

## 依赖条件

- [ ] 依赖 Issue #___

<!-- P0/P1 Issue：若有外部依赖（法源权利/供应商条款/盲测/部署），登记依赖表。 -->
<!-- 代码与外部依赖都满足才整体 Verified；否则拆「本地完成」+「外部 pending_external」。 -->

| dependency_type | blocking_level | evidence_required | substitute_allowed | owner | rollback_if_missing |
|---|---|---|---|---|---|
| code/source-rights/vendor-terms/blind-test/deployment | hard/soft | 文件/回执/测试/签字 | 是/否 | 责任人 | 关闭入口/quarantine/回到 pending |

## 验收标准

<!-- 分级语义以 plan-breakdown 为准；边界与错误处理若会阻塞使用，属 P0/P1，不要因为「看起来像边界」就放进 P2 -->

### P0（阻塞必修，不满足不合入）

- [ ] 

### P1（本次必修）

- [ ] 

### P2（可后续 PR，记为 follow-up）

- [ ] 

### P3（可忽略，记录不追踪）

- [ ] 

## 参考

<!-- 指向 CONTEXT_INDEX 中的相关文档 -->
