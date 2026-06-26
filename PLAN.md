# 项目: 旅游助手 | 状态: M1 已完成 + P0 已修 + E2E 通过

> 项目状态唯一真源（≤500 tokens）。方法论见 vibe-coding-playbook。

## 当前 Milestone: M1 - Gradio 现代化主题 MVP [100%]

## Issue 状态

- [x] #1 抽离样式层：主题(gr.themes.Soft) + 外置 custom.css → done
- [x] #2 布局重构：顶部品牌区 + 主对话区 + 侧栏（日志/开发者） → done
- [x] #3 对话区美化：气泡布局、输入框+发送按钮、示例问题 → done
- [x] #4 reasoning 与日志面板适配新布局（保留 details 折叠与 dev 模式） → done
- [x] #5 响应式：移动端断点（双栏→单栏，@max-width 860px） → done
- [x] P0: enforce_city_on_tools city 注入修复 → done（req.override(tool_call=...)）
- [x] P0: 模型名 qwen-turbo-latest 403 → done（改为 qwen-turbo）

## 关键决策（不可回调）

- 方案 A：Gradio 主题 + CSS + 布局重构，后端零改动
- stream_answer 返回 4 值（+reasoning_text），前端已适配
- Gradio 6：theme/css 在 launch() 传入；Chatbot 用 buttons=["copy"]

## 验收分级

P0：功能不回退；P1：核心视觉/布局；P2：边界；P3：锦上添花。

## 自查结论

- P0 ✅ E2E 全链路通过（enforce_city_on_tools 注入 city=成都 + MCP 3 工具正常返回）
- P1 ✅ Soft 主题 + custom.css + 双栏布局
- P2 ✅ 空态 placeholder、输入 max_lines=4、清空可复位
- P3 ✅ 气泡布局、标签、示例问题
- Skills ✅ 两层安装完成（playbook 7 个 + 项目 2 个 → .cursor/ 和 .claude/）
- 文档 ✅ ARCHITECTURE.md 已与代码对齐（模型名/工具名/中间件逻辑/stream 返回值）
