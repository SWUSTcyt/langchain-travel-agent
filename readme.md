# Travel Agent Demo (LangChain 1.0 + MCP + Qwen)

一个基于 **LangChain 1.0**、**阿里通义 Qwen** 和 **MCP(amap-maps)** 的旅游规划 Agent Demo，支持：

- 并行调用高德地图相关工具（搜索 POI、路线规划、天气查询）
- 中间件级别的城市约束、工具预算控制、输出城市安全检查
- Gradio 前端，支持流式对话与调试日志查看（开发者模式）

## 功能特性

- ✅ 使用 `langchain-mcp-adapters` 连接自建 MCP Server（高德地图）
- ✅ 自动提取用户输入中的城市，并约束所有工具调用 city/adcode
- ✅ 工具调用轮次预算控制，防止无限工具循环
- ✅ 响应后检查输出是否出现“未指定城市”，自动提示修正
- ✅ Gradio 前端支持：
  - 聊天窗口
  - 摘要日志（工具调用、模型调用、城市解析）
  - 原始事件 JSON（开发者模式）

## 安装

```bash
git clone https://github.com/<yourname>/travel-agent.git
cd travel-agent

# 建议使用虚拟环境（略）

pip install -r requirements.txt


## 环境配置（Qwen Key 与高德 MCP）

本项目通过以下两个环境变量进行配置（可参考仓库中的 `.env.example`）：

- `DASHSCOPE_API_KEY`：  
  - 用于访问 **通义千问 Qwen 模型**（通过 DashScope 平台）  
  - 获取方式：登录阿里云通义千问 / DashScope 控制台，创建 API Key，将值填入 `.env` 中的 `DASHSCOPE_API_KEY`
  - 推荐模型：`qwen-turbo-latest`（默认）、或按需改为 `qwen-plus`

- `AMAP_MCP_URL`：  
  - 用于连接 **高德地图 MCP Server（amap-maps）** 的 SSE 服务地址  
  - 获取方式（示例流程）：  
    1. 打开 ModelScope（魔搭社区），进入 **MCP 广场**  
    2. 搜索「高德」或「amap」相关 MCP，按照页面说明填写对应的高德api，获取url

      ![高德 MCP 配置示意图](src/amap-mcp-config.png)
      
    3. 在文档中找到提供的 **SSE 访问地址**（通常是以 `http://.../sse` 或 `https://.../sse` 结尾的 URL）  
    4. 将该地址填入 `.env` 中的 `AMAP_MCP_URL`

配置完成后，确保本地 `.env` 文件与上述环境变量一致，再运行：

```bash
python main.py
```


