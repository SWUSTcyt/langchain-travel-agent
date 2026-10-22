# Issue: 左列对话，行程卡对应地图

> 状态：已确认并实现。P0、P1 离线通过。P2 已在浏览器核对左列输入和两张卡的切换。

spec: SPEC-007（Frozen）
accepts: 左边连续对话；行程卡选中后地图画这一次；点第几天只作用于这张卡。

## 任务描述

左边整列显示问过的话和每次回答。输入框和清空放在左列底部，不再横跨整页。右边仍是地图。

- 有几天行程的回答渲染成卡片，带稳定编号 `t1`、`t2` 这种。天数按钮和站点编号都带上这个编号。
- 选中卡片时，地图用这张卡里已经存好的坐标重画，默认第 1 天。再点这张卡的某一天，只改这一天的线和镜头。
- 只问天气的回答没有天数按钮。点它不提供另一份地图。
- 新问题进行中，上一张卡的文字还在，地图先回到默认空图。
- 这句没有新行程时，地图回到上一张有点的卡，并标出那张卡。
- 点选时不拆掉地图对象再新建。

涉及：`itinerary_view.py` 的对话 HTML 与编号，`ui.py` 把输入放进左列并记住每一张卡，`assets/trip-map.js` 按卡片取坐标重画，`assets/custom.css` 标出选中的卡。测试在 `tests/test_itinerary_view.py`。

## 规格未写、合理用户会踩

| 输入或情况 | 合理用户期望 | 落到哪条测试 |
|---|---|---|
| 先成都三天，再杭州一天 | 两张卡都在，第 2 天不会画到另一次上 | 两张卡的天数和站点编号不同 |
| 第二句只问天气 | 天气写在对话里，地图仍是上一张有点的行程 | 文字回答没有天数按钮；选中编号仍是上一张卡 |
| 新问题还在查 | 上一张卡的字还在，地图不是上一座城市的点 | 进行中的对话含上一张卡和「正在查」 |
| 点某一天 | 只高亮这一张卡里的这一天 | 脚本按 `.turn-card` 取这一张的坐标，这一路不拆地图 |

## 输入 / 输出

- **输入：** 多轮问答。有的轮次有几天行程，有的只是一段话
- **输出：** 左列按时间留下这些问答。地图只画当前选中的那张行程卡里的那一天

## 依赖条件

- [x] 结果页和按天切换地图已经在。本任务给每次行程加上编号，并把左边改成对话。

| dependency_type | blocking_level | evidence_required | substitute_allowed | owner | rollback_if_missing |
|---|---|---|---|---|---|
| code | hard | `tests/test_itinerary_view.py` 新断言通过 | 否 | 实现者 | 不合入 |
| deployment | soft | 浏览器里左列输入不横跨地图，两张卡的编号不同 | 是，离线先过；浏览器未看则该条 pending_external | 实现者 | 不把离线通过写成页面已核对 |

## 证据合同

```yaml
evidence_contract:
  claim: "两张行程卡的第几天彼此独立，地图使用该卡已存的坐标"
  evidence_level: "E0"
  source_of_truth: "tests/test_itinerary_view.py 里两张卡的编号、天气回答、以及脚本按卡片重画"
  required_fields: ["卡片编号", "第几天", "站点编号", "是否行程卡"]
  disqualifiers: ["只改提示词", "两张卡共用 day-0"]
  fail_closed_state: "unverified"
  model_call_allowed_when: "离线断言通过之后，才在浏览器看左列和卡片；没看则该条 pending_external"
  human_owner: "实现者"
  expires_or_review_due_at: null
```

## 验收标准

### P0（阻塞必修，不满足不合入）

- [x] 两张行程卡同时出现时，天数按钮和站点编号都带各自的卡片编号，不共用 `day-0`。证据：`test_two_cards_do_not_share_day_ids`。
- [x] 只问天气的回答没有天数按钮。证据：`test_weather_reply_is_not_a_day_card`。
- [x] 新问题还在查时，上一张卡的内容仍在对话里。证据：`test_pending_keeps_the_previous_card`。
- [x] 点某一天时，脚本在该张 `.turn-card` 里取坐标并重画，这一路不调用拆掉地图。证据：`test_day_click_uses_the_card_and_does_not_destroy_the_map`。浏览器里点杭州卡后再点成都第 1 天，地图画布还是同一个，中心分别到 120.121, 30.223 和 104.058, 30.665。

### P1（本次必修）

- [x] 输入框排在左列里，而不是排在地图栏之后的整页横条。证据：`test_ask_row_sits_in_the_left_column`。浏览器 1366 宽时输入右缘约 744px，地图从约 777px 开始。
- [x] 新行程卡默认标成选中。没有新行程时，选中仍可以是上一张行程卡。证据：两张卡的测试里 `t2` 为选中；天气测试里选中仍是 `t1`。

### P2（可后续 PR，记为 follow-up）

- [x] 浏览器里看左列输入是否只占左边，以及两张卡的编号。见上面。这两张卡是放进页面的坐标，不是再跑一遍真实模型。

### P3（可忽略，记录不追踪）

- [ ] 无

## 参考

- `docs/spec/trip-chat-cards.md`
- `assets/trip-map.js` 的 `selectDay`
