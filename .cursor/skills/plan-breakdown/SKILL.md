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

1. **拆 Epic** — 先确认依据的 Spec 已是 Frozen；仍是 Draft 就回 plan-spec 定稿。每个 Epic = 一个独立功能模块，先拆当前需要的 2-3 个。**若 plan-spec 已出过 Spec 地图，直接沿用：一份子 Spec 对应一个 Epic**，不要重新划一套边界。
2. **拆 Milestone** — 选第一个 Epic，拆出 Milestone，每个含：起始条件、交付物、验收标准。只细化前 1-2 个。用 `templates/milestone-template.md`。**有 UI 的产品，每个 Milestone 标注它交付的「用户使用路径增量」**（映射 Spec 的关键路径步骤），让阶段完成后能从用户视角反馈。
3. **拆 Issue** — 选第一个 Milestone，拆到 Issue 级别。每个 Issue 含：任务描述、输入/输出、依赖条件、P0-P3 验收标准。用 `templates/issue-template.md`。计划只记决策，见下方「计划记决策，不写实现」。
4. **写验收标准（前置）** — 拆 Issue 的同时按 P0-P3 分级写验收标准（见下表），并补上「规格未写、合理用户会踩」的失败。让用户确认/调整。
5. **停下等确认** — 把拆分交给用户看。用户确认这份拆分之前，不得进入 execute-implement。Spec 已冻结 ≠ 实现计划已被看过。
6. **维护 Plan Document** — 把当前 Milestone 与 Issue 状态写入 `PLAN.md`（≤500 tokens），用 `templates/plan-document-template.md`。PLAN 只挂**活跃**的 Issue 与 Spec 链接；需求全貌与历史在 `docs/spec/`（索引见 `docs/spec/INDEX.md`），不要让 PLAN 承担 Spec 目录职责。

## Issue 粒度黄金法则

如果一个 Issue 需要 **3 轮以上 review** 才能合入，就是太大了，必须再拆。

## 计划记决策，不写实现

Issue 写实现者自己决定不了的东西：改哪些文件、接口签名、规格里钉死的值、测试要断言什么。函数体、大段示例代码留给 execute-implement。

- 计划比它所拆的 Spec 长出很多，或大半是代码，就是把实现写进了计划，要改回签名、断言和文件路径。
- 用户确认这份拆分之前，不得开始写生产代码。

## 规格未写、合理用户会踩的失败

规格只写必须做什么，不会把每种输入列全。没写到，不等于这种输入可以崩、答错或被当成成功。每个 Issue 从该规格已经承诺的能力里，最多列 5 条使用者真会碰到、但原文没点名的情况：什么输入、合理用户期望什么、落到哪条测试。检查过、没有这类情况，写一行「无（已检查）」；表格空着等于没做。

能从现有规格推出来的才算。规格写的是审阅，不要因此加「起草整份合同」——那是范围变更，回 plan-spec。

Spec 里有「Agent 方案」时，Issue 和上面这些失败必须能指回其中某一条决定（例如「改条件后的查询使用新状态」）。方案里写了不需要的能力，就不拆对应的实现任务。

## 重构类任务的拆分范式：按关注点逐个剥离

服务化/工程化重构（如「脚本改造成可交付的服务」）不要一把梭，按关注点逐个剥离拆 Issue，**每个 Issue 结束时代码必须可运行、可验证**：

- 典型关注点（顺序和取舍按项目实际定）：配置剥离（含密钥出代码）→ prompt/资源剥离 → 装配边界（工厂函数/包结构）→ 接入协议（HTTP 等）。
- 每个 Issue 只动一个关注点；若一个 Issue 要同时动两个关注点，拆开。
- 参考案例见 `reference/service-refactor-guide.md`（框架无关的演进路线）。

## P0-P3 验收标准分级

| 等级 | 含义 | 处理方式 |
|---|---|---|
| P0 | 阻塞性，不修复不能合入 | 必须修复 |
| P1 | 重要缺陷，本次合入前修复 | 必须修复 |
| P2 | 建议修复，可后续 PR | 记录为 follow-up issue |
| P3 | 锦上添花，可忽略 | 记录不追踪 |

**原则：中途不允许降级。** 做不完就拆 Issue，不降标准。

## 证据合同（P0/P1 Issue 前置）

验收标准回答「要做到什么」，证据合同回答「凭什么算做到了、做不到时停在哪个终态」。二者容易被混为一谈——模型调用成功、候选链接存在、已核验、业务质量通过是四件不同的事。

每个 P0/P1 Issue 至少挂一份证据合同（多条独立结论就挂多份），用 `templates/evidence-contract-template.md`，至少写清：

- `source_of_truth`：结论算数的唯一依据（代码/数据库终态/外部回执/人工签字）——**「模型说已核验」不能作为 source_of_truth**；
- `required_fields`：判定通过必须齐备的字段（来源版本、逐字引文、样本量等）；
- `fail_closed_state`：证据不足时的可见终态（`blocked`/`unverified`/`no_match`/`pending_external`），不得静默变成成功。

**硬规则：缺 `source_of_truth`、`required_fields` 或 `fail_closed_state` 的 P0/P1 Issue，不得进入除 Planned 外的任何完成态。** 涉及模型/外部服务的结论必须写 `model_call_allowed_when`（宿主门禁通过后的条件）。

## 外部依赖 / 证据依赖图（每个 P0/P1 Issue）

代码写完 ≠ Issue 完成。外部条件（法源权利、供应商条款、律所盲测、部署资源）若不在 Issue 开始时登记为「前置依赖 + 退出条件」，就会在代码完成后才暴露，把总进度误显示为完成。每个 P0/P1 Issue 除验收标准外，登记依赖表：

| 字段 | 取值示例 |
|---|---|
| `dependency_type` | code / source-rights / vendor-terms / blind-test / deployment |
| `blocking_level` | hard（缺则不能验收）/ soft（可先做骨架） |
| `evidence_required` | 文件 / 回执 / 测试 / 人工签字 |
| `substitute_allowed` | 是否允许合成样本替代（是→标「不可推广」） |
| `owner` | 项目负责人 / 律师 / 供应商 / DevOps |
| `rollback_if_missing` | 关闭入口 / 保持 quarantine / 回到 pending |

**硬规则：只有代码与外部依赖都满足，Issue 才能整体标 `Verified`。** 否则拆成两个状态——「本地实现完成」+「外部验收 pending_external」，缺的依赖自动生成 `pending_external`，不让总进度显示为完成。

## 产出

- Epic / Milestone 列表（Milestone 用模板）
- Issue 列表（每个带 P0-P3 验收标准，用模板）
- `PLAN.md`（≤500 tokens，**当前运行状态**唯一真源）

## 提示词参考

> 基于这份 Spec 做任务拆分：先拆 Epic，再选第一个 Epic 拆 Milestone，最后选第一个 Milestone 拆到 Issue。每个 Issue 要含任务描述、输入/输出、验收标准（P0/P1/P2/P3 四级）、依赖关系。Issue 粒度不超过 3 轮 review。

## 常见错误

- **一次性把所有 Milestone/Issue 细节都拆完** → 浪费，且计划会变。只细化最近 1-2 个。
- **Issue 过大** → 后续反复 review、token 浪费。按黄金法则及时再拆。
- **验收标准事后补** → 标准会被实现牵着走而滑坡。必须创建时前置写好。
- **Plan Document 写成大杂烩** → 超出 500 tokens 就失去「快速对齐」价值。细节交给 Issue。
- **重构一把梭** → 一个 Issue 同时改配置、prompt、结构、协议，出错无法定位。按关注点逐个剥离，每步可运行。
- **无视 Spec 地图另划 Epic** → Epic 边界与子 Spec 对不上，验收找不到依据。有地图就一份子 Spec 一个 Epic。
- **把函数体写进 Issue** → 计划变成实现稿，评审看的是代码而不是决策。只留文件、签名、规格值和断言。
- **Spec 一冻结就写代码** → 用户还没看过这份拆分。确认拆分后再进入 execute-implement。
- **规格没点名的输入就当不用测** → 使用者仍会这么用。先列入最多 5 条合理预期失败；推不出的新功能不要塞进来。

## 参考

- 模板：`templates/issue-template.md`、`templates/milestone-template.md`、`templates/plan-document-template.md`
- 重构参考：`reference/service-refactor-guide.md`（服务化重构的关注点剥离案例）
- 上一步：`skills/plan-spec/SKILL.md`
- 下一步：`skills/execute-implement/SKILL.md`
