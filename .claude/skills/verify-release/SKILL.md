---
name: verify-release
description: 发布与合并安全门禁。Use when 阶段开发结束、需要 commit/push/开 PR/合并代码时，尤其是让 Agent 自动帮你提交并合并的场景。也适用于需要在提交前做 secret/客户文件扫描、区分单人与协作开发、避免误合误推的场景。
---

# Verify-Release：发布与合并安全

## 概述

把「实现完成」到「安全进主干」这一段做成固定验收阶段，而不是靠临时记忆。核心是：**每一步都有明确停止点，宁可停下问，也不误报完成、不误合、不误推。**

**核心原则：** commit / push / 开 PR / merge 是四个独立授权动作（见 execute-implement「外部写操作授权」）；本 skill 负责在获得授权后，把每个动作的安全门禁落到位。

## 何时使用

- 阶段开发结束，要把变更提交并合并（尤其是让 Agent 自动帮你 commit + merge 的场景）
- 混合工作树里只想发布其中一部分变更
- 不确定当前是单人仓库还是协作仓库，怕漏掉配合环节

**何时不用：** 只在本地改文件、明确未获授权做远程写操作时——那就停在本地，不进入本 skill。

## 固定流程（逐步停止点）

1. **读现状** — `git status`、当前分支、远端、默认分支、最近提交。搞清「现在在哪、要发到哪」。
2. **判协作场景** — 见下方「协作感知」。先确定单人还是协作，后面的自合/推送规则不同。
3. **定拟纳入 allowlist** — 明确列出要提交的路径。混合工作树**逐路径确认**；**禁止无审查的 `git add .` / `git add -A`**。客户数据/运行产物/密钥目录必须排除。
4. **可见性检查** — 读远端仓库 visibility。若与预期不符（如本应 private 却是 public），**停止并上报**，不推送。
5. **开发分支** — 在默认分支基础上创建 feature branch，**不直接在 main/master 提交**。
6. **提交前扫描（staged diff）** — 对已 staged 内容做：
   - secret / token / 认证头扫描；
   - PII / 客户文件名扫描；
   - `git diff --check`（行尾/冲突标记）；
   - 相关测试 + lint。
   任一命中 → 停止修复，不带病提交。
7. **建 PR（forge-neutral）** — 用当前 forge 的 CLI 或 push 后打印的 URL 建**一个** PR，不硬编码某一家工具。记录 base / head / commit SHA / checks。
8. **合并门禁** — required checks / required review 未通过**不得合并**。
9. **合并后回执** — 合并后再读一次 PR 状态与 base 分支 SHA，生成发布记录（PR 号/URL、merge 方式、merge commit/base SHA、合并时间、验证命令）。

全程对照 `templates/release-safety-checklist.md` 逐项打勾。

## 协作感知（单人 vs 协作，规则不同）

先判断当前仓库是不是协作开发，避免「一个人的习惯」在多人仓库里造成配合疏漏：

**判为协作的信号（命中任一即按协作处理）：**

- 默认分支设了保护规则 / required reviewers / CODEOWNERS；
- 远端存在他人的活跃分支或未合并 PR；
- 仓库有多个 contributor / 组织仓库；
- 存在 CI required checks。

| 场景 | 自动 merge | force-push | 直接推 main |
|---|---|---|---|
| 单人本地/私有仓库（无保护、无他人 PR） | 获授权后可自合 | 仅限自己的私有分支，且需显式授权 | 禁止（仍走 feature branch + PR） |
| 协作仓库 | **禁止自合**，交由 required review / 负责人合 | **禁止对共享分支 force-push** | 禁止 |

协作仓库额外停止点：发现他人正在同一区域改动、PR 有未解决 review、required check 缺失时——**停下上报**，不替他人拍板合并。

## 破坏性操作（打字确认）

以下动作即使获得授权，也要先复述影响、再等用户显式确认（对齐 Superpowers v6.3.0）：

- `git push --force` / 重写已推送历史；
- 删除分支 / 丢弃未合并工作；
- **删除 worktree 时若存在未提交/未跟踪文件**：不要 `--force`，先停下、列出这些文件、问用户，别销毁工作。

## 产出

- 填好的 `templates/release-safety-checklist.md`
- 一个 PR（含 base/head/SHA/checks）
- 合并后发布回执

## 常见错误

- **`git add .` 一把梭** → 把客户文件/密钥/无关改动一起提交。必须 allowlist 逐路径。
- **直接在 main 提交/合并** → 绕过 review 与 checks。永远走 feature branch + PR。
- **可见性没核实就推** → 私有内容进了 public 仓库。推送前必查 visibility。
- **协作仓库自动自合** → 抢了他人 review、埋下配合疏漏。命中协作信号就不自合、不 force-push 共享分支。
- **把「合并成功」当「上线完成」** → 合并只证明代码进远端，不改变产品上线状态。上线以各项目自己的上线门禁为准。
- **计划当事实回写** → 命令未执行就把发布记录写成完成。回执逐项在动作完成后填。
- **把人读方法论长文当发布完成条件** → 清单里那一项仅人、可选。Agent 跳过：不打开、不更新该文件。

## 参考

- 模板：`templates/release-safety-checklist.md`、`templates/pr-summary-template.md`
- 授权分权：`skills/execute-implement/SKILL.md`「外部写操作授权」
- 未授权写=P0：`skills/verify-review/SKILL.md`
- 借鉴：Superpowers `finishing-a-development-branch`（v6.3.0：forge-neutral PR、破坏性操作打字确认、worktree 删除不销毁未跟踪文件）
