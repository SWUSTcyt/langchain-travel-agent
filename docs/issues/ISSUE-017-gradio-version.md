# Issue: requirements.txt 的 Gradio 版本与实际一致

> 状态：已确认并完成。

## 用户原话（2026-10-23）

那你说的这个可以改，改完也合并到当前的 PR，然后帮我进行代码合并。

## 来源

ISSUE-016 的 P2：`requirements.txt` 写 `gradio>=4.1.0`，但页面在 `launch()` 里传 `theme`、`css`、`head`，这是 Gradio 6 的用法。装了 4.x 或 5.x 的人会启动失败或丢样式。

## 要改

- `requirements.txt`：`gradio>=4.1.0` 改为 `gradio>=6.0.0`。

## 不改

- 其它依赖（`dashscope`、`langchain-community` 只被仓库根目录的旧测试脚本使用，不在本任务里清理）。
- 代码、README。

## 验收标准

### P0

- [x] `requirements.txt` 中 Gradio 下限为 6.0.0，当前环境（gradio 6.0.1）满足。证据：版本比较输出 `satisfies >=6.0.0: True`。
- [x] 单测全部通过。证据：`unittest discover` OK。

### P1

- [x] README 技术栈表与 `requirements.txt` 不再矛盾。证据：README 写 gradio 6.0.1，requirements 下限 6.0.0。
