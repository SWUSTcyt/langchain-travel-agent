---
spec_id: SPEC-003
title: 旅游助手前端现代化
status: Frozen
version: 1
parent: SPEC-001
supersedes:
superseded_by:
---

# Spec: 旅游助手前端现代化

> 2026-10-20 只补了上面的编号和 parent，便于挂到 `docs/spec/INDEX.md`。下面的范围、验收和「后端零改动」都没改。状态标 Frozen 是因为这份范围早已确认并已实现；这次没有重跑验收，所以不标 Verified。

> 由 vibe-coding-playbook 的 plan-spec 流程产出。方案 A：保留 Gradio，做现代主题 + 自定义 CSS + 布局重构（纯 Python，后端零改动）。

## 一句话描述

把现有 Gradio 旅游助手界面重构为现代、美观、响应式的对话界面，给 C 端用户使用。

## 核心功能

- [ ] 现代化视觉：主题（gr.themes）+ 外置自定义 CSS（配色、圆角、间距、字体）
- [ ] 对话区美化：消息气泡、用户/AI 区分、流式输出体验
- [ ] 「💭 AI 思考过程」可折叠展示（保留现有 reasoning 能力，不回退）
- [ ] 顶部品牌区（标题 + 简介 + 示例问题）
- [ ] 开发者模式 + 过程日志（折叠到侧栏/抽屉，不干扰主对话）
- [ ] 响应式布局（桌面双栏 / 移动单栏）

## 边界条件（不在范围内）

- 不改后端 Agent 逻辑：`agent.py` / `tools.py` / `middleware.py` / `config.py` 不动
- 不改 `stream_answer()` / `on_submit()` 的事件流与 reasoning 累积逻辑（仅在其外层重构 UI）
- 不改 MCP / Qwen 接入方式
- 不做用户登录 / 多会话持久化 / 后端 API 化（那是方案 B）

## 非功能性需求

| 维度 | 要求 |
|---|---|
| 性能 | 首屏 < 2s；流式输出无明显卡顿 |
| 安全 | 坐标脱敏（_mask_coord）保留；前端不暴露 API Key |
| 可维护性 | 样式与逻辑分离（CSS 外置/集中）；主题与配色可配置 |
| 兼容 | Gradio >= 4.1；沿用 `python main.py` 启动 |

## 技术约束

| 项 | 选择 |
|---|---|
| 语言 | Python |
| 框架 | Gradio（gr.Blocks + gr.themes + custom CSS） |
| 部署环境 | 本地 `python main.py`（127.0.0.1） |
| 虚拟环境 | `pj-04-langchain-agent` |

## 验收总纲（P0）

1. 现有对话、流式输出、reasoning 折叠展示、开发者模式/日志功能均不回退
2. 后端文件（agent/tools/middleware/config）零改动
3. 新界面在桌面与移动端均可正常使用，视觉明显现代化
