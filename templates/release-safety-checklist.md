# 发布安全清单（Release Safety Checklist）

> 配合 `skills/verify-release/SKILL.md` 使用。逐项打勾；执行完成前不把计划写成事实。

## 现状

| 项 | 值 |
|---|---|
| 远端仓库 | |
| 可见性（private/public） | |
| 默认分支 | |
| 当前分支 | |
| 发布分支（从默认分支创建） | |
| 协作场景（单人 / 协作） | |

## 拟纳入 allowlist

- [ ] 已逐路径列出要提交的文件（未用 `git add .` / `-A`）
- [ ] 客户数据 / 运行产物 / 上传文件目录已排除
- [ ] 密钥文件（`.env`、secret、token）已排除

拟纳入路径：

```
（逐行列出）
```

## 提交前扫描

| 检查 | 命令/动作 | 结果 |
|---|---|---|
| secret / token / 认证头 | staged 内容扫描 | |
| PII / 客户文件名 | staged 路径+内容扫描 | |
| 行尾/冲突标记 | `git diff --check` | |
| 测试 | 相关测试脚本 | |
| Lint / 静态检查 | | |

## PR 与合并

| 项 | 值 |
|---|---|
| PR 号 / URL | |
| base SHA | |
| head SHA | |
| required checks | 通过 / 未通过 / 无 |
| required review | 通过 / 未通过 / 无 |
| 合并方式 | |
| merge commit / base SHA（合并后） | |
| 合并时间 | |

## 七种停止点自检（每种都应有明确动作，不误报完成）

- [ ] **在 main 工作树** → 不直接提交，先建 feature branch。
- [ ] **有未追踪的客户文件** → 从 allowlist 排除，不入 staged。
- [ ] **远端为 public（预期 private）** → 停止上报，不推送。
- [ ] **secret scan 命中** → 停止修复，不带病提交；若已进历史则重写历史 + 轮换。
- [ ] **测试失败** → 不合并，回到实现修复。
- [ ] **PR 需要他人 review（协作仓库）** → 不自合，交 required review / 负责人。
- [ ] **合并成功** → 回读 PR 状态与 base SHA，生成发布回执；注明「合并 ≠ 上线」。

## 破坏性操作确认

- [ ] force-push / 重写历史 / 删分支 / 删含未跟踪文件的 worktree：已复述影响并取得用户显式确认。

## 人读导出（仅人，Agent 跳过）

- [ ] 对照本轮 CHANGELOG，是否要把 skills 增量整理进 `docs/AI 编程方法论 — 人读版.md`。**不是本 skill 完成条件**；Agent 不要打开、不要更新该文件。
