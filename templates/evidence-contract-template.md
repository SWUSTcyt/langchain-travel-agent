# 证据合同（Evidence Contract）

> 用途：为一条「要证明的结论」显式声明——它算数的唯一真源、必备字段、取消资格条件、
> 证据不足时的失败终态。防止「模型调用成功 / 候选链接存在 / 已核验 / 业务质量通过」被混为一谈。
>
> 何时挂：每个 P0/P1 Issue 至少挂一份；一个 Issue 有多条独立结论就挂多份。
> 缺 `source_of_truth` / `required_fields` / `fail_closed_state` 的 P0/P1 Issue **不得进入除 Planned 外的任何完成态**。

## 字段说明

| 字段 | 含义 | 硬约束 |
|---|---|---|
| `claim` | 要证明的那一句事实 | 必填，一句话可证伪 |
| `evidence_level` | E0 自动可复现 / E1 人工或负责人确认 / E2 外部待核验 / E3 推断 | 必填；E2/E3 不得当作「通过」 |
| `source_of_truth` | 结论算数的唯一依据：代码/数据库终态/外部回执/人工签字 | 必填；**「模型说已核验」不可作 source_of_truth** |
| `required_fields` | 判定通过必须齐备的字段（如来源版本、逐字引文、锚点、样本量） | 必填，缺任一即不通过 |
| `disqualifiers` | 出现即取消资格的情况（转载材料、无原文、版本不符、分母不合格） | 命中即失败关闭 |
| `fail_closed_state` | 证据不足时的可见终态：`blocked`/`unverified`/`no_match`/`pending_external` | 必填；不得静默变成成功 |
| `model_call_allowed_when` | 允许调用模型/外部服务产生确定结论的前置条件（宿主门禁通过后） | 涉及模型/外部服务时必填 |
| `human_owner` | 谁对这条结论负责（角色或责任人） | 必填 |
| `expires_or_review_due_at` | 有效期或复核到期（法源版本、供应商条款等会过期的） | 会过期的必填，否则 null |

## 模板

```yaml
evidence_contract:
  claim: ""
  evidence_level: ""          # E0 | E1 | E2 | E3
  source_of_truth: ""         # 代码 / 数据库 / 外部回执 / 人工确认
  required_fields: []
  disqualifiers: []
  fail_closed_state: ""       # blocked | unverified | no_match | pending_external
  model_call_allowed_when: ""
  human_owner: ""
  expires_or_review_due_at: null
```

---

## 示例 1：权威来源逐字核验类（RAG 引用 / 标准条款 / 版本化文档）

> 通用模式：**权威来源 + 版本 + 逐字回读 + 缺失即失败关闭**。适用于 RAG 引用核验、
> RFC/ISO/国标条款、药品说明书、监管合规文件、法规条文等任何带版本的权威来源——
> 换个领域只改 `claim` 里的来源类型，字段结构不变。

```yaml
evidence_contract:
  claim: "指定权威文档某章节/条目的正文与限定版本逐字一致"
  evidence_level: "E0"
  source_of_truth: "数据库中的来源快照 + digest 逐字回读校验（非模型自述）"
  required_fields: ["来源名称", "版本/基准日", "章节/条目号", "逐字引文", "snapshot digest"]
  disqualifiers: ["仅转载材料无原文", "版本/基准日不符", "章节/条目不存在", "来源不可访问"]
  fail_closed_state: "no_match"    # 条目不存在或版本缺失时返回 NO_MATCH，模型调用为 0
  model_call_allowed_when: "宿主已完成来源+版本+条目精确匹配且原文可逐字回读之后"
  human_owner: "检索/引用模块负责人"
  expires_or_review_due_at: "2026-12-31"   # 权威来源版本会更新，需定期复核
```

## 示例 2：外部 connector 类（E0/E2，候选不升级）

```yaml
evidence_contract:
  claim: "外部检索服务能返回候选，可作二级参考"
  evidence_level: "E0"          # 「能返回候选」是 E0；「候选=权威证据」不成立
  source_of_truth: "connector 结构化回执（connector/status/count/latency/error_code）"
  required_fields: ["status", "count", "error_code"]
  disqualifiers: ["把候选/转载/搜索摘要自动升级为 verified", "回执含空/超时/错误 schema 却记成功"]
  fail_closed_state: "unverified"   # 候选停留在 REF_ONLY，不进权威证据卡
  model_call_allowed_when: "候选仅作参考，不构成产生确定性结论的依据"
  human_owner: "集成负责人"
  expires_or_review_due_at: null
```

## 示例 3：模型质量类（E0，未完成不降门）

```yaml
evidence_contract:
  claim: "模型对该类输入的结构化输出满足质量基线"
  evidence_level: "E0"
  source_of_truth: "holdout 评测报告（样本量+基线+通过率+失败项）"
  required_fields: ["样本量", "基线", "通过率", "失败项清单", "数据版本 hash"]
  disqualifiers: ["用单条合成请求宣称质量通过", "调参读取了 blind set 答案", "HTTP 200/JSON 可解析即判过"]
  fail_closed_state: "blocked"
  model_call_allowed_when: "宿主 preflight 通过；质量结论另由 holdout 报告决定，不由传输成功决定"
  human_owner: "评测负责人"
  expires_or_review_due_at: null
```

## 示例 4：失败/blocked（缺前置，禁止标 done）

```yaml
evidence_contract:
  claim: "端到端主链路功能不回退"
  evidence_level: "E2"          # 缺真实凭据，尚不能提供 E0 证据
  source_of_truth: "真实端到端冒烟回执（缺）"
  required_fields: ["真实模型/外部服务/工具链回执"]
  disqualifiers: ["用构建通过/服务能起来冒充功能验证"]
  fail_closed_state: "blocked"
  model_call_allowed_when: "N/A（前置未满足）"
  human_owner: "本 Issue owner"
  expires_or_review_due_at: null
# 说明：① 缺什么=真实凭据/环境；② 替代验证=已跑单测+契约测试；③ 解除条件=拿到凭据后补跑冒烟
```
