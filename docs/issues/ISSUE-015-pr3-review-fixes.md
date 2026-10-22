# Issue: PR #3 审查问题修复

> 状态：已确认。除截图外均已完成。

## 用户原话（2026-10-23）

你按照 review 的结果继续进行修改以及测试，直到能通过验收标准。截图我会去截取的，截图放置位置需要你告诉我。

## 来源

PR #3 审查结论「不可合入」，两条 P1：

1. 高德连不上时，页面补查不会停，12 次 × 每次最多 10 秒，最多卡 120 秒在「正在查」。
2. README 说 JS key「见下面的环境配置」，但环境配置里没有 `AMAP_JS_KEY`；功能列表还写着「并行调用路线规划」，和现在只搜地点、查天气矛盾；缺界面截图。

另有一条 P2 顺手修：PR 里 14 个文件被存成 CRLF，真实改动被换行符变化盖住。原因是用 WSL 的 git 暂存，没走 Windows 的 `autocrlf`。

## 要改

- 页面补查（补搜地点、查详情）遇到第一次失败就停掉剩下的补查。失败包括：抛异常、返回空、返回「工具执行失败」开头的文字。已经查到的坐标照常用。
- README 环境配置补上 `AMAP_JS_KEY`、`AMAP_JS_SECURITY_CODE`；功能列表改成现在的行为；在「界面」一节放截图引用 `docs/images/ui-preview.png`，图由用户截取放入。
- 用 Windows git 重新暂存，仓库里统一存 LF。

## 不改

- 正常情况下的补查顺序、12 次上限、按天轮流。
- 模型一轮只搜一次、查一次天气的限制。
- 页面布局、地图画法。
- `on_submit` 里 `finally` 中的 `yield`（P2，留后续）。
- `prototypes/` 和 `templates/` 不移出 PR，在 PR 说明里写明来由（`PLAN.md` 以 `prototypes/travel-ui-v0.11.html` 为界面基准）。

## 验收标准

### P0

- [x] 高德不通时，一次回答的页面补查最多发出 1 次。证据：`tests/test_itinerary.py` 的 `test_gaode_down_stops_host_lookups_after_first_failure`（失败文字、抛异常、空结果三种都只调用 1 次）；模拟 3 天 12 个地点，补查从 12 次降到 1 次。
- [x] 某次补查失败前已经拿到的坐标仍然画上。证据：`test_coords_found_before_failure_are_kept`，B1 坐标保留，B2 失败后不再补搜景山公园。
- [x] 原有 75 项单测仍全部通过。证据：`unittest discover` 77 项 OK；三个 examples 退出码 0。

### P1

- [x] README 环境配置写明 `AMAP_JS_KEY` 和 `AMAP_JS_SECURITY_CODE`，不再出现「并行调用」「路线规划」作为现有功能。证据：`readme.md` 环境配置一节；全文搜索「并行」「路线规划」「searchPOI」无结果。
- [ ] README 截图引用的路径与告诉用户的放置位置一致：`docs/images/ui-preview.png`。README 已引用，等用户放入图片后提交。
- [x] PR 与 `origin/main` 比较时，不再有只因换行符变化的文件。证据：暂存区 68 个文件逐个检查无 CRLF；ISSUE-001、ISSUE-002 不再出现在差异里。
- [x] 新增与改动模块的单测覆盖率 ≥ 80%。证据：coverage 报告 `itinerary.py` 83%，`itinerary_view.py` 87%。

### P2

- [ ] ISSUE-008、ISSUE-012 的真实运行日志（pending_external）。
- [ ] `on_submit` 的 `finally` 里不再 `yield`。
