# 项目: 旅游助手 | 状态: ISSUE-015 PR #3 审查问题修复

> 当前运行状态唯一真源。需求全貌见 `docs/spec/INDEX.md`。

## 目标

正式界面：详细文字行程为主，电子地图为辅。

## 活跃 Spec

| Spec ID | 路径 |
|---|---|
| SPEC-004（Frozen） | `docs/spec/trip-map-ui.md` |
| SPEC-005（Frozen，已取代 SPEC-002） | `docs/spec/travel-agent-v2.md` |
| SPEC-006（Frozen） | `docs/spec/trip-map-single-page.md` |
| SPEC-007（Frozen） | `docs/spec/trip-chat-cards.md` |

## 活跃 Issue

| Issue | P0 摘要 | 依赖 |
|---|---|---|
| ISSUE-003 | 已完成：工具失败可见，26 项 OK | 无 |
| ISSUE-004 | 离线完成。真实回答已能解析出三天行程 | 无 |
| ISSUE-005 | 文字和地图已通。JS key 已配置 | 无 |
| ISSUE-006 | 提问页、按天分色、单点落到地图。页面核对已做 | 无 |
| ISSUE-007 | 补记：模型只打搜索和天气。代码先于 Issue | 无 |
| ISSUE-008 | 已确认：同一轮搜索和天气各最多 1 次。离线 58 项 OK。真实日志待补 | 无 |
| ISSUE-009 | 已确认：只留结果页；点上只留序号。离线与浏览器已核对 | 无 |
| ISSUE-010 | 已确认并实现：左列对话，行程卡各自切换地图 | 无 |
| ISSUE-011 | 已确认：聊天框常在，提问在下；白点和连线已改 | 无 |
| ISSUE-012 | 已确认：没对上的地点由页面补搜。离线 22 项 OK。真实提问待补 | 无 |
| ISSUE-013 | 已确认：去掉「这句话已经发出去了」 | 无 |
| ISSUE-014 | 已确认：接着问时示例仍留在聊天框内部最下面 | 无 |
| ISSUE-015 | 已完成：高德不通时补查第一次失败就停；README 补 JS key 和界面截图 | 无 |
| ISSUE-016 | 已完成：README 开头重写，加 LICENSE；GitHub 简介与话题已更新 | 无 |

## 已确定的技术决策

- 界面结构以 `prototypes/travel-ui-v0.11.html` 为准；外观之后按 Stitch 稿替换。
- 前端方案 A（Gradio 内嵌高德 JS）已确认。ISSUE-003 离线已完成。

## 不做的事

- 订票、登录、拖拽、手绘地图；不改成 Deep Agents 或向量库

## 下一步

PR #3 等人工审查后合并；合并后核对 GitHub 是否识别 MIT 许可证。git 一律用 Windows git，不用 `bash -lc`。只有用户说出「很急」才算急。
