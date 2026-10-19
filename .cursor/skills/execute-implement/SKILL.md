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

1. **读 Issue 与验收标准** — 明确 P0/P1 必须满足项、输入/输出、依赖。用户尚未确认这份拆分时停下来，不写生产代码；spike 档没有拆分，以用户确认过的一句话意图为准。
2. **先出测试计划** — 编码前列出测试场景 + 预期结果，交用户确认（见 verify-test）。
3. **按 TDD 实现** — 先写失败测试，再写最小实现使其通过，再重构。参考 `reference/vendored-skills/superpowers/skills/test-driven-development`。
4. **补功能测试 + 使用示例** — 至少 1 正常 + 1 异常；2-3 个实际用法示例。
5. **提交前自查** — 用 verify-review 对照验收标准逐项自审，再提交 PR/合入。
6. **写 PR Summary** — 用 `templates/pr-summary-template.md`。

## Token 与信息获取

- **Issue 足够小**，一次做对。
- **信息按需获取** — 通过 `CONTEXT_INDEX.md` 按路径读取所需文档，不一次性灌入全部上下文。
- 同一段代码反复写不对（≥2 次）→ 委托 explore 子 Agent 查文档/查类似实现，不要硬撞。
- 若使用任务台账（task ledger）追踪子代理进度，放在稳定工作区目录，避免被 git clean 清理。**台账要按计划隔离**：每个计划一个独立目录、台账首行写明所属计划，否则同一工作树里的后续计划会把上一个计划的台账当成自己的进度（对齐 Superpowers v6.2.0 plan-scoped workspace）。示例路径：`.superpowers/sdd/<计划名>/progress.md`。

## 并行注意

并行处理的 Issue 必须操作不同文件/模块，否则串行，避免冲突。共享 DB Schema、接口契约、代码风格。

## 外部写操作授权

「允许写代码」不等于「允许改远端」。以下动作各自需要用户明确授权，逐项确认，不要互相推导：

`commit` / `push` / 开 PR / `merge` / 打 tag / 发 Release / 改 CI workflow

- 默认只在本地改文件；未获授权不做任何远程写操作。
- 只授权了 A 不代表可以做 B（授权 push ≠ 可以 merge，授权 commit ≠ 可以发 Release）。
- 一次失败不要反复换认证方式重试；记录失败原因并上报。

## 涉及模型 / 外部服务 / 连接器时（按需读取）

写这类功能时，先读 `reference/model-and-connector-guide.md`，落三组规则（纯前端/CRUD/离线工具不触发，不必读）：

- **失败关闭门禁**：先宿主 preflight，再外部请求；证据不足/版本冲突/权限失败/输入超限/来源不可访问都落可见失败终态，不调用模型；不允许模型自己把候选/转载/搜索摘要提升为 `verified`。
- **三层不变量**：领域不变量（来源/权限/版本/确认范围/删除谱系，不可由模型决定）+ 外部契约（输入投影/结构化输出/字段互斥/上下文预算）+ 宿主状态机（正常/边界/失败/恢复/重放/并发/外部缺失终态）。
- 对应的负例测试与连接器隔离要求见 `skills/verify-test/SKILL.md`。

## 子代理 dispatch 契约

- 必须声明 **model**（版本/提供商），便于复现与回溯。
- 必须说明 **审查边界**：哪些问题要拦截（P0/P1）、哪些仅建议（P2/P3）。
- 禁止指示审查员忽略问题；只能补充更多证据（日志/测试/文件:行号）。

## 产出

- 代码 + 单元测试 + 功能测试 + 使用示例
- PR（附 PR Summary）

## 约束（不可回调）

- P0 无法满足时**停止上报**，不自行降低标准。
- 不超出 Issue 范围（YAGNI）。
- 中文注释用 UTF-8，避免乱码。

## 工程纪律（服务/模块类代码）

写任何对外交付的服务或模块时（与是否重构无关），遵守：

- **密钥纪律（硬规则）**：API key 等敏感信息永不进代码库。`.env` 进 `.gitignore`；`.env.example`（仅字段说明）进 git；生产环境由部署平台注入。一旦真实 key 进了 git 历史，必须重写历史 + 立即吊销 key。
- **诊断字段白名单（硬规则）**：接外部 connector/MCP/API 时，诊断与日志只输出白名单字段（工具名/状态/数量/耗时/错误码/来源 host），**禁止整体序列化** URL query/headers/auth/原始 Action/ExecutionResource（真实事故：诊断整体序列化执行资源暴露认证头）；泄露即轮换 token 并记录「已轮换/无法审计第三方是否已撤销」。完整清单见 `templates/connector-isolation-checklist.md`。
- **配置三层覆盖**：代码默认值（兜底）← 配置文件（本地开发）← 环境变量（部署注入，最高优先级）。目标：同一份代码不改一行能跑在任何环境。
- **职责分层看「不该做什么」**：接入层不做业务判断、不调模型；业务层不感知协议（HTTP 等）、不直接读环境变量；配置层不混业务逻辑。
- **封装边界**：调用方代码里不应出现内部实现的框架名/模型名，出现即泄漏。

## 常见错误

- **不写测试就提交** → 违反三层测试要求，必被 review 退回。
- **越界实现** → 顺手改了别的功能，破坏其他 Issue。严守边界。
- **撞墙硬写** → 同一问题反复失败仍不调研，浪费 token。2 次失败即委托 explore。
- **dispatch 未写边界** → 子代理/审查员标准漂移；必须写清 P0/P1 拦截与 P2/P3 建议边界。
- **密钥写进代码** → 换环境要改代码重新发布，且 key 有泄漏进 git 历史的风险。从第一行代码起就走环境变量。
- **把「让你改代码」当成「让你发布」** → 擅自 push/merge/发 Release。远程写操作逐项授权，没说就不做。

## 参考

- 模板：`templates/pr-summary-template.md`
- 涉及模型/外部服务/连接器：`reference/model-and-connector-guide.md`（失败关闭门禁 + 三层不变量 + 连接器隔离）
- 配套：`skills/verify-test/SKILL.md`、`skills/verify-review/SKILL.md`
- 借鉴：`reference/vendored-skills/superpowers/skills/test-driven-development`、`subagent-driven-development`（参考基线：Superpowers v6.0.x；已对照 v6.1.1 做增量优化）
