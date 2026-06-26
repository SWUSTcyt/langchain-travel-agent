# [项目名称] 深度架构分析报告

> 由 /understand skill 自动生成
> 目标：为后续开发提供核心架构上下文与代码范式。

## 1. 全局概览 (Executive Summary)
- **核心技术栈**: [列出编程语言, 框架 (如 LangChain, FastAPI), 关键库]
- **项目类型**: [例如：单体应用 / 微服务 / CLI 工具 / Web 服务]
- **入口文件**: [指明程序的启动入口，如 main.py]

## 2. Agent 核心架构 (LLM & Brain)
> 重点关注 Agent 的初始化与模型配置。

- **模型初始化**:
  - **位置**: [指出代码文件及行号]
  - **参数**: [提取 temperature, model_name 等关键参数]
  - **代码范式**:
    ```python
    [请在此处粘贴初始化 LLM 或 Agent 的关键代码片段]
    ```

- **Prompt 管理**:
  - **System Prompt**: [Prompt 是硬编码在代码里，还是存储在外部文件？]
  - **模版机制**: [是否使用了 Jinja2 或 f-string？]

## 3. 工具与动作 (Tools & Actions)
> 重点关注 Function Calling 与工具注册机制。

- **工具注册方式**:
  - [分析项目是如何定义工具的？是使用装饰器，还是手动构建 Schema？]
  - **代码范式**:
    ```python
    [请粘贴一个典型的工具定义代码]
    ```

## 4. 外部连接与扩展 (MCP & APIs)
> 重点关注 MCP 及第三方 API 集成。

- **MCP 集成**:
  - **状态**: [是否检测到 MCP 相关依赖？]
  - **Client 配置**: [提取 MCP Client 连接代码]
  - **Server 列表**: [连接了哪些 MCP Server？]

## 5. 开发注意事项 (Best Practices)
- **代码风格**: [命名规范, 类型注解覆盖率]
- **潜在风险**: [指出开发中可能容易出错的地方]