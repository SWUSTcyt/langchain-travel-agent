# Travel Agent Demo (LangChain 1.0 + MCP + Qwen)

一个基于 **LangChain 1.0**、**阿里通义 Qwen** 和 **MCP(amap-maps)** 的旅游规划 Agent Demo。打开就是一页：左边聊天，右边地图。

## 界面

左边是聊天记录，提问框在聊天框下面。还没提问时，框里有「想去哪里，待几天？」和三张示例；问过之后，示例留在同一个聊天框的最下面，点一下只填进输入框。

右边是高德地图。点「第 1 天 / 第 2 天」只看这一天：有两个以上地点就连线，只有一个地点就只标点。序号是当天的颜色，点一下才看到地点全名。

![旅游助手界面：左边聊天，右边按天标点连线的地图](docs/images/ui-preview.png)

本地运行 `python main.py` 后打开 http://127.0.0.1:7862/ 。地图需要单独的高德 Web 端 JS key，见下面的环境配置。

支持：

- 每次提问，模型只调用一轮高德工具：搜一次地点（`maps_text_search`）、查一次天气（`maps_weather`）
- 地点坐标由页面补查（`maps_search_detail`），最多 12 次，按天轮流；高德连不上时第一次失败就停
- 中间件级别的城市约束、工具预算控制、输出城市安全检查
- AI 思考过程（通过 `enable_thinking=True` 启用 Qwen 推理），放在页面下方的「开发者」折叠里
- **Claude Skills 集成**（项目架构分析和功能开发支持）

## 功能特性

- ✅ 使用 `langchain-mcp-adapters` 连接自建 MCP Server（高德地图）
- ✅ 自动提取用户输入中的城市，并约束所有工具调用 city/adcode
- ✅ 工具调用轮次预算控制：同一轮搜索、天气各最多一次；`maps_geo`、`maps_direction_*` 等工具不交给模型
- ✅ 响应后检查输出是否出现"未指定城市"，自动提示修正
- ✅ 行程卡片：每次行程回答是一张卡，点哪张卡、哪一天，地图就画哪一天
- ✅ 「开发者」折叠：
  - AI 思考过程（意图理解、工具选择、信息整合）
  - 摘要日志（工具调用、模型调用、城市解析）
  - 原始事件 JSON（勾选开发者模式后显示）

## 安装

```bash
git clone https://github.com/<yourname>/travel-agent.git
cd travel-agent

# 建议使用虚拟环境（略）

pip install -r requirements.txt
```

## 环境配置（Qwen Key 与高德 MCP）

本项目通过以下环境变量进行配置（可参考仓库中的 `.env.example`）：

- `DASHSCOPE_API_KEY`：
  - 用于访问 **通义千问 Qwen 模型**（通过 DashScope 平台）
  - 获取方式：登录阿里云通义千问 / DashScope 控制台，创建 API Key，将值填入 `.env` 中的 `DASHSCOPE_API_KEY`
  - 当前模型：`qwen3.8-flash`（兼容接口）。`qwen-turbo` 已下线，不要再改回 `qwen-turbo-latest`

- `AMAP_MCP_URL`：
  - 用于连接 **高德地图 MCP Server（amap-maps）** 的 SSE 服务地址
  - 获取方式（示例流程）：
    1. 打开 ModelScope（魔搭社区），进入 **MCP 广场**
    2. 搜索「高德」或「amap」相关 MCP，按照页面说明填写对应的高德api，获取url

      ![高德 MCP 配置示意图](src/amap-mcp-config.png)

    3. 在文档中找到提供的 **SSE 访问地址**（通常是以 `http://.../sse` 或 `https://.../sse` 结尾的 URL）
    4. 将该地址填入 `.env` 中的 `AMAP_MCP_URL`

- `AMAP_JS_KEY`、`AMAP_JS_SECURITY_CODE`：
  - 用于右边的 **高德地图**（Web 端 JS API），和上面的 MCP 地址不是同一个 key
  - 获取方式：登录 [高德开放平台控制台](https://console.amap.com/dev/key/app)，在应用管理里添加 Key，服务平台选「Web端(JS API)」；Key 填 `AMAP_JS_KEY`，旁边的安全密钥填 `AMAP_JS_SECURITY_CODE`（[步骤说明](https://lbs.amap.com/api/javascript-api-v2/prerequisites)）
  - 不填时页面只显示文字，地图区写「地图暂不可用」
  - 安全密钥会写进页面，只适合本地演示；公开部署请按高德文档改成代理转发

配置完成后，确保本地 `.env` 文件与上述环境变量一致，再运行：

```bash
python main.py
```

## 🆕 新增功能说明

### AI 深度思考过程展示

从本版本开始，系统支持展示 AI 的完整推理过程：

#### 工作原理

1. **启用思考模式**：在 `agent.py` 中配置 `enable_thinking=True`
2. **收集推理链**：`ui.py` 中的 `stream_answer()` 函数从 `AIMessage.additional_kwargs['reasoning_content']` 逐块累积推理内容
3. **前端展示**：页面下方「开发者」折叠里显示思考过程，用户可选择查看

#### 使用场景

- **用户透明度**：让用户了解 AI 的决策逻辑
- **信任建立**：完整的推理过程增强用户信任度
- **调试优化**：开发者可通过 reasoning 识别 AI 的决策偏差
- **教育价值**：用户可学习系统性的规划思路

#### 界面效果

展开页面下方的「开发者」，可以看到完整的推理链：

```
用户问"规划成都2天美食路线"，我需要明确理解需求：
- 目标城市：成都
- 时间限制：2天
- 兴趣点：美食

决定调用以下工具获取信息：
1. maps_text_search（获取美食地点）
2. maps_weather（查询天气）

基于这些信息，我将生成最终答案...
```

### Claude Skills 集成

项目包含两个 Claude Skills（位于 `.claude/skills/`）：

#### 1. **understand** Skill
- **功能**：深度分析项目架构、Agent 配置及 MCP 集成
- **输出**：生成 `docs/ARCHITECTURE.md` 中文架构文档
- **使用**：在 Claude Code 中运行 `/understand`
- **文件路径**：`.claude/skills/understand/SKILL.md`

#### 2. **feature** Skill
- **功能**：基于架构规范安全地实现新功能或优化现有代码
- **使用**：在 Claude Code 中运行 `/feature`
- **文件路径**：`.claude/skills/feature/SKILL.md`

这些 Skills 可帮助开发者快速理解项目结构，并以最佳实践方式进行开发。

## 项目结构

```
├── main.py                      # 应用启动入口
├── config.py                    # 配置管理与常量定义
├── agent.py                     # Agent 创建与配置
├── tools.py                     # MCP 工具加载与异步包装
├── middleware.py                # LangChain 中间件集合
├── ui.py                        # Gradio 页面：左边聊天，右边地图
├── itinerary.py                 # 从回答里读出行程，并补地点坐标
├── itinerary_view.py            # 行程卡片 HTML 与地图数据
├── assets/
│   ├── custom.css               # 页面样式
│   └── trip-map.js              # 高德地图绘制（按天标点、连线）
├── requirements.txt             # 依赖清单
├── .env                         # 环境变量配置（未提交）
├── .env.example                 # 环境变量模板
├── readme.md                    # 本文件
├── docs/
│   ├── ARCHITECTURE.md          # 详细架构文档
│   └── images/ui-preview.png    # README 界面截图
├── .claude/
│   └── skills/                  # Claude Skills 集合
│       ├── understand/          # 架构分析 Skill
│       └── feature/             # 功能开发 Skill
└── src/
    └── amap-mcp-config.png      # 配置说明图
```

## 技术栈版本

| 组件 | 版本 | 说明 |
|-----|------|------|
| LangChain | >=1.0.0 | Agent 框架核心 |
| langchain-community | >=0.3.0 | 通义千问模型集成 |
| langchain-mcp-adapters | >=0.0.8 | MCP 协议适配器 |
| dashscope | >=1.14.0 | 阿里云通义千问 SDK |
| Gradio | >=4.1.0 | Web UI 框架 |

## 贡献指南

如需改进该项目，建议：

1. 运行 `/understand` Skill 了解项目架构
2. 参考 `docs/ARCHITECTURE.md` 中的设计模式
3. 使用 `/feature` Skill 实现新功能
4. 提交 PR 前运行测试验证

## 相关文档

- **完整架构文档**：查看 `docs/ARCHITECTURE.md`（包含系统设计、中间件详解、优化方向等）
- **Claude Skills**：见 `.claude/skills/` 目录说明

## 许可证

MIT License
