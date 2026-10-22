# Issue: README 与仓库展示信息

> 状态：已确认并完成。许可证识别待合并后核对。

## 用户原话（2026-10-23）

README 文件以及项目名称啥的你觉得是否需要调整，现在咱们的项目做的很好，宣传也要很好才行。

确认的选项：标题用「旅游助手 · Travel Agent」；不加英文小节；新增 MIT LICENSE，署名 SWUSTcyt；由 Agent 用 gh 更新 GitHub 简介和话题标签；改动放进 PR #3。

## 要改

- README 开头：标题、一句话卖点、徽章、截图、三个亮点、三步跑起来。
- 修正克隆地址（`SWUSTcyt/langchain-travel-agent`）和技术栈表（主程序用 `langchain-openai`；写明开发验证版本）。
- 去掉「🆕」；Claude Skills、思考过程挪到后面的「开发者」一节。
- 新增 `LICENSE`（MIT，2025-2026 SWUSTcyt）。
- GitHub 仓库简介改成当前功能；加话题标签。

## 不改

- 仓库名、代码、`requirements.txt`、页面上的「旅游助手」标题、截图。
- 环境配置的内容，只调位置与格式。

## 验收标准

### P0

- [x] README 与 GitHub 简介里不出现与现有行为矛盾的说法（并行调用、路线规划、searchPOI、`<yourname>`）。证据：`rg` 搜 `readme.md` 无结果；`gh repo view` 简介已换成当前功能。
- [x] 不写入任何密钥。证据：README 只有变量名，LICENSE 无密钥。

### P1

- [x] 截图在 README 前 15 行内出现。证据：`readme.md` 第 10 行。
- [x] 技术栈表与主程序实际依赖一致。证据：`agent.py:6` 引入 `langchain_openai`；`pip list`：langchain 1.1.0、langchain-openai 1.3.2、langchain-mcp-adapters 0.1.14、gradio 6.0.1。
- [ ] GitHub 显示 MIT 许可证与话题标签。证据：话题标签 6 个已生效；`licenseInfo` 仍为 null，要等 PR #3 合并到 `main` 后 GitHub 才会识别。
- [x] README 中的相对链接都指向存在的文件。证据：`src/amap-mcp-config.png`、`docs/ARCHITECTURE.md`、`docs/images/ui-preview.png`、`LICENSE` 等逐个 `Test-Path` 为 True。

### P2

- [x] `requirements.txt` 的 `gradio>=4.1.0` 与实际需要的 Gradio 6 不一致，已在 ISSUE-017 改为 `>=6.0.0`。
