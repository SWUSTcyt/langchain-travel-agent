---
name: plan-breakdown
description: 任务归约拆分与验收标准前置。Use when 已有 Spec 或较清晰的需求、要把大需求切成可执行任务、准备启动开发之前。也适用于需求太大、一个 Agent 无法独立完成、需要拆成 Epic/Milestone/Issue 并定义 P0-P3 验收标准的场景。
---

# Plan-Breakdown：归约拆分 + 验收标准前置

## 概述

承接 plan-spec 的 Spec，把需求从大到小逐层拆解，直到每个任务单元能被一个 Agent 独立完成；同时在创建时就写清每个 Issue 的 P0-P3 验收标准，并维护项目的 Plan Document。

**核心原则：** 任务足够小 + 标准前置不可回调。拆到位、标准定死，是后续高质量执行的地基。

## 何时使用

- 已有 Spec（来自 plan-spec），要开始拆任务
- 新 Milestone 启动 / 计划需要重新拆分
- 一个需求大到单个 Agent 无法一次做对

**何时不用：** 单个明确的小改动；需求尚未澄清（先用 plan-spec）。

## 流程

1. **拆 Epic** — 每个 Epic = 一个独立功能模块，先拆当前需要的 2-3 个。
2. **拆 Milestone** — 选第一个 Epic，拆出 Milestone，每个含：起始条件、交付物、验收标准。只细化前 1-2 个。用 `templates/milestone-template.md`。
3. **拆 Issue** — 选第一个 Milestone，拆到 Issue 级别。每个 Issue 含：任务描述、输入/输出、依赖条件、P0-P3 验收标准。用 `templates/issue-template.md`。
4. **写验收标准（前置）** — 拆 Issue 的同时按 P0-P3 分级写验收标准（见下表），让用户确认/调整。
5. **维护 Plan Document** — 把当前 Milestone 与 Issue 状态写入 `PLAN.md`（≤500 tokens），用 `templates/plan-document-template.md`。

## Issue 粒度黄金法则

如果一个 Issue 需要 **3 轮以上 review** 才能合入，就是太大了，必须再拆。

## P0-P3 验收标准分级

| 等级 | 含义 | 处理方式 |
|---|---|---|
| P0 | 阻塞性，不修复不能合入 | 必须修复 |
| P1 | 重要缺陷，本次合入前修复 | 必须修复 |
| P2 | 建议修复，可后续 PR | 记录为 follow-up issue |
| P3 | 锦上添花，可忽略 | 记录不追踪 |

**原则：中途不允许降级。** 做不完就拆 Issue，不降标准。

## 产出

- Epic / Milestone 列表（Milestone 用模板）
- Issue 列表（每个带 P0-P3 验收标准，用模板）
- `PLAN.md`（≤500 tokens 的项目唯一真源）

## 提示词参考

> 基于这份 Spec 做任务拆分：先拆 Epic，再选第一个 Epic 拆 Milestone，最后选第一个 Milestone 拆到 Issue。每个 Issue 要含任务描述、输入/输出、验收标准（P0/P1/P2/P3 四级）、依赖关系。Issue 粒度不超过 3 轮 review。

## 常见错误

- **一次性把所有 Milestone/Issue 细节都拆完** → 浪费，且计划会变。只细化最近 1-2 个。
- **Issue 过大** → 后续反复 review、token 浪费。按黄金法则及时再拆。
- **验收标准事后补** → 标准会被实现牵着走而滑坡。必须创建时前置写好。
- **Plan Document 写成大杂烩** → 超出 500 tokens 就失去「快速对齐」价值。细节交给 Issue。

## 参考

- 模板：`templates/issue-template.md`、`templates/milestone-template.md`、`templates/plan-document-template.md`
- 上一步：`skills/plan-spec/SKILL.md`
- 下一步：`skills/execute-implement/SKILL.md`
- 方法论出处：唯一真源 `docs/AI 编程方法论 v1.2 — 可操作版.md` 第 1.2 / 1.3 / 1.4 节
