# SKILL.md 写作规范小抄

> M0 产出。提炼自三份权威来源 + 优秀样例，供 M2 自研五层 skill 时统一风格。
> 来源：Anthropic `skill-creator`、superpowers `writing-skills`、Cursor 内置 `create-skill`；  
> 参考基线：`reference/vendored-skills/superpowers/`（v6.0.x），已与 `superpowers@6.1.1` 直接对比并做增量优化。
> 样例：`brainstorming`、`writing-plans`、`test-driven-development`。

---

## 1. 一个 Skill 的结构

```
skill-name/
├── SKILL.md          # 必需：YAML frontmatter + Markdown 正文
├── references/       # 可选：大段参考文档（按需读取，>300 行加目录）
├── scripts/          # 可选：可执行脚本（确定性/重复性任务，省 token）
└── assets/           # 可选：输出用模板/图标/字体
```

- **扁平命名空间**：所有 skill 放同一层，靠 `name` 检索。
- **能内联就内联**：原则、概念、<50 行代码片段直接写在 SKILL.md；只有「重型参考(100+行)」和「可复用脚本」才拆文件。
- **引用只下一层**：SKILL.md 直接链到参考文件，不要多层嵌套（深层可能只被部分读取）。

## 2. 渐进式披露（三级加载，必须理解）

| 级别 | 内容 | 何时加载 | 体量 |
|---|---|---|---|
| 1 | frontmatter（name + description） | 永远在上下文 | ~100 词 |
| 2 | SKILL.md 正文 | skill 被触发时 | < 500 行 |
| 3 | references/scripts/assets | Agent 按需读取/执行 | 不限 |

正文逼近 500 行就再拆一层，并明确写「需要时去读哪个文件」。

## 3. Frontmatter 规范

```yaml
---
name: skill-name              # 仅小写字母/数字/连字符，≤64 字符
description: Use when ...      # ≤1024 字符（建议 <500），第三人称
---
```

- **name**：动词优先 / 动名词（-ing）。`creating-skills` 优于 `skill-creation`；`root-cause-tracing` 优于 `debugging-techniques`。不要 `helper`/`utils`/`tools`。
- **description 是触发的唯一机制**，最关键。要点：
  - **第三人称**（会被注入系统提示）。不要「I can help...」「You can...」。
  - 以 **"Use when..."** 开头，写清**触发条件/症状/场景**。
  - 关键词覆盖：错误信息、症状词、同义词、工具/库/文件名——Agent 会按这些检索。
  - 技术无关的触发描述「问题」（竞态、不一致）而非「语言症状」（setTimeout/sleep）；除非 skill 本身就绑定某技术，则显式写明。

### 三家的一个分歧（重要，按下面折中）
- **superpowers**：description **只写 WHEN（触发条件），绝不概述 workflow**。理由：实测发现 description 一旦概述流程，Agent 会「照着 description 做」而跳过读正文，导致漏步骤。
- **Anthropic / Cursor**：description 写 **WHAT + WHEN**，且对「触发不足」要稍微"pushy"一点。
- **本项目折中**：description 以触发条件为主、可含一句话能力概述，但**绝不把多步流程写进 description**（流程留在正文）。

## 4. 正文写作原则

- **简洁**：默认 Agent 很聪明，只补它不知道的。每段都问「这段值它的 token 吗？」。
- **祈使句**：用命令式写指令。
- **讲清 WHY 而非堆砌 MUST**（Anthropic/superpowers 共识）：今天的模型有 theory of mind，解释清楚「为什么重要」比生硬全大写 MUST 更有效、更稳。
- **自由度匹配任务脆弱性**：
  - 高自由度（纯文字）→ 多种合法解法、依赖上下文（如代码评审准则）
  - 中（伪代码/模板）→ 有偏好模式但可变（如报告生成）
  - 低（具体脚本）→ 脆弱、必须一致（如数据库迁移）
- **术语一致**：选定一个词贯穿全文（别 URL/route/path 混用）。
- **一个出色的例子胜过多个平庸例子**；不要多语言堆叠、不要填空模板、不要造作示例。

### 「让形式匹配失败类型」（superpowers 关键洞察）
| 基线失败 | 正确形式 | 错误形式 |
|---|---|---|
| 压力下违反规则（知道却不做） | 禁令 + 理由化对照表 + 红旗清单 | 软建议（"prefer/consider"） |
| 照做但输出形状错（冗长/重点埋没） | 正向配方/契约：直接规定输出「是什么、含哪些部分、顺序」 | 禁令清单（"别 restate"） |
| 漏掉本该产出的必填项 | 结构化：模板里设 REQUIRED 字段/槽位 | 模板旁的散文提醒 |
| 行为应依条件而定 | 基于可观察谓词的条件句（"若 X 存在则…"） | 无条件规则 + 例外条款 |

**可执行样例（最小句式）**  
- 压力下违反规则：`禁止跳过 verify-review；若跳过则必须在 PR 说明写明原因并给出补偿步骤。`  
- 输出形状错：`输出必须为 Review Packet：结论 / P0 / P1 / 必须修改 / 证据引用（至少一条）。`  
- 漏必填项：`测试计划模板中「预期结果」为 REQUIRED，缺失则退回。`  
- 条件行为：`若缺密钥无法 E2E，则该项标 blocked 并写明替代验证与解除条件。`

## 5. 跨工具落地路径（本项目核心诉求）

| 工具 | Skill 存放位置 | 说明 |
|---|---|---|
| Cursor（项目） | `.cursor/skills/skill-name/SKILL.md` | 随仓库共享 |
| Cursor（个人） | `~/.cursor/skills/skill-name/` | 跨项目；**禁止**写 `~/.cursor/skills-cursor/`（系统内置区） |
| Claude Code | `.claude/skills/skill-name/SKILL.md` | 同 SKILL.md 格式 |
| Codex / Copilot / Gemini | 识别跨运行时别名 `~/.agents/skills/` | 另靠 `AGENTS.md` 兜底 |

- 三家都读 `SKILL.md`，所以**一份真源可复用**；本项目策略：`skills/` 为真源，各工具目录做同步/适配。
- `AGENTS.md`（仓库根）是跨工具通用入口，写三铁律 + 五层 + 指向 skills/templates。

### Cursor 专属：`disable-model-invocation`
```yaml
disable-model-invocation: true   # 默认建议：仅在被显式点名时加载
```
只有当希望 Agent 从上下文自动触发时才省略它。流程类 skill（plan/verify 等）建议允许自动触发；强约束类可按需点名。

## 6. 反模式清单（写完自检）

- ❌ 叙事体（"在 2025-10-03 那次我们发现…"）→ 不可复用
- ❌ 多语言稀释（同一示例 js/py/go 各一份）
- ❌ 流程图里塞代码 / 无语义的标签（step1、helper2）
- ❌ Windows 反斜杠路径（用 `scripts/helper.py`）
- ❌ 时效性信息（"2025 年 8 月前用旧 API"）→ 改用「旧模式」折叠区
- ❌ description 用第一人称 / 概述完整 workflow
- ❌ 给一堆并列选项（给一个默认 + 逃生出口）

## 7. 本项目五层 → 可借鉴的现成 skill 映射

真源在 `reference/vendored-skills/`，仅作风格/结构借鉴，不直接当交付。

| 本项目层 | 自研 skill（M2） | 可借鉴的 vendored skill |
|---|---|---|
| Plan | `plan-spec`、`plan-breakdown` | superpowers `brainstorming`、`writing-plans` |
| Execute | `execute-implement` | superpowers `test-driven-development`、`subagent-driven-development`、`dispatching-parallel-agents`、`executing-plans` |
| Verify | `verify-test`、`verify-review` | superpowers `requesting-code-review`、`receiving-code-review`、`verification-before-completion`、`systematic-debugging` |
| Observe | `observe-session` | （开源较少，自研为主） |
| Improve | `improve-retro` | superpowers `writing-skills`（提炼规则/沉淀 skill 的方法） |
| 元能力 | 写/测 skill 本身 | Anthropic `skill-creator`、superpowers `writing-skills`、Cursor `create-skill` |
| 试点相关 | （M4 前端重构用） | Anthropic `frontend-design`、`webapp-testing` |

## 8. SKILL.md 起手模板（本项目统一用）

```markdown
---
name: layer-action
description: Use when <触发条件/症状/场景，第三人称，关键词丰富>
---

# <Skill 名称>

## 概述
这是什么？核心原则 1-2 句。

## 何时使用
- 触发症状/场景（bullet）
- 何时**不**用

## 流程
1. 步骤（祈使句，必要处给模板/命令/预期输出）
...

## 产出
明确定义输出物（含格式模板）。

## 常见错误
出错点 + 修法。

## 参考
- 需要时读 references/xxx.md（说明何时读）
```

---

> 备注：`reference/vendored-skills/` 是 vendored 第三方仓库（含各自 .git），建议在仓库 `.gitignore` 忽略，避免嵌套 git 与体积污染。
