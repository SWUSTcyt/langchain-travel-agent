# E2E 验证指南（端到端冒烟）

> 当 `verify-test` skill 要求「真实端到端冒烟」时，参考本文档执行。
> 配合核心文档 §3.1 硬规则：凡声称「功能不回退」，必须至少跑通一次关键路径的真实端到端冒烟。

## 什么是 E2E 验证

E2E = End-to-End（端到端）。从用户操作的入口一路走到出口，验证**整条链路**都通。

与「构建冒烟」「服务起得来」的区别：

| 验证层级 | 验证什么 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| L1 构建冒烟 | import/编译不报错 | 代码语法正确 | 业务能跑通 |
| L1 服务起得来 | HTTP 200 | 服务器能启动 | 请求能正确处理 |
| **L2 E2E** | **真实请求→完整链路→预期结果** | **业务关键路径通** | 边界/并发/性能 |

## 何时需要 E2E

- P0 验收项声称「功能不回退」时（**必须**）
- 修了影响关键路径的 bug 后（验证修复生效）
- 升级了外部依赖版本后（验证 API 兼容）
- 何时**不用**：纯 UI 样式调整（不必走业务链路，但仍在产品入口按视口检查，见 `reference/ui-frontend-guide.md`）、文档修改、配置文件变更

## E2E 骨架流程

任何项目的 E2E 验证都遵循同一骨架：

```
1. 构建：加载项目入口，初始化必要组件
2. 执行：发送一个真实请求（用户会做的操作）
3. 检查：验证关键路径的中间节点和最终结果
4. 汇总：输出通过/失败 + 关键指标
5. 清理：删除临时验证文件
```

## 按项目类型的填写指引

### Web 后端（FastAPI / Flask / Django）

```python
from app import app
from fastapi.testclient import TestClient

client = TestClient(app)

# 发送真实请求
resp = client.post("/api/users", json={"name": "test"})

# 检查关键路径
assert resp.status_code == 200
assert resp.json()["name"] == "test"
# 可选：检查数据库
```

**可消费性验收项**（对外交付的服务额外检查）：

```python
# 1. 健康检查：不依赖任何业务模块（不调 flow / 不访问数据库）
resp = client.get("/health")
assert resp.status_code == 200

# 2. 错误码语义：传错字段应得 4xx（调用方的错），而非 500
resp = client.post("/v1/xxx", json={})  # 缺必填字段
assert 400 <= resp.status_code < 500

# 3. 契约校验：响应字段与 Spec 中声明的契约一致
# 4. 自动文档可访问（如 /docs），版本前缀存在（如 /v1/...）
```

### AI Agent（LangChain / MCP / 工具调用）

```python
from agent import agent
from langchain_core.messages import HumanMessage

# 发送需要工具调用的查询
for event in agent.stream(
    {"messages": [HumanMessage(content="用户会问的问题")]},
    config={"recursion_limit": 40},
):
    # 检查中间件注入是否生效（如城市约束）
    # 检查工具是否被调用且返回了结果
    # 检查最终答案是否有内容
    pass
```

### CLI 工具

```python
import subprocess

result = subprocess.run(
    ["python", "my_tool.py", "--input", "test_data"],
    capture_output=True, text=True, timeout=30
)

assert result.returncode == 0
assert "expected_output" in result.stdout
```

### 前端 SPA（React / Vue）

```python
# 使用 Playwright 或 Puppeteer
from playwright.sync_api import sync_playwright

# 入口是产品构建按部署方式启动后的地址，不是开发服务器或设计预览
PRODUCT_URL = "http://127.0.0.1:8000/"
VIEWPORTS = [(1920, 1080), (1366, 768), (390, 844), (390, 420)]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    try:
        for width, height in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": height})
            page.goto(PRODUCT_URL)
            # 等应用自己的就绪信号，不用 load / document.complete 代替
            # 下面的选择器只是示例，换成你应用的就绪信号（如账户入口可点、首屏数据已渲染）
            page.locator("button.account:not(:disabled)").wait_for()

            # 模拟用户操作
            page.get_by_role("textbox", name="搜索").fill("测试查询")
            page.get_by_role("button", name="提交").click()
            page.locator(".result").first.wait_for()

            # 无横向溢出
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            ), f"{width}x{height} 横向溢出"
            page.screenshot(path=f"e2e-{width}x{height}.png")
    finally:
        # 测试登录过的话，在这里用进程内保留的凭据调用退出/撤销接口
        browser.close()
```

视口矩阵、哪些能自动查、测试凭据核销见 `reference/ui-frontend-guide.md`。

### MCP / SSE 工具链

```python
import urllib.request

# 检查 MCP 端点可达
with urllib.request.urlopen("http://localhost:PORT/health", timeout=10) as r:
    assert r.status == 200

# 发送真实工具调用请求
# 检查工具返回了有效数据（不是空/错误）
```

## E2E 脚本规范

1. **自包含**：脚本能独立运行，不依赖外部状态
2. **有输出**：打印关键检查点的结果（OK/FAIL + 值），方便 agent 解读
3. **有退出码**：通过 `sys.exit(0)` / `sys.exit(1)` 表达通过/失败
4. **可清理**：运行后删除临时文件（脚本本身 + 临时日志）
5. **超时保护**：设合理超时，避免阻塞

## 常见错误

- **只测「能起来」** → HTTP 200 不等于业务通，必须走到关键路径的终点
- **mock 外部服务** → mock 通过不代表真实 API 兼容，E2E 就是要测真实链路
- **忘记清理** → 临时脚本留在项目里，下次 agent 可能误读
- **不做就标 done** → 跑不了（缺密钥/环境）只能标 blocked，不能标 done

## 参考

- 测试三层 skill：`skills/verify-test/SKILL.md`
