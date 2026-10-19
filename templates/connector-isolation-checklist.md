# 外部连接器隔离 & 凭据/诊断安全清单

> 用途：防两类真实事故——① 本机 `.env` 的连接器开关污染普通测试，让「本地证据卡」测试意外联网、终态从 `succeeded` 漂成 `partial`；② 诊断日志把执行资源整体序列化，意外暴露认证头/token。
> 何时用：任何接入付费/联网/外部 connector（检索、模型、MCP、第三方 API）的功能。

## A. 普通测试默认断网

- [ ] 普通 pytest/单元/功能测试启动时，**进程级** autouse fixture 覆盖所有可选 connector 为 false（不是在单个测试里关——进程级配置污染盖不住）。
- [ ] 测试默认读取的是**测试夹具的显式配置**，不是开发者本机 `.env`。
- [ ] 运行前打印一行「连接器状态摘要」（哪些开、哪些关），但**不打印任何凭据**。
- [ ] 验证：即使本机 `.env` 把连接器打开，普通测试也不联网、终态确定。

## B. 真实 E2E 显式隔离

- [ ] 真实外部调用只能通过显式 `RUN_REAL_*` 开关 + 独立测试标记打开，默认关闭。
- [ ] 有独立环境、明确超时、脱敏回执、零正文日志。
- [ ] 真实 E2E 报告不含 query、headers、问题正文、答案正文、客户文件名。

## C. 回执与诊断字段白名单

- [ ] 连接器回执只保留：`connector` / `status` / `count` / `latency` / `error_code` / 来源 host。
- [ ] **禁止整体序列化**：工具 schema、ExecutionResource / Action、MCP headers、URL query、原始 payload 永不整体输出。
- [ ] 诊断对象与「可安全打印」对象分离——运行时元数据（可能携带认证信息）不能当作工具 schema 那样随便打印。

## D. 凭据纪律

- [ ] token 用纯值或文件均可，但示例、回执、日志、commit、聊天里**永不出现真实值**。
- [ ] 提交前扫描 tracked/staged 内容是否含 secret（见发布安全清单）。
- [ ] 日志隐私门禁、报告隐私门禁本身要有自动测试（断言输出里不含 headers/auth/token）。

## E. 泄露后处置（一旦发生）

- [ ] 立即轮换 token。
- [ ] 同时记录两条事实：`已轮换` 与 `无法审计第三方是否已撤销旧值`——**不宣称绝对安全**。
- [ ] 排查仓库/应用日志是否留存旧值；新值冒烟通过后才算恢复。

---

## 通用 connector fixture（语言无关伪代码）

```python
# 进程级 autouse：普通测试一律断开所有可选 connector
@pytest.fixture(autouse=True, scope="session")
def _isolate_connectors(monkeypatch_session):
    for flag in ALL_OPTIONAL_CONNECTOR_FLAGS:   # 检索/模型/MCP/第三方
        monkeypatch_session.setenv(flag, "false")
    print(connector_status_summary())           # 只打印开/关，绝不打印凭据

# 真实 E2E：显式开关 + 独立标记，默认 skip
@pytest.mark.real_connector
def test_real_retrieval():
    if os.getenv("RUN_REAL_RETRIEVAL") != "1":
        pytest.skip("需显式 RUN_REAL_RETRIEVAL=1 才跑真实外部调用")
    receipt = call_connector(timeout=REAL_TIMEOUT)
    # 回执只留白名单字段
    assert set(receipt) <= {"connector", "status", "count", "latency", "error_code"}
```
