---
name: verify-review
description: 代码审查与分层验收。Use when PR 提交后、或提交前自查、需要对照 Issue 验收标准逐项核验时。也适用于需要按 P0-P3 给出问题列表、判断能否合入的场景。
---

# Verify-Review：审查与分层验收

## 概述

对照 Issue 验收标准逐项检查，给出 P0-P3 问题列表，并按 L1/L2/L3 分层把验收分配给合适的执行者。审查不负责合并。

**核心原则：** 标准不滑坡。审查就是守住「标准前置」这条线，绝不说「差不多了合吧」。

## 何时使用

- 每次 PR 提交后
- implement 提交前的自审查

**何时不用：** 代码尚未完成；纯风格偏好讨论。

## 分层验收（谁查什么）

| 层级 | 谁检查 | 检查什么 |
|---|---|---|
| L1 自动 | CI / Linter / 测试（本地即测试脚本） | 编译、Lint、测试全绿、覆盖率 |
| L2 Agent | review 子 Agent | 对照 Issue 验收标准 P0/P1 逐项核验 |
| L3 人 | 你 | 只看 P0 + 整体设计方向（5-10 分钟） |

**流程：** PR → L1 自动跑 → 不过则 CI watcher 分析修复 → 过后 review Agent 做 L2 → 通知人做 L3 → 确认合入。

## 审查清单

- [ ] 所有 P0/P1 标准是否满足？
- [ ] 是否超出 Issue 范围？
- [ ] 单元测试覆盖率 ≥ 80%？
- [ ] 至少 1 正常 + 1 异常功能测试？

## 输出格式

```markdown
## P0 检查：[通过/不通过]
## P1 检查：[通过/部分/不通过]
## 必须修改：
-
## 建议（P2/P3）：
-
```

## 常见错误

- **标准滑坡** → 把 P0 当 P2 放行。出现此苗头强制重读验收标准文档。
- **越权合并** → review 只给结论，不负责合并。
- **泛泛而评** → 不对照具体验收标准。必须逐项核验。

## 参考

- 配套：`skills/execute-implement/SKILL.md`、`skills/verify-test/SKILL.md`
- 借鉴：`reference/vendored-skills/superpowers/skills/requesting-code-review`、`receiving-code-review`
- 方法论出处：唯一真源 `docs/AI 编程方法论 v1.2 — 可操作版.md` 第 3.2 节
