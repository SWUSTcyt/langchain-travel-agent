# Session Summary: [日期]

<!--
标准交接结构。事实/决定/推断/外部待办分开写，防止把一次观察当成产品事实、把外部 pending 当成已完成。
至少要有 1 条 facts 和 1 条 next_action；缺则本摘要标 incomplete_observation。
inference / external_blocker 绝不写进 verified/complete/done。
-->

```yaml
session_id:
date:
issue_id:
spec_id:
scope_changed: false
facts: []                 # 可复核的原始事实（日志/测试/文件:行号/用户明确消息）
decisions: []             # 负责人/需求方明确拍板的范围或策略
inferences: []            # 基于事实的推断，不是事实
tests:
  command: []
  result: ""
  baseline_sample_size: null
external_blockers: []     # 需供应商/律师/部署/用户继续提供的证据
secrets_or_customer_content_read: false
files_changed: []
commit_or_pr: null        # PR 号/URL/SHA，未做则 null，不写成计划
next_owner:
next_action:
```

## 使用的 Skill

-

## 错误与解决方案

| 错误(fact) | 解决方案 | 是否推断 |
|---|---|---|
| | | |

## 模型降质指标

- **Review 轮次**:
- **同一问题反复次数**:
- **是否摸鱼**: 是 / 否

## 备注

<!-- 若 facts 为空或 next_action 为空：本摘要标 incomplete_observation，说明缺什么 -->
