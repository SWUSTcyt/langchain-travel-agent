"""Gradio 前端界面（流式输出 + 过程日志）"""

from datetime import datetime
from typing import List, Tuple, Any, Dict

import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage

from agent import agent
from middleware import msg_text  # 复用工具函数


# ===== 工具小函数 =====

def _safe_trunc(v: str, maxlen=120):
    v = str(v)
    return (v[:maxlen] + "…") if len(v) > maxlen else v


def _fmt_ts():
    return datetime.now().strftime("%H:%M:%S")


def _mask_coord(x):
    """脱敏坐标（保留 3 位小数）"""
    if isinstance(x, str) and "," in x:
        try:
            a, b = x.split(",", 1)
            return f"{float(a):.3f},{float(b):.3f}"
        except Exception:
            return x
    return x


def _event_to_summary(event: dict) -> str:
    """将事件转换为摘要日志（不包含思维链）"""
    rounds_info = ""
    if "__tool_rounds__" in event:
        rounds = event.get("__tool_rounds__", 0)
        if rounds > 0:
            rounds_info = f"[轮次 {rounds}] "

    # 城市解析事件
    if "pin_cities_and_adcodes.before_model" in event:
        try:
            pin_data = event["pin_cities_and_adcodes.before_model"]
            if isinstance(pin_data, dict) and "messages" in pin_data:
                msgs = pin_data["messages"]
                for m in msgs:
                    text = (
                        msg_text(m)
                        if hasattr(m, "content") or isinstance(m, dict)
                        else str(m)
                    )
                    if "【DEBUG】本轮解析城市：" in text:
                        line = text.split("【DEBUG】本轮解析城市：", 1)[1].split("；")[0]
                        return f"[{_fmt_ts()}] 🛰 {rounds_info}解析城市：{line}"
                    elif "【强制约束】本轮用户指定城市：" in text:
                        import re

                        match = re.search(r"本轮用户指定城市：([^。]+)", text)
                        if match:
                            return f"[{_fmt_ts()}] 🛰 {rounds_info}解析城市：{match.group(1)}"
        except Exception:
            pass

    # 单工具事件
    if "tool" in event:
        name = event.get("tool", {}).get("name") or event.get("tool_name") or "tool"
        ti = event.get("tool_input") or event.get("input") or {}
        city = ti.get("city") or ti.get("cityd") or "-"
        origin = ti.get("origin") or "-"
        destination = ti.get("destination") or "-"
        origin = _mask_coord(origin)
        destination = _mask_coord(destination)
        return (
            f"[{_fmt_ts()}] 🔧 {rounds_info}工具 {name} | "
            f"city={city} | origin={origin} -> dest={destination}"
        )

    # 批量工具事件（并行调用）
    if "tools" in event:
        tools_info = []
        tools_data = event.get("tools", {})
        msgs = []
        if isinstance(tools_data, dict) and "messages" in tools_data:
            msgs = tools_data.get("messages", [])
            for m in msgs:
                if hasattr(m, "name"):
                    tools_info.append(getattr(m, "name", "?"))

        batch_prefix = None
        if msgs:
            first_msg = msgs[0]
            if hasattr(first_msg, "tool_call_id"):
                call_id = getattr(first_msg, "tool_call_id", "")
                if "_split_" in str(call_id):
                    batch_prefix = str(call_id).rsplit("_split_", 1)[0]

        tool_count = len(tools_info) if tools_info else len(msgs)

        if tools_info:
            tool_names_str = "、".join(tools_info[:3])
            if tool_count > 3:
                tool_names_str += f" 等 {tool_count} 个"
            if batch_prefix and tool_count > 1:
                return f"[{_fmt_ts()}] 🔧 {rounds_info}工具 {tool_names_str} 完成（并行批次）"
            if tool_count > 1:
                return f"[{_fmt_ts()}] 🔧 {rounds_info}工具 {tool_names_str} 完成"
            return f"[{_fmt_ts()}] 🔧 {rounds_info}工具 {tool_names_str} 完成"

        return f"[{_fmt_ts()}] 🔧 {rounds_info}工具调用完成"

    # 模型事件
    if "model" in event:
        return f"[{_fmt_ts()}] 🤖 {rounds_info}模型生成中…"

    # 消息更新事件
    if "messages" in event:
        try:
            msgs = event.get("messages") or []
            for m in msgs:
                text = (
                    msg_text(m)
                    if hasattr(m, "content") or isinstance(m, dict)
                    else str(m)
                )
                if "【DEBUG】本轮解析城市：" in text:
                    line = text.split("【DEBUG】本轮解析城市：", 1)[1].split("；")[0]
                    return f"[{_fmt_ts()}] 🛰 {rounds_info}解析城市：{line}"
                elif "【强制约束】本轮用户指定城市：" in text:
                    import re

                    match = re.search(r"本轮用户指定城市：([^。]+)", text)
                    if match:
                        return f"[{_fmt_ts()}] 🛰 {rounds_info}解析城市：{match.group(1)}"
        except Exception:
            pass
        return f"[{_fmt_ts()}] 📩 {rounds_info}消息更新"

    return f"[{_fmt_ts()}] 📎 {rounds_info}事件 {_safe_trunc(str(list(event.keys())))}"


def stream_answer(
    user_text: str, chat_history, dev_mode_flag: bool
) -> Tuple[str, str, str, Any]:  # 🆕 返回 4 个值：content, logs, reasoning, raw_events
    """使用 agent.stream 做增量推送，并生成摘要 / JSON 日志 + reasoning"""
    summaries: List[str] = []
    raw_events: List[Dict[str, Any]] = []
    final_text = ""
    reasoning_text = ""  # 🆕 累积思考过程
    tool_rounds_tracker = 0
    last_batch_prefix_seen = None

    for event in agent.stream(
        {"messages": [HumanMessage(content=user_text)]},
        config={"recursion_limit": 40},
    ):
        if isinstance(event, dict):
            current_batch_prefix = None
            if "tools" in event or "tool" in event:
                tool_call_id = None
                if "tool" in event:
                    tool_data = event.get("tool", {})
                    if isinstance(tool_data, dict):
                        tool_call_id = (
                            tool_data.get("tool_call_id") or tool_data.get("id")
                        )
                elif "tools" in event:
                    tools_data = event.get("tools", {})
                    if isinstance(tools_data, dict) and "messages" in tools_data:
                        msgs = tools_data.get("messages", [])
                        if msgs:
                            first_msg = msgs[0]
                            if hasattr(first_msg, "tool_call_id"):
                                tool_call_id = getattr(first_msg, "tool_call_id", None)
                if tool_call_id:
                    if "_split_" in str(tool_call_id):
                        current_batch_prefix = str(tool_call_id).rsplit("_split_", 1)[0]
                    else:
                        current_batch_prefix = str(tool_call_id)

                if current_batch_prefix and current_batch_prefix != last_batch_prefix_seen:
                    tool_rounds_tracker += 1
                    last_batch_prefix_seen = current_batch_prefix

            event_with_rounds = dict(event)
            event_with_rounds["__tool_rounds__"] = tool_rounds_tracker
            raw_events.append(event_with_rounds)

        try:
            if isinstance(event, dict):
                summaries.append(_event_to_summary(event))
        except Exception:
            pass

        msgs = None
        if isinstance(event, dict):
            if "model" in event and isinstance(event["model"], dict):
                msgs = event["model"].get("result") or event["model"].get("messages")
            elif "messages" in event:
                msgs = event["messages"]

        # 🆕 提取 reasoning 和 content
        if isinstance(msgs, list):
            for msg in msgs:
                if isinstance(msg, AIMessage):
                    # 提取 reasoning（从 additional_kwargs）
                    if hasattr(msg, 'additional_kwargs') and isinstance(msg.additional_kwargs, dict):
                        reasoning_chunk = msg.additional_kwargs.get('reasoning_content', '')
                        if reasoning_chunk:  # 只累积非空的 reasoning
                            reasoning_text += reasoning_chunk

                    # 提取 content（最终回复）
                    if hasattr(msg, 'content') and msg.content:
                        final_text = msg.content

        md_text = "  \n".join(summaries) if summaries else "（本次尚无日志）"
        yield (
            final_text or "",
            md_text,
            reasoning_text or "",  # 🆕 思考过程
            raw_events if dev_mode_flag else None,
        )

    # 兜底：没流出文本就 invoke 一次
    if not final_text:
        result = agent.invoke(
            {"messages": [HumanMessage(content=user_text)]},
            config={"recursion_limit": 40},
        )
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage):
                # 提取 content
                final_text = msg.content if hasattr(msg, 'content') else str(msg)

                # 🆕 兜底时也提取 reasoning
                if hasattr(msg, 'additional_kwargs') and isinstance(msg.additional_kwargs, dict):
                    reasoning_text = msg.additional_kwargs.get('reasoning_content', '')
                break

    md_text = "  \n".join(summaries) if summaries else "（本次尚无日志）"
    yield (final_text, md_text, reasoning_text, raw_events if dev_mode_flag else None)


def create_gradio_app():
    """创建并返回 Gradio Blocks 应用"""
    with gr.Blocks() as demo:
        gr.Markdown("## 旅游助手（MCP + Qwen + LangChain Agent）")
        chat = gr.Chatbot(height=480, label="对话")
        txt = gr.Textbox(placeholder="输入需求，如：规划成都2天美食+人文轻松路线…")
        clear_btn = gr.Button("清空")
        status = gr.Markdown("", visible=False)

        dev_mode = gr.Checkbox(label="开发者模式（显示原始事件 JSON）", value=False)

        with gr.Accordion("过程与日志（点击展开）", open=False):
            logs_md = gr.Markdown(label="摘要日志", value="（本次尚无日志）")
            logs_json = gr.JSON(
                label="原始事件（仅开发者模式显示）",
                visible=False,
            )

        # 🆕 新增：思考过程展示区域
        with gr.Accordion("💭 AI 思考过程（点击展开）", open=False):
            reasoning_md = gr.Markdown(
                label="深度推理链",
                value="（本次尚无思考记录）",
            )
            gr.Markdown("""
## 说明

这里展示了 AI 的内部推理过程，包括：

- **🎯 意图理解**：如何分析和理解你的需求
- **🔍 策略规划**：决定调用哪些工具以及调用顺序
- **🧩 信息整合**：如何根据工具结果组织最终回复
- **⚡ 推理链**：完整的思考步骤和逻辑

*注：思考过程仅供参考，最终以正式回复为准*
            """)

        def on_submit(history, user_text, dev_mode_flag):
            history = history or []
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": ""})

            # 🆕 接收 4 个返回值：content, logs, reasoning, raw_events
            for partial_text, md_logs, reasoning, raw in stream_answer(
                user_text, history, dev_mode_flag
            ):
                history[-1]["content"] = partial_text
                json_payload = raw if dev_mode_flag else None

                # 🆕 格式化 reasoning（添加标题和样式）
                formatted_reasoning = reasoning if reasoning else "（本次尚无思考记录）"

                # 🆕 返回 6 个值：history, txt, status, logs_md, logs_json, reasoning_md
                yield (
                    history,
                    gr.update(value="", interactive=True),
                    gr.update(visible=False),
                    gr.update(value=md_logs),
                    gr.update(value=json_payload, visible=bool(dev_mode_flag)),
                    gr.update(value=formatted_reasoning),  # 🆕 思考过程
                )

        txt.submit(
            on_submit,
            inputs=[chat, txt, dev_mode],
            # 🆕 新增 reasoning_md 到 outputs
            outputs=[chat, txt, status, logs_md, logs_json, reasoning_md],
            queue=True,
            show_progress=True,
            concurrency_limit="default",
            concurrency_id="chat",
        )

        def _clear(dev_flag):
            # 🆕 新增返回 reasoning_md 的清空状态
            return (
                [],
                "",
                gr.update(visible=False),
                gr.update(value="（本次尚无日志）"),
                gr.update(value=None, visible=bool(dev_flag)),
                gr.update(value="（本次尚无思考记录）"),  # 🆕 清空思考过程
            )

        clear_btn.click(
            _clear,
            inputs=[dev_mode],
            # 🆕 新增 reasoning_md 到 outputs
            outputs=[chat, txt, status, logs_md, logs_json, reasoning_md],
            queue=False,
        )

    return demo
