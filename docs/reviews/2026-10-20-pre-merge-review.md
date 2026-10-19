# 合入前审查：换模型 + 上下文与注入失败关闭

- 日期：2026-10-20
- 范围：`main` 上未提交的全部改动（`agent.py`、`config.py`、`middleware.py`、`turn_context.py`、`ui.py`、`requirements.txt`、测试、示例、文档、skill 安装）
- 对照：`docs/issues/ISSUE-001-turn-context.md` 的验收标准；`verify-review` 中「合理用户会碰到的失败」一条
- 审查方式：只读。复现脚本用 `python -c` 直接调用中间件，未改工作树

## 结论：不可合入（not_verified）

## P0 检查：通过

- 密钥：工作区扫描 `sk-[A-Za-z0-9]{16,}` 与 MCP 地址 ID，只命中 `docs/ARCHITECTURE.md:726` 的占位符 `sk-xxxx...`。`.env` 未被跟踪。
- 外部写操作：本次没有 push / PR / merge。
- 注入失败不调用地图工具：`tests/test_offline_baseline.py` 通过。

## P1 检查：不通过

## 必须修改

1. 上一轮城市会覆盖本句明确说出的城市（回归）。
   - `middleware.py:57` 本句提取不到城市时保留旧城市；`middleware.py:409` 注入时读这份旧城市。
   - `CITY_REGEX`（`middleware.py:115`）只认约 34 个城市。用户说的城市不在表里（如丽江），就被当成「本句没提城市」。
   - 复现：先问「成都两天」，再问「丽江今天天气」，模型传 `city=丽江`，工具实际收到 `city=成都`。输出：`case1 user_asks=丽江 tool_city= 成都`。
   - 改动前每轮都会清空城市缓存，这种情况不会注入城市。
2. 行程记忆是进程级全局变量，所有浏览器会话共用。
   - `middleware.py:37-38`、`turn_context.py:18` 是模块级状态；`ui.py:431` 允许并发。
   - 新开标签页或刷新页面后，Gradio 历史为空，但城市和天数仍是别人或上一次对话留下的，只有点「清空对话」才会重置。
   - 证据：代码路径；上面的复现就是「无历史的新一问」。未在两个真实标签页里点测，这一点属于推断。
3. 序数词被当成行程天数。
   - `turn_context.py:13-15` 的正则会匹配「第一天」里的「一天」；`turn_context.py:29` 取第一个匹配。
   - 复现：「第一天去宽窄巷子，第二天去熊猫基地，一共三天」，记下的是 `行程天数：一天`，这个值会写进给模型的强制约束。
4. 以上三条都没有测试覆盖。14 项离线测试全过，但都没测到这三种情况。

## 建议（P2/P3）

- P2：`tools.py` 的 `_safe_run_coro` 把工具异常变成普通文字交给模型（已在 ISSUE-001 记为 follow-up）。
- P3：`enforce_city_on_tools` 短路返回的 `ToolMessage` 可加 `status="error"`。
- P3：`requirements.txt` 里的 `dashscope`、`langchain-community` 已无代码引用。
- P3：两份测试都改写 `sys.modules["agent"]`，测试之间有顺序依赖。

## 证据引用

- `middleware.py:57`、`middleware.py:409`、`middleware.py:115`
- `middleware.py:37-38`、`turn_context.py:18`、`ui.py:431`
- `turn_context.py:13-15`、`turn_context.py:29`
- 复现输出：`case1 user_asks=丽江 tool_city= 成都`；`case2b 行程天数：一天`
- 测试：`python -m unittest tests.test_offline_baseline tests.test_turn_context` → `Ran 14 tests ... OK`

## 发布

未执行。按 `verify-release`，审查有 P1 时不提交、不推送、不开 PR。修复走 `docs/issues/ISSUE-002-trip-memory-fixes.md`，用户确认后再改代码。

---

## 复审（ISSUE-002 修复后，同日）

## 结论：可合入

## P0 检查：通过

- 注入失败不调用工具：`test_map_tool_not_called_when_city_injection_fails` 通过。
- 密钥：复扫只命中占位符。

## P1 检查：通过

| 原问题 | 结论 | 证据 |
|---|---|---|
| 上一轮城市覆盖本句城市 | 通过 | `test_unlisted_city_named_now_is_not_overwritten_by_previous_city`；真实第三轮日志 `保留模型给出的 city=丽江` |
| 记忆跨会话共用 | 通过 | `middleware.py` 已无模块级行程变量；`test_new_session_does_not_inherit_other_session_city` |
| 「第一天」当成天数 | 通过 | `test_ordinal_day_is_not_trip_length`、`test_ordinal_only_sets_no_days` |
| 缺测试 | 通过 | 新增 9 项，改代码前失败，共 23 项 `OK`；示例 `examples ok` |

复审中另发现一处并已修复：工具本身抛错会被 `enforce_city_on_tools` 报成「城市注入失败」。证据：`test_tool_error_is_not_reported_as_city_injection_failure`。

## 建议（P2/P3，不阻塞）

- P2：没有在两个真实浏览器标签页里点测隔离，只有离线测试。
- P2：`tools.py` 工具异常仍变成普通文字交给模型。
- P3：`requirements.txt` 无引用依赖、`ToolMessage` 缺 `status="error"`、测试改写 `sys.modules`，均未处理。
