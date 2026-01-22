# 更新日志 (CHANGELOG)

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
