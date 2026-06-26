# 问题记录 issues-log

> 本项目踩坑与解法记录（栈特定，归属本项目）。格式见 vibe-coding-playbook 的 improve-retro。
> 通用的流程教训请提炼进 playbook，不要堆在这里。

---

### 2026-06-19: qwen-turbo-latest 无权限，被包装成 KeyError: 'request'

- **出现位置**: M1 前端现代化「真实对话联调」阶段（model 节点）
- **问题**:
  - 现象：`KeyError: 'request'`，`During task with name 'model'`。
  - 调用链：`ui.py → stream_answer → agent.stream → middleware → ChatTongyi.invoke → DashScope API → check_response()`。
  - 真因：DashScope 对 `qwen-turbo-latest` 返回 **403 AccessDenied**，当前 API Key 无权访问该模型。
  - 表面异常：`langchain_community` 用 `requests.HTTPError(response=dashscope_resp)` 抛错，DashScope 响应对象无 `request` 字段，被包成 `KeyError: 'request'`，掩盖了真实 403。
  - 诊断（未改代码）：`qwen-turbo` / `qwen-plus` / `qwen-plus-latest` 均 200 OK；仅 `-latest` 的 turbo 无权限；`qwen-omni-turbo-latest` 需 OpenAI 兼容接口。
- **最终解法**: `agent.py` 第 37 行模型名 `qwen-turbo-latest → qwen-turbo`（仅此一处，其余 ChatTongyi / 流式 / enable_thinking / middleware / MCP 不动）。
- **可复用规则**:
  - DashScope/通义报 `KeyError: 'request'` 时，先怀疑 **HTTP 4xx（尤其 403 模型无权限）**，而非框架 bug。
  - 切模型前先用最小脚本逐个探测模型可用性（裸 DashScope API + ChatTongyi 各一次），再定方案。

---

### 2026-06-19: 复杂规划触发 MCP 工具时 city 参数未注入（ToolException）**[已修]**

- **出现位置**: 换模型后 Gradio 实测，旅游规划类问题（tools 节点）
- **问题**:
  - 现象：`ToolException: Error: Cannot read properties of undefined (reading 'city')`，`During task with name 'tools'`。
  - 调用链：`agent.stream → 模型 tool_calls → tool_node → enforce_city_on_tools → tools.py(MCP 异步包装) → 高德 MCP Server`。
  - 根因：`enforce_city_on_tools` 用了 `req.override(tool_input=params)`，但 LangGraph 的 `ToolCallRequest.override()` 只支持 `tool_call`，不支持 `tool_input`；异常被 `except: pass` 吞掉。
- **最终解法**: ✅ 已修（2026-06-26 验证通过）
  - `middleware.py` `enforce_city_on_tools`：改为 `req.override(tool_call=modified_call)`，区分 dict/对象两种 `tc` 类型，从模块级缓存 `_target_cities_cache` 读取城市
  - System Prompt 工具名已与真实 `maps_*` 对齐（无需改，原来就是对的）
  - E2E 验证：3 个工具调用全部注入 `city=成都`，MCP 正常返回
- **可复用规则**:
  - 用框架 API（如 `override`）前先确认其**支持的字段**，不要凭直觉传参；`except: pass` 会掩盖此类用法错误，禁止裸吞异常。

---

### 2026-06-19: Gradio 6 迁移——theme/css 移至 launch()、Chatbot 参数变化

- **出现位置**: M1 前端重构（ui.py / main.py）
- **问题**:
  - `gr.Blocks(theme=..., css=...)` 在 Gradio 6 报 `TypeError: BlockContext.__init__() got an unexpected keyword argument 'theme'`。
  - `gr.Chatbot` 去掉了 `type`（只剩 messages 格式）与 `show_copy_button`。
- **最终解法**:
  - `theme/css/css_paths` 改在 `launch()` 时传入（`main.py`）；`Blocks` 只保留 `title`。
  - `Chatbot`：去掉 `type="messages"`；`show_copy_button=True → buttons=["copy"]`；并用 `layout="bubble"` + `placeholder`。
  - 验证：构建冒烟 SMOKE-OK；非阻塞 launch 返回 HTTP 200。
- **可复用规则**:
  - 跨大版本依赖（Gradio 4→6 等）迁移前，先用 `inspect.signature` 或读源码确认真实 API，再改代码。
  - 升级类改动至少做「构建冒烟 + 非阻塞起服务」两层；但这只是 L1，业务链路仍需真实端到端验证。

---

### 2026-06-26: stream_answer 返回值从 3→4（reasoning 分离）

- **出现位置**: ui.py `stream_answer()` 函数
- **问题**: 原 `stream_answer` 返回 3 个值 `(final_text, md_text, raw_events)`，reasoning 内容混在 final_text 中
- **最终解法**: 返回 4 个值 `(reasoning_text, final_text, md_text, raw_events)`，reasoning 从 `AIMessage.additional_kwargs['reasoning_content']` 逐块独立累积，前端通过 `<details>` 折叠展示
- **影响**: `on_submit` 的解包顺序同步更新；无破坏性变更

---

### 2026-06-26: 两层 skill 安装 + 文档对齐

- **出现位置**: 项目全栈（playbook 流程落地）
- **动作**:
  - 从 playbook 安装 7 个流程 skill（plan-spec/plan-breakdown/execute-implement/verify-test/verify-review/observe-session/improve-retro）到 `.cursor/skills/` 和 `.claude/skills/`
  - 项目自有 skill（understand/feature）从 `.claude/skills/` 同步到 `.cursor/skills/`，并按 playbook 写作规范优化格式
  - `docs/ARCHITECTURE.md` 修正 4 处 drift（模型名、工具名、中间件逻辑、stream 返回值）
  - E2E 验证通过（enforce_city_on_tools 注入 + MCP 工具链路）

---

## 已提炼进 playbook 的通用规则（避免污染本项目记录）

- 「P0 功能不回退」必须包含**关键路径真实端到端冒烟**；跑不了标 blocked，不标 done。
  → 已写入 `vibe-coding-playbook/skills/verify-test/SKILL.md`（验收硬规则 + 常见错误）。
