# Spec 索引

> 本项目全部 Spec 的目录。`status` 的真源是各 Spec 的 front matter，本表是镜像。

| spec_id | 标题 | status | version | parent | 路径 |
|---|---|---|---|---|---|
| SPEC-001 | 旅游助手 | Frozen | 1 | - | `docs/spec/PROJECT.md` |
| SPEC-002 | 旅行对话 Agent | Superseded | 1 | SPEC-001 | `docs/spec/travel-agent.md`（由 SPEC-005 取代） |
| SPEC-003 | 旅游助手前端现代化 | Frozen | 1 | SPEC-001 | `docs/spec/frontend-modernization.md` |
| SPEC-004 | 行程加地图界面 | Frozen | 1 | SPEC-001 | `docs/spec/trip-map-ui.md` |
| SPEC-005 | 旅行对话 Agent（修订：结构化行程） | Frozen | 2 | SPEC-001 | `docs/spec/travel-agent-v2.md` |
| SPEC-006 | 结果页作为唯一页面 | Frozen | 1 | SPEC-004 | `docs/spec/trip-map-single-page.md` |
| SPEC-007 | 左列对话与可切换的行程卡 | Frozen | 1 | SPEC-006 | `docs/spec/trip-chat-cards.md` |

## 状态说明

| 状态 | 允许的动作 | 谁置位 |
|---|---|---|
| Draft | 自由编辑；不能作为实施或验收完成的依据 | plan-spec 新建时 |
| Frozen | 可以拆 Issue、进入实施 | plan-spec，用户确认后 |
| Verified | P0/P1 验收项都有通过证据 | verify-review，全部通过时回写 |
| Superseded | 只读，必须指向后继 Spec | plan-spec，新建 revision 时 |

SPEC-003 于 2026-10-20 只补了编号、parent 和状态。正文范围没改。它的界面改动早已实现，但这次没有重跑它的验收，所以不标 Verified。
