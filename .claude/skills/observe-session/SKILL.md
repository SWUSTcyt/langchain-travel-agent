---
name: observe-session
description: 可观测性与模型降质检测。Use when 一次开发会话结束、需要记录 Session 摘要、或怀疑模型出现降质（反复返工、标准滑坡、摸鱼）时。也适用于需要追踪 Issue 状态、生成 PR 摘要、复盘 token 花费的场景。
---

# Observe-Session：可观测性

## 概述

为长期运行建立可观测性：Issue 状态看板、PR Summary、Session 摘要，并基于指标检测模型降质，及时干预。

**核心原则：** 看得见才管得住。降质要靠指标早发现，而不是等结果烂了才察觉。

## 何时使用

- 一次开发会话结束 → 写 Session 摘要
- PR 提交 → 生成 PR Summary
- 怀疑模型降质（反复返工、标准滑坡）

## Issue 状态看板

标准流转：`todo → in-progress（标注 Agent）→ in-review → blocked（标注原因）→ done`。
本地/单人退化为 `PLAN.md` 表格或编辑器 TODO 列表。

## Session 摘要

每次会话结束记录（用 `templates/session-summary-template.md`），存入 `docs/session-summaries/`。摘要按结构化字段写，把四类信息分开——**facts（可复核事实）/ decisions（负责人拍板）/ inferences（推断）/ external_blockers（外部待办）**——外加 `issue_id`、`spec_id`、`scope_changed`、`tests`（含 `baseline_sample_size`）、`secrets_or_customer_content_read`、`files_changed`、`commit_or_pr`、`next_owner`、`next_action`。

**硬规则：**

- `inference` 和 `external_blocker` 绝不写进 `verified`/`complete`/`done`。
- 摘要至少要有 **1 条 fact + 1 条 next_action**；缺则标 `incomplete_observation` 并说明缺什么，不静默丢记录。

**模板自检（启动时）：** 先确认 `templates/session-summary-template.md` 存在。若缺失，输出 `template_missing_fallback` 诊断，并用最小安全结构（上面的必填字段）手写摘要，不能因为模板不在就跳过记录。

## PR Summary

每个 PR 末尾附摘要（用 `templates/pr-summary-template.md`）。有 UI 的产品必须含「用户视角（本次让用户能做什么）」一行，别只报「实现了什么技术功能」。

**Milestone/阶段完成时**：除了逐 Issue 的完成情况，输出一段「用户使用路径增量」——从用户视角说清「现在能走通哪条使用路径」，并映射回 Spec 的关键路径步骤（见 plan-spec「用户使用路径与信息架构」），而非空泛描述。无 UI 的项目跳过。

## 模型降质检测

| 指标 | 正常值 | 告警阈值 | 处理方式 |
|---|---|---|---|
| Review 轮次 | 1-2 轮 | ≥ 4 轮 | 检查 Issue 是否太大，或换模型 |
| 同一问题反复 | 0 次 | ≥ 2 次 | 检查验收标准是否清晰 |
| 标准滑坡 | 无 | P0 被标为 P2 | 强制重读标准文档 |
| Issue 完成率 | > 80% | < 50% | 拆分 Issue，或换模型 |

**识别信号：** 连续 3 个 Issue review > 4 轮 → 换模型；review 开始说"差不多了合吧" → 查滑坡；同一 Bug 修 2 次没好 → 模型在摸鱼。

## 产出

- Session 摘要（`docs/session-summaries/`）、PR Summary、降质告警与处理建议

## 常见错误

- **只记成功不记错误** → 复盘失去价值。错误与解法必须记。
- **发现降质不干预** → 任由标准烂下去。命中告警阈值就按处理方式动作。
- **事实/推断/外部待办混写** → 一次观察被当成产品事实、外部 pending 被当成完成。四类分开写。
- **模板不在就跳过记录** → 会话记录静默丢失。缺模板走 `template_missing_fallback` 最小结构补记。

## 参考

- 模板：`templates/session-summary-template.md`、`templates/pr-summary-template.md`
- 下一步：`skills/improve-retro/SKILL.md`（把记录提炼成规则/新 skill）
