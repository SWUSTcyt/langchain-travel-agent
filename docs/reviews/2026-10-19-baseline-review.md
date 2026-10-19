# 基线评审：旅游助手

- 日期：2026-10-19
- 范围：现有产品代码与文档，外加「它作为 Agent 项目，规划是否合适」。本轮不改产品行为。

## 结论：不能把当前状态写成功能已通过

真实对话没有走完。界面能打开，用户发出「成都今天天气」后只看到红色 Error，没有行程答案，也没有地图工具调用。`PLAN.md` 里「E2E 全链路通过」不能继续当成当前事实。

## P0 检查：不通过

## P1 检查：不通过

## 做得好的

这些有代码或测试对得上，建议保留，不要为了「更像一个大 Agent」拆掉。

- 框架选得对。这是一个目的固定、工具集合固定的旅行助手。官方 `ecosystem-primer` 的判定顺序是：要长程规划、文件、子代理、跨会话记忆才用 Deep Agents；要手写分支图才用 LangGraph；单一职责用 LangChain `create_agent`。代码走的是最后一档，见 `agent.py` 第 51–68 行。
- 约束放在中间件，而不是另写一张图。城市、预算、未点名城市，都挂在 `create_agent` 的 middleware 上。这和官方 `langchain-middleware` 的扩展点一致。
- 只读地图工具没有加人审。`reference/agent-design-guide.md` 写明：只读查询不要加无意义的确认。这里不需要 Human-in-the-loop。
- 不需要向量知识库。事实来自高德工具的当次返回，不是一份要切片召回的文档库。不要为了对齐 `langchain-rag` 去加向量库。
- 用户点了城市时，注入是成功的。离线测试 `test_named_city_is_injected_before_map_tool_runs` 通过：`maps_weather` 收到 `city=成都`，原来的 `adcode=330100` 被清掉。
- 坐标脱敏生效。`104.065735,30.659462` 变成 `104.066,30.659`，工具日志里也不再出现完整坐标。`tests/test_offline_baseline.py` 的 `MaskCoordTest` 通过。
- 没有密钥时不会去构造模型。子进程把 `DASHSCOPE_API_KEY` 置空后导入 `ui`，抛出 `RuntimeError`，`ChatTongyi` 构造次数为 0，`load_tools` 也没被调用。
- 界面骨架在。`http://127.0.0.1:7860/` 返回页面，有标题、示例问题、输入框、发送、调试侧栏。发出问题后，日志里出现「解析城市：成都」。样式断点在 `assets/custom.css` 第 110 行。

## 必须修改

### P0 必要：供应商报错被包成 KeyError，界面直接崩溃

- 是否必要：必要。用户已经碰到。
- 建议：先改这个。不要靠换成 `qwen-plus` 绕开。
- 事实：同一把密钥下，`qwen-turbo` 返回 HTTP 429 `Throttling.RateQuota`；`qwen-plus` 返回 200；`qwen-turbo-latest` 仍是 403 `AccessDenied`。`langchain_community/llms/tongyi.py` 的 `check_response` 把 DashScope 响应塞进 `requests.HTTPError`，响应对象没有 `request` 字段，最终变成 `KeyError: 'request'`。
- 界面：Gradio 弹出红色 Error，对话里只有用户那一句，没有最终答案。服务日志停在 `middleware.py` 第 451 行和第 475 行的 `handler(...)`，下面是模型调用。
- 这和 2026-06-19 的 403 是同一类包装。当时只把模型名改成了 `qwen-turbo`，错误包装还在。限流、无权限、参数错误都会走这条崩溃路径。
- 期望：模型或工具失败时停住，界面写出供应商的状态码和简短原因，不再当成一次成功的回答。

### P1 必要：城市注入失败后，地图工具仍会执行

- 是否必要：必要。这是上次 P0 留下的洞，这次被测试打红。
- 建议：和 P0 一起改，但不要先改框架。
- 证据：`tests/test_offline_baseline.py` 的 `test_map_tool_not_called_when_city_injection_fails` 失败。`override` 抛错后，`handler` 仍被调用。对应 `middleware.py` 第 422–425 行：记下警告后继续执行。
- 正常路径的注入测试是通过的。所以不是「现在每次都注不进城市」，而是「一旦注入再出错，工具会拿着原参数继续跑」。

### P1 必要：聊天框像多轮，模型每轮只看见当前一句

- 是否必要：必要，如果这个产品就是对话式行程助手。
- 建议：先写进 Agent 方案，再改。不要先上跨会话数据库。
- 证据：`stream_answer` 的参数有 `chat_history`（`ui.py` 第 172 行），函数体没有使用它。实际发给 Agent 的是 `{"messages": [HumanMessage(content=user_text)]}`（第 182–184 行）。用户说「改成两天」时，模型看不到上一轮。
- 城市缓存是进程级 `set`（`middleware.py` 第 36、157 行）。多个城市时 `next(iter(cities))` 不保证是用户说的顺序。这是后续问题，不是这次崩溃的原因。

### P1 必要：readme 仍推荐会 403 的模型名

- 是否必要：必要。按文档操作会配到无权限的模型。
- 建议：改文档即可，不必等功能改动。
- 证据：`readme.md` 第 45 行写默认 `qwen-turbo-latest`。代码是 `agent.py` 第 37 行的 `qwen-turbo`。本次探测里 `qwen-turbo-latest` 仍是 403。

### P1 必要：没有一份 Agent 方案，现有 Spec 还声明不改后端

- 是否必要：必要，作为下一次改 Agent 的前置。不必为了补文档去重写实现。
- 建议：后续做。用 `reference/agent-design-guide.md` 的七项写进 Spec，每一项写「选什么、为什么不选旁边那个」。
- 证据：仓库里只有 `docs/spec/frontend-modernization.md`。它的边界是 `agent.py` / `tools.py` / `middleware.py` / `config.py` 不动（第 20–23 行），全文没有「Agent 方案」。`plan-spec` 要求：会调模型、会调工具、会跨轮留信息的产品，没有这一节不得冻结。

## 建议（P2/P3）

- P2，后续做：`tools.py` 第 84–91 行把工具异常收成一段字符串返回。模型会把它当成正常观察结果。应改成失败关闭，而不是让模型凭这段话编行程。
- P2，后续做：`Config.MAX_TOOL_ROUNDS = 1`（`config.py` 第 14 行）。复杂行程第二轮工具会被预算拦住。先在方案里决定这是不是想要的停止条件。
- P2，后续做：`load_tools` 在导入时连接高德并预热天气（`tools.py` 第 182–206 行），`agent.py` 第 79 行在导入时就创建 Agent。缺密钥时能挡住模型，这是好的；但界面和测试都被绑在密钥和 MCP 上。
- P2，可稍后：官方 skill 建议打开 LangSmith。这是观测，不是这个 Demo 能回答问题的前提。密钥没进仓库（`.gitignore` 含 `.env`）。
- P2，文档状态：前端 Spec 的功能勾选仍是空的，`PLAN.md` 却写 M1 完成且 E2E 通过。勾选状态和「已通过」不是一回事。
- P3，可忽略：不要把项目迁到 Deep Agents，不要手写 LangGraph 把现有中间件重做一遍，不要加向量库，不要给查天气加人审。

## Agent 规划是否合适

对照 `reference/agent-design-guide.md` 和官方 `ecosystem-primer` / `langchain-fundamentals` / `langchain-middleware`。

| 方案项 | 代码里实际是什么 | 判断 |
|---|---|---|
| 控制方式 | `create_agent` 的工具循环，再加 1 轮工具上限 | 合适。单一职责，不必换层 |
| 谁做决定 | 宿主管城市、预算和未点名城市；供应商失败和注入失败仍会漏下去 | 方向对，失败时宿主没有把决定权收回来 |
| 工具 | 高德 MCP，本次加载 12 个；提示词只点了搜索、路线、天气 | 工具来源合适；结果校验不够 |
| 上下文与记忆 | 界面保留对话，模型只收当前一句 | 不合适。聊天产品至少要近期窗口 |
| 知识库与召回 | 没有文档库，事实来自当次工具 | 不需要向量库。工具失败不能改由模型凭记忆作答 |
| 运行边界 | 只读，无对外写入，无暂停续跑 | 合适。不必加人审 |
| 用户路径 | 能输入、能看到城市解析；失败时只有 Error | 失败路径没设计 |

结论：作为典型 Agent，**运行时的层选对了，规格没写**。改进项里必要的是失败关闭、把对话历史交给模型、补一份七项方案。不必要的是更换框架。

## 测试证据

离线，解释器 `F:\ENVS\pj-04-langchain-agent\python.exe`：

```text
python -m unittest tests.test_offline_baseline -v
Ran 9 tests in 12.831s
FAILED (failures=1)
```

- 通过 8 个：城市提取、坐标脱敏、点名城市后的注入、非地图工具不改写、无密钥不构造模型。
- 失败 1 个：`test_map_tool_not_called_when_city_injection_fails`。没有改产品代码去把它跑绿，因为计划规定本轮不改行为。这条红测试就是缺口的证据。

真实链路：

- `.env` 里 `DASHSCOPE_API_KEY`、`AMAP_MCP_URL` 都非空，也不是示例里的占位符。值没有写入本文。
- 高德 MCP 加载了 12 个 `maps_*` 工具。
- `agent.invoke("成都一日游...")` 在模型节点失败，`KeyError: 'request'`。工具参数里的 city 没有被观察到，因为还没走到工具。
- 页面 `http://127.0.0.1:7860/` 能打开。发送「成都今天天气」后，日志解析出成都，随后红色 Error。服务在验证后已停。

真实「工具被注入城市并返回行程」这一段标 **blocked**，不能标 done。

- 缺什么：不是缺密钥。`qwen-turbo` 当前 429 限流，而且任意供应商错误都会被包成未捕获的 `KeyError`。
- 已做的替代：离线注入成功测试通过；页面确认城市解析发生在崩溃之前。
- 何时能解开：`qwen-turbo` 不再返回 429 之后，再跑一条「成都今天天气」，确认工具参数里有 `city=成都`，并且界面有最终答案。限流期间不要改模型名来制造一次通过。

## 证据引用

- `agent.py:37` 模型名 `qwen-turbo`；`agent.py:51` `create_agent`；`agent.py:79` 导入时创建
- `middleware.py:422` 注入异常后仍 `return handler(req)`
- `ui.py:182` 只发送当前用户句
- `readme.md:45` 仍写 `qwen-turbo-latest`
- `docs/spec/frontend-modernization.md:20` 声明不改后端，且没有 Agent 方案
- `tests/test_offline_baseline.py` 9 项里 1 项失败
- 2026-10-19 页面发送「成都今天天气」：日志含「解析城市：成都」，随后 `KeyError: 'request'`
