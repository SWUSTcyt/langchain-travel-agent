# 更新日志 (CHANGELOG)

## [v1.2.1] - 2026-06-26

### 文档更新与版本同步

#### 1. **ARCHITECTURE.md 文件结构更新**
- 更新文件结构树，反映最新的项目组织
- 新增 `assets/custom.css` 自定义样式文件
- 新增 `docs/issues-log.md` 问题记录文档
- 新增 `.claude/skills/` 和 `.cursor/skills/` 两层 skill 目录结构
- 更新 `main.py` 和 `ui.py` 的功能说明注释

#### 2. **版本同步与 Git 提交**
- 统一提交所有 v1.2.0 变更到 GitHub
- 包括：P0 修复、前端现代化、Skills 体系建设、文档对齐
- 确保代码库与文档保持一致

### 📁 文件变更

#### 修改文件
- `docs/ARCHITECTURE.md` - 更新文件结构树，反映最新项目组织

---

## [v1.2.0] - 2026-06-26

### P0 Bug 修复

#### 1. **enforce_city_on_tools city 注入修复**
- **问题**: `enforce_city_on_tools` 使用 `req.override(tool_input=params)` 注入城市参数，但 LangGraph 的 `override()` 只支持 `tool_call` 字段，异常被 `except: pass` 吞掉，导致 city 未注入、MCP 工具报错
- **修法**: 改为 `req.override(tool_call=modified_call)`，正确构造完整的 tool_call dict，区分 dict/对象两种 `tc` 类型；从模块级缓存 `_target_cities_cache` 读取城市
- **验证**: E2E 全链路通过 — 3 个工具调用全部注入 `city=成都`，MCP 正常返回（maps_text_search 1396+6524 字符，maps_weather 1600 字符）

#### 2. **模型名 403 修复**
- **问题**: `qwen-turbo-latest` 返回 403 AccessDenied，被通义 SDK 包装成 `KeyError: 'request'` 掩盖真实错误
- **修法**: `agent.py` 第 37 行 `qwen-turbo-latest` → `qwen-turbo`

### 前端现代化（Gradio 6 适配）

#### 3. **UI 重构**
- 主题：`gr.themes.Soft`（teal + blue + slate），CSS 在 `launch()` 时注入
- 布局：顶部品牌区 + 双栏（对话区 3 : 侧栏 1）+ 响应式断点（`@media max-width: 860px`）
- Chatbot：气泡布局、`buttons=["copy"]`、placeholder 空态提示
- 示例问题：`gr.Examples` 降低上手门槛
- 调试面板：开发者模式 JSON + 过程日志折叠

#### 4. **Gradio 6 API 迁移**
- `theme`/`css` 从 `gr.Blocks()` 移到 `launch()`
- `gr.Chatbot` 去掉 `type="messages"`（Gradio 6 默认 messages 格式）
- `show_copy_button=True` → `buttons=["copy"]`

### Skills 体系建设

#### 5. **两层 skill 安装**
- **playbook 流程 skill（7 个）**: plan-spec / plan-breakdown / execute-implement / verify-test / verify-review / observe-session / improve-retro
- **项目自有 skill（2 个）**: understand（架构分析）/ feature（功能开发）
- 安装到 `.cursor/skills/` + `.claude/skills/`，两层结构统一

#### 6. **项目 skill 格式优化**
- understand / feature 按 playbook 写作规范重写：description 改为 `Use when...` 触发格式；正文补「概述/何时使用/流程/产出/常见错误/参考」标准节
- 新增常见错误：禁止 `except: pass` 裸吞异常、改动后文档必须同步

### 文档对齐

#### 7. **ARCHITECTURE.md 修正 4 处 drift**
- 模型名 `qwen-turbo-latest` → `qwen-turbo`（2 处）
- 工具名 `searchPOI/getRoute/getWeather` → `maps_text_search/maps_direction_*/maps_weather`（Mermaid 图 + 事件流 + 工具列表，10+ 处）
- `enforce_city_on_tools` 代码片段更新为 `req.override(tool_call=...)` + 模块级缓存
- `stream_answer` 更新为 4 值返回 + reasoning 提取逻辑

### 📁 文件变更

#### 修改文件
- `agent.py` - 模型名 qwen-turbo-latest → qwen-turbo
- `middleware.py` - enforce_city_on_tools 修复（req.override + dict/对象兼容）
- `ui.py` - 前端现代化（主题/布局/Chatbot/响应式/Gradio 6 适配）
- `main.py` - launch() 注入 theme + css
- `PLAN.md` - 状态同步（P0 已修 + E2E 通过 + skills 已安装）
- `docs/ARCHITECTURE.md` - 修正 4 处 drift
- `docs/issues-log.md` - P0 标记已修 + 新增记录

#### 新增文件
- `assets/custom.css` - 自定义样式（旅行主题 + 响应式断点）
- `.cursor/skills/` - 9 个 skill（playbook 7 + 项目 2）
- `.claude/skills/plan-spec/` 等 7 个 playbook skill

---

## [v1.1.0] - 2026-01-22

### 🆕 新增功能

#### 1. **AI 深度思考过程展示**
- 启用 Qwen 的 `enable_thinking=True` 功能，展示完整推理过程
- `ui.py` 中 `stream_answer()` 函数新增 reasoning 提取逻辑
  - 从 `AIMessage.additional_kwargs['reasoning_content']` 逐块累积思考内容
  - 返回值从 3 个增加到 4 个（新增 reasoning_text）
- 前端新增 **"💭 AI 思考过程"** 可折叠面板
  - 用户可选择查看 AI 的完整推理链
  - 包含意图理解、策略规划、信息整合等步骤

#### 2. **Claude Skills 集成**
- **understand Skill** (`.claude/skills/understand/`)
  - 深度分析项目架构、Agent 配置及 MCP 集成
  - 自动生成 `docs/ARCHITECTURE.md` 中文架构文档
  - 包含系统设计、中间件详解、优化方向等完整说明

- **feature Skill** (`.claude/skills/feature/`)
  - 基于架构规范安全地实现新功能或优化现有代码
  - 符合项目最佳实践

### 📝 文档更新

- **README.md**
  - 新增功能特性说明（思考过程、Claude Skills）
  - 添加新增功能详细说明章节
  - 新增项目结构图
  - 补充技术栈版本对照表
  - 补充贡献指南和相关文档链接

- **CHANGELOG.md**（本文件）
  - 记录版本更新历史

- **docs/ARCHITECTURE.md**（由 understand Skill 生成）
  - 完整的中文架构文档
  - 包含系统设计、API 设计、优化方向等

### 🔧 技术改进

#### `ui.py` 修改

**`stream_answer()` 函数**：
```python
# 旧签名
def stream_answer(...) -> Tuple[str, str, Any]:
    yield (final_text, md_text, raw_events)

# 新签名
def stream_answer(...) -> Tuple[str, str, str, Any]:  # ← 返回 4 个值
    yield (final_text, md_text, reasoning_text, raw_events)
```

**主要改动**：
- 从所有 AIMessage 块中逐块提取 `reasoning_content`
- 遍历而非仅取最后一条消息，确保完整累积
- reasoning 数据分离返回，前端可独立处理

**`create_gradio_app()` 函数**：
- 新增 `reasoning_md` Markdown 组件
- 在 `on_submit()` 中接收并处理 reasoning 返回值
- 更新 `txt.submit()` 和 `clear_btn.click()` 的 outputs 列表

### 📊 性能影响

| 方面 | 影响程度 | 说明 |
|-----|--------|------|
| CPU | 轻微 ↓ | 字符串拼接操作极少 |
| 内存 | 可忽略 | reasoning 通常 < 2KB |
| 网络 | 轻微 ↓ | 前端额外传输 < 2KB 数据 |
| 用户体验 | 正面 ↑↑ | 透明度显著提升 |
| 加载时间 | 无影响 | 流式传输，不增加延迟 |

### 🧪 测试

- 验证 reasoning_content 提取（通过 `test_reasoning.py`）
- 确认 Gradio UI 正确展示思考过程
- 测试清空功能、开发者模式兼容性

### 📁 文件变更

#### 修改文件
- `ui.py` - 新增 reasoning 支持
- `README.md` - 更新功能说明
- `.gitignore` - 忽略测试文件

#### 新增文件
- `CHANGELOG.md` - 本文件
- `.claude/skills/understand/` - 架构分析 Skill
- `.claude/skills/feature/` - 功能开发 Skill
- `docs/ARCHITECTURE.md` - 详细架构文档

### 🚀 升级指南

对于已有的用户，只需 `git pull` 即可获得新功能，无需特殊配置。新功能在首次对话时自动启用。

### 已知问题

- 如果终端编码不支持 UTF-8，可能显示乱码（Windows 环境）
  - 解决：在 `ui.py` 开头添加 `sys.stdout.reconfigure(encoding='utf-8')`

### 下一步计划

- [ ] 支持多语言 reasoning 展示
- [ ] 优化 reasoning 长度控制（过长时截断）
- [ ] 支持导出完整推理链（PDF/Markdown）
- [ ] 增加 reasoning 语义分析和分段
- [ ] 时间线可视化（思考步骤 → 工具调用 → 答案生成）

---

## [v1.0.0] - 初始版本

- 基础 Agent 框架
- MCP 工具集成
- 中间件系统
- Gradio UI
- 并行工具调用支持
