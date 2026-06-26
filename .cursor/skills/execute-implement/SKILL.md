---
name: execute-implement
description: 对照 Issue 与验收标准开发。Use when 一个 Issue 被分配、准备写代码/写测试/修 Bug 时。也适用于需要按验收标准实现功能、并保证产出包含测试与示例、提交前自查的场景。
---

# Execute-Implement：开发执行

## 概述

对照 Issue 和 P0-P3 验收标准写代码，产出必须包含单元测试、功能测试、使用示例，提交前先自查。

**核心原则：** 一次只做一个 Issue，一次做对，不靠反复重试（重试是最大的 token 浪费源）。

## 何时使用

- 某个 Issue 被分配，进入开发
- 修 Bug（先写复现测试，再修）

**何时不用：** 需求/拆分还没定（先 plan-spec / plan-breakdown）；纯调研（用 explore 子 Agent，不写代码）。

## 流程

1. **读 Issue 与验收标准** — 明确 P0/P1 必须满足项、输入/输出、依赖。
2. **先出测试计划** — 编码前列出测试场景 + 预期结果，交用户确认（见 verify-test）。
3. **按 TDD 实现** — 先写失败测试，再写最小实现使其通过，再重构。参考 `reference/vendored-skills/superpowers/skills/test-driven-development`。
4. **补功能测试 + 使用示例** — 至少 1 正常 + 1 异常；2-3 个实际用法示例。
5. **提交前自查** — 用 verify-review 对照验收标准逐项自审，再提交 PR/合入。
6. **写 PR Summary** — 用 `templates/pr-summary-template.md`。

## Token 与信息获取

- **Issue 足够小**，一次做对。
- **信息按需获取** — 通过 `CONTEXT_INDEX.md` 按路径读取所需文档，不一次性灌入全部上下文。
- 同一段代码反复写不对（≥2 次）→ 委托 explore 子 Agent 查文档/查类似实现，不要硬撞。

## 并行注意

并行处理的 Issue 必须操作不同文件/模块，否则串行，避免冲突。共享 DB Schema、接口契约、代码风格。

## 产出

- 代码 + 单元测试 + 功能测试 + 使用示例
- PR（附 PR Summary）

## 约束（不可回调）

- P0 无法满足时**停止上报**，不自行降低标准。
- 不超出 Issue 范围（YAGNI）。
- 中文注释用 UTF-8，避免乱码。

## 常见错误

- **不写测试就提交** → 违反三层测试要求，必被 review 退回。
- **越界实现** → 顺手改了别的功能，破坏其他 Issue。严守边界。
- **撞墙硬写** → 同一问题反复失败仍不调研，浪费 token。2 次失败即委托 explore。

## 参考

- 模板：`templates/pr-summary-template.md`
- 配套：`skills/verify-test/SKILL.md`、`skills/verify-review/SKILL.md`
- 借鉴：`reference/vendored-skills/superpowers/skills/test-driven-development`、`subagent-driven-development`
- 方法论出处：唯一真源 `docs/AI 编程方法论 v1.2 — 可操作版.md` 第 2.1 / 2.3 / 2.6 / 3.3 节
