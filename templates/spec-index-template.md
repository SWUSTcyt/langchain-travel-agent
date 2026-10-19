# Spec 索引

> 本项目全部 Spec 的目录。放在 `docs/spec/INDEX.md`。
> 只有一份 Spec 时不必建本文件，出现第二份时再补上（把已有那份一并登记）。
> `PLAN.md` 只挂当前活跃的 Spec 链接，全量目录看这里。
> `status` 的真源是各 Spec 的 front matter，本表是镜像——改状态时两处一起改。
> 新建 Spec 取号：本表现有最大号 +1，只增不复用。

| spec_id | 标题 | status | version | parent | 路径 |
|---|---|---|---|---|---|
| SPEC-001 | | Frozen | 1 | - | `docs/spec/PROJECT.md` |
| SPEC-002 | | Draft | 1 | SPEC-001 | `docs/spec/xxx.md` |

## 状态说明

| 状态 | 允许的动作 | 谁置位 |
|---|---|---|
| Draft | 自由编辑；不能作为实施或验收完成的依据 | plan-spec 新建时 |
| Frozen | 可以拆 Issue、进入实施 | plan-spec，用户确认后 |
| Verified | P0/P1 验收项都有通过证据 | verify-review，全部通过时回写 |
| Superseded | 只读，必须指向后继 Spec | plan-spec，新建 revision 时 |
