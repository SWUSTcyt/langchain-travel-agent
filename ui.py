"""Gradio 前端界面（流式输出 + 过程日志）"""

from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Any, Dict

import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage

from agent import agent
from middleware import msg_text, trip_state_from_texts
from turn_context import build_model_messages, session_user_texts


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


def _format_response_with_reasoning_separated(content: str, reasoning: str) -> str:
    """将思考过程和最终回复分离展示为结构化的消息内容"""
    parts = []

    # 添加思考过程部分（使用 HTML details 可折叠）
    if reasoning:
        parts.append(f"""<details>
<summary><b>💭 AI 思考过程</b></summary>

{reasoning}

</details>""")

    # 添加分隔线
    if reasoning:
        parts.append("\n---\n")

    # 添加最终回复部分
    if content:
        parts.append(f"""## 最终答案

{content}""")

    return "".join(parts)


def stream_answer(
    user_text: str, chat_history, dev_mode_flag: bool
) -> Tuple[str, str, str, Any]:  # 返回 4 个值：reasoning, final_content, logs, raw_events
    """使用 agent.stream 做增量推送，返回分离的思考过程和最终结果"""
    summaries: List[str] = []
    raw_events: List[Dict[str, Any]] = []
    final_text = ""
    reasoning_text = ""  # 累积思考过程
    tool_rounds_tracker = 0
    last_batch_prefix_seen = None
    # 行程状态只由本会话的用户原话算出，随请求传给中间件，不同浏览器会话互不影响。
    # 模型上下文仍只带上一轮原话和最终答案。
    trip = trip_state_from_texts(session_user_texts(chat_history, user_text))
    turn_messages = build_model_messages(chat_history, user_text)

    for event in agent.stream(
        {"messages": turn_messages},
        config={"recursion_limit": 40},
        context=trip,
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

        # 提取 reasoning 和 content，并在有更新时立即 yield（流式效果）
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

        # 每次事件都输出一次，保证流式效果
        md_text = "  \n".join(summaries) if summaries else "（本次尚无日志）"
        yield (
            reasoning_text,  # 思考过程（累积）
            final_text,      # 最终答案（累积）
            md_text,
            raw_events if dev_mode_flag else None,
        )

    # 兜底：没流出文本就 invoke 一次
    if not final_text:
        result = agent.invoke(
            {"messages": turn_messages},
            config={"recursion_limit": 40},
            context=trip,
        )
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage):
                # 提取 content
                final_text = msg.content if hasattr(msg, 'content') else str(msg)

                # 兜底时也提取 reasoning
                if hasattr(msg, 'additional_kwargs') and isinstance(msg.additional_kwargs, dict):
                    reasoning_text = msg.additional_kwargs.get('reasoning_content', '')
                break

    # 最终输出
    md_text = "  \n".join(summaries) if summaries else "（本次尚无日志）"
    yield (reasoning_text, final_text, md_text, raw_events if dev_mode_flag else None)


def load_app_css() -> str:
    """读取外置自定义样式（assets/custom.css），与逻辑分离；缺失时降级为空。"""
    css_path = Path(__file__).parent / "assets" / "custom.css"
    try:
        return css_path.read_text(encoding="utf-8")
    except Exception:
        return ""


# 首屏示例问题，降低用户上手门槛
EXAMPLE_PROMPTS = [
    "规划成都 2 天美食 + 人文轻松路线",
    "杭州周末 1 天，西湖周边 citywalk + 咖啡",
    "北京 3 天，故宫长城经典线，带交通和天气",
]

# 现代化主题（Gradio 6：theme 在 launch() 时应用，见 main.py）
APP_THEME = gr.themes.Soft(
    primary_hue="teal",
    secondary_hue="blue",
    neutral_hue="slate",
    radius_size="lg",
)


def create_gradio_app():
    """创建并返回 Gradio Blocks 应用（现代化主题 + 双栏布局，业务逻辑不变）

    注意：Gradio 6 起 theme/css 在 launch() 时传入（见 main.py），不再传给 Blocks。
    """
    with gr.Blocks(title="旅游助手") as demo:
        # 顶部品牌区
        gr.HTML(
            """
            <div id="ta-header">
              <h1>🧭 旅游助手</h1>
              <p>基于 LangChain Agent · 通义千问 Qwen · 高德地图 MCP，为你并行规划行程</p>
              <div class="ta-tags">
                <span class="ta-tag">POI 搜索</span>
                <span class="ta-tag">路线规划</span>
                <span class="ta-tag">天气查询</span>
                <span class="ta-tag">AI 思考过程</span>
              </div>
            </div>
            """
        )

        # 隐藏占位组件，保持事件输出签名不变
        status = gr.Markdown("", visible=False)

        with gr.Row(elem_id="ta-main-row"):
            # ===== 主对话区 =====
            with gr.Column(scale=3, elem_id="ta-chat-card"):
                chat = gr.Chatbot(
                    height=520,
                    label="对话",
                    elem_id="ta-chatbot",
                    layout="bubble",
                    buttons=["copy"],
                    placeholder="👋 你好！告诉我你的出行计划，我来帮你规划行程。",
                )
                with gr.Row():
                    txt = gr.Textbox(
                        placeholder="输入需求，如：规划成都 2 天美食 + 人文轻松路线…",
                        scale=8,
                        lines=1,
                        max_lines=4,
                        show_label=False,
                        autofocus=True,
                        elem_id="ta-input",
                    )
                    send_btn = gr.Button(
                        "发送", scale=1, variant="primary", elem_id="ta-send"
                    )
                with gr.Row():
                    clear_btn = gr.Button("🗑 清空对话", elem_id="ta-clear")
                gr.Examples(examples=EXAMPLE_PROMPTS, inputs=txt, label="试试这些")

            # ===== 侧栏：开发者与过程日志 =====
            with gr.Column(scale=1, elem_id="ta-side-card"):
                gr.Markdown("### ⚙️ 调试面板")
                dev_mode = gr.Checkbox(
                    label="开发者模式（显示原始事件 JSON）", value=False
                )
                with gr.Accordion("📋 过程与日志", open=False):
                    logs_md = gr.Markdown(label="摘要日志", value="（本次尚无日志）")
                    logs_json = gr.JSON(
                        label="原始事件（仅开发者模式显示）",
                        visible=False,
                    )

        def on_submit(history, user_text, dev_mode_flag):
            history = history or []
            # 添加用户消息
            history.append({"role": "user", "content": user_text})
            # 添加一个 AI 消息块，包含思考过程和最终答案，但视觉上分离
            history.append({"role": "assistant", "content": ""})

            # 接收 4 个返回值：reasoning, final_content, logs, raw_events
            has_final_content = False  # 跟踪是否已开始输出最终结果
            for reasoning, final_content, md_logs, raw in stream_answer(
                user_text, history, dev_mode_flag
            ):
                # 检测是否开始有最终结果
                if final_content and not has_final_content:
                    has_final_content = True

                # 构建完整消息（包含思考过程和最终答案，用分隔符分离）
                message_parts = []

                # 添加思考过程部分（可折叠，默认展开/收起取决于是否有最终结果）
                if reasoning:
                    is_open = " open" if not has_final_content else ""
                    message_parts.append(f"""<details{is_open}>
<summary><b>💭 AI 思考过程</b></summary>

{reasoning}

</details>""")

                # 添加分隔线和最终答案部分
                if final_content:
                    if reasoning:  # 只在有思考过程时添加分隔线
                        message_parts.append("\n\n---\n\n")  # 前后各加空行确保分隔线正确渲染
                    message_parts.append(f"""## 最终答案

{final_content}""")

                # 合并为单一消息
                history[-1]["content"] = "".join(message_parts)

                json_payload = raw if dev_mode_flag else None

                # 返回 5 个值：history, txt, status, logs_md, logs_json
                yield (
                    history,
                    gr.update(value="", interactive=True),
                    gr.update(visible=False),
                    gr.update(value=md_logs),
                    gr.update(value=json_payload, visible=bool(dev_mode_flag)),
                )

        # 提交：回车与「发送」按钮共用同一处理逻辑
        submit_kwargs = dict(
            fn=on_submit,
            inputs=[chat, txt, dev_mode],
            outputs=[chat, txt, status, logs_md, logs_json],
            queue=True,
            show_progress=True,
            concurrency_limit="default",
            concurrency_id="chat",
        )
        txt.submit(**submit_kwargs)
        send_btn.click(**submit_kwargs)

        def _clear(dev_flag):
            return (
                [],
                "",
                gr.update(visible=False),
                gr.update(value="（本次尚无日志）"),
                gr.update(value=None, visible=bool(dev_flag)),
            )

        clear_btn.click(
            _clear,
            inputs=[dev_mode],
            outputs=[chat, txt, status, logs_md, logs_json],
            queue=False,
        )

    return demo
