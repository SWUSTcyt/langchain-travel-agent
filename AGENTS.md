# AGENTS.md

> 跨工具通用入口（Cursor / Claude Code / Codex 均识别）。
> 来源：vibe-coding-playbook（https://github.com/...），项目首次安装 skill 时一并复制。

## 三条铁律（不可回调）

1. **标准前置，不可回调** — 验收标准定义在写代码之前，中途绝不降低。做不完就拆任务，不降标准。
2. **信息触手可及，而非全部塞入** — Agent 需要什么能自己找到（按 `CONTEXT_INDEX.md` 索引按需读取），不一次性灌入。
3. **任务足够小，流程足够固化** — 大任务必拆分，重复流程必封装为 Skill。

## 五层闭环

```
Plan（规划）→ Execute（执行）→ Verify（验证）→ Observe（观测）→ Improve（改进）
  ↑                                                              │
  └──────────────────────────────────────────────────────────────┘
```

## Skill 调用指引（按阶段）

真源在 `skills/`，三家工具同步加载。遇到对应场景时调用：

| 阶段 | Skill | 何时用 |
|---|---|---|
| Plan | `plan-spec` | 需求模糊，先澄清产出 Spec |
| Plan | `plan-breakdown` | 把 Spec 拆成 Epic/Milestone/Issue + P0-P3 验收标准 |
| Execute | `execute-implement` | 一个 Issue 进入开发 |
| Verify | `verify-test` | 写三层测试 / 编码前出测试计划 |
| Verify | `verify-review` | PR 提交后或提交前自查 |
| Observe | `observe-session` | 会话结束写摘要 / 检测模型降质 |
| Improve | `improve-retro` | 反复踩坑 / Milestone 结束，提炼规则与新 Skill |
| **项目级** | `understand` | 首次进入项目或架构大改后，生成/更新 `docs/ARCHITECTURE.md` |
| **项目级** | `feature` | 基于架构文档实现新功能或修复 bug |

## 关键约定

- **项目架构文档**：`docs/ARCHITECTURE.md`（开发前必读）。
- **项目状态唯一真源**：`PLAN.md`（≤500 tokens），Agent 启动先读。
- **验收分级**：P0（阻塞必修）/ P1（本次必修）/ P2（后续 PR）/ P3（可忽略）。
- **测试三层**：单元（覆盖率 ≥80%）+ 功能（≥1 正常 +1 异常）+ Examples（2-3 个）。
- **本地/单人**：GitHub Issues/PR/CI 退化为 `PLAN.md` + 本地分支 + 本地测试脚本，质量标准不变。

## 信息索引

需要什么读什么，详见 `CONTEXT_INDEX.md`。不要一次性读全部上下文。

## 代码规范

- 注释用中文 + UTF-8，避免乱码。
- 优先 async/await，编写完善的错误处理。
- 修改既有函数时先理解原逻辑，在其基础上改，不随意移除已有正确逻辑。
- 新代码沿用项目主语言与既有约定。
