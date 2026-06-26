---
name: improve-retro
description: 问题记录与定期总结提炼。Use when 同一问题反复出现、Milestone 结束、或需要把踩过的坑提炼成可复用规则/新 Skill 时。也适用于定期复盘、更新验收标准或拆分策略、沉淀方法论的场景。
---

# Improve-Retro：持续改进

## 概述

把执行中反复出现的问题自动记录下来，定期总结，提炼成可复用规则、新 Skill 或方法论更新，形成闭环。

**核心原则：** 同样的坑不踩第二次。改进必须沉淀为「下次会自动生效」的东西（规则/Skill/标准），而非一次性口头总结。

## 何时使用

- 同一问题反复出现 ≥ 2 次
- CI/测试失败且非显而易见原因
- Review 被退回 ≥ 2 次
- Milestone 结束 / 每完成 10 个 Issue / 每周固定时间 → 定期总结

## 问题自动记录

满足触发条件时追加到 `docs/issues-log.md`，格式：

```markdown
### [日期]: 问题标题
- **出现位置**: #3, #5
- **问题**: 简述
- **最终解法**: 简述
- **可复用规则**: 提炼出的规则
```

## 定期总结提炼流程

1. 读取本期所有问题记录
2. 分类：重复出现的 vs 一次性的
3. 提炼：哪些固化为 Skill？哪些更新验收标准？哪些调整拆分策略？
4. 输出改进清单，逐条更新到对应文档/Skill，并记入 `docs/improvements/CHANGELOG.md`

## 产出

- `docs/issues-log.md` 问题记录
- 改进清单 + `docs/improvements/CHANGELOG.md` 条目
- 新增/更新的 Skill 或验收标准

## 提炼为新 Skill 时

参考 `reference/SKILL-writing-guide.md` 的写作规范与 `reference/vendored-skills/superpowers/skills/writing-skills`。

## 常见错误

- **总结停在口头** → 下次照样犯。必须落成规则/Skill/标准更新。
- **重复与一次性不分** → 把偶发问题也固化成规则，增加负担。先分类再提炼。

## 参考

- 记录文件：`docs/issues-log.md`、`docs/improvements/CHANGELOG.md`
- 上一步：`skills/observe-session/SKILL.md`
- 写 Skill 规范：`reference/SKILL-writing-guide.md`
- 方法论出处：唯一真源 `docs/AI 编程方法论 v1.2 — 可操作版.md` 第五章（Improve）
