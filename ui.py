"""Gradio 前端界面（流式输出 + 过程日志）"""

from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Any, Dict

import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage

from agent import agent
import config
import itinerary
import itinerary_view
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


def _search_fetcher(cache: dict, city: str | None):
    """没对上的地点名再搜一次。同一名字一轮只搜一次，并带上当前城市。"""

    def fetch(keywords: str):
        if keywords in cache:
            return cache[keywords]
        from tools import get_global_tools

        tool = next(
            (item for item in get_global_tools() if getattr(item, "name", "") == "maps_text_search"),
            None,
        )
        if tool is None:
            cache[keywords] = ""
            return ""
        args = {"keywords": keywords}
        if city:
            args["city"] = city
        try:
            cache[keywords] = tool.invoke(args)
        except Exception:
            cache[keywords] = ""
        return cache[keywords]

    return fetch


def _detail_fetcher(cache: dict):
    """按关键词搜索给出的 id 查详情坐标。同一 id 一轮只查一次。"""

    def fetch(poi_id: str):
        if poi_id in cache:
            return cache[poi_id]
        from tools import get_global_tools

        tool = next(
            (item for item in get_global_tools() if getattr(item, "name", "") == "maps_search_detail"),
            None,
        )
        if tool is None:
            cache[poi_id] = ""
            return ""
        try:
            cache[poi_id] = tool.invoke({"id": poi_id})
        except Exception:
            cache[poi_id] = ""
        return cache[poi_id]

    return fetch


def _present_turn(final_text: str, raw_events, trip, fetch_detail=None, fetch_search=None):
    """去掉行程代码块，并按本轮工具结果补坐标。界面布局仍由调用方决定。"""
    city = trip.cities[0] if getattr(trip, "cities", None) else None
    messages = itinerary.tool_messages_from_events(raw_events)
    return itinerary.finalize_turn(
        final_text or "",
        messages,
        city=city,
        fetch_detail=fetch_detail,
        fetch_search=fetch_search,
    )


def stream_answer(
    user_text: str, chat_history, dev_mode_flag: bool
):
    """使用 agent.stream 做增量推送。

    每次产出：思考过程、最终答案、日志、原始事件、文字行程、地图行程。
    没有结构化文字时文字行程为 None；只要这次查到坐标，地图行程仍在。
    """
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
    city = trip.cities[0] if trip.cities else None
    fetch_detail = _detail_fetcher({})
    fetch_search = _search_fetcher({}, city)

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
        display_text, turn_itinerary, map_itinerary = _present_turn(
            final_text, raw_events, trip
        )
        yield (
            reasoning_text,  # 思考过程（累积）
            display_text,    # 最终答案（已去掉行程代码块）
            md_text,
            raw_events if dev_mode_flag else None,
            turn_itinerary,
            map_itinerary,
        )

    # 兜底：没流出文本就 invoke 一次
    if not final_text:
        result = agent.invoke(
            {"messages": turn_messages},
            config={"recursion_limit": 40},
            context=trip,
        )
        fallback_messages = list(result.get("messages", []) or [])
        for msg in reversed(fallback_messages):
            if isinstance(msg, AIMessage):
                # 提取 content
                final_text = msg.content if hasattr(msg, 'content') else str(msg)

                # 兜底时也提取 reasoning
                if hasattr(msg, 'additional_kwargs') and isinstance(msg.additional_kwargs, dict):
                    reasoning_text = msg.additional_kwargs.get('reasoning_content', '')
                break
        raw_events.append({"tools": {"messages": fallback_messages}})

    # 最终输出
    md_text = "  \n".join(summaries) if summaries else "（本次尚无日志）"
    display_text, turn_itinerary, map_itinerary = _present_turn(
        final_text, raw_events, trip, fetch_detail, fetch_search
    )
    yield (
        reasoning_text,
        display_text,
        md_text,
        raw_events if dev_mode_flag else None,
        turn_itinerary,
        map_itinerary,
    )


def load_app_css() -> str:
    """读取外置自定义样式（assets/custom.css），与逻辑分离；缺失时降级为空。"""
    css_path = Path(__file__).parent / "assets" / "custom.css"
    try:
        return css_path.read_text(encoding="utf-8")
    except Exception:
        return ""


# 现代化主题（Gradio 6：theme 在 launch() 时应用，见 main.py）
APP_THEME = gr.themes.Soft(
    primary_hue="teal",
    secondary_hue="blue",
    neutral_hue="slate",
    radius_size="lg",
)


def page_head() -> str:
    """启动时注入地图脚本。key 只来自环境变量。"""
    return itinerary_view.page_head(config.AMAP_JS_KEY, config.AMAP_JS_SECURITY_CODE)


def _thread_view(items, selected_id=None, pending_question: str = ""):
    """左列对话。正文始终在文字面板里，另一栏留空。"""
    html = itinerary_view.conversation_html(
        items,
        selected_id=selected_id,
        pending_question=pending_question,
        js_key=config.AMAP_JS_KEY or "",
    )
    return gr.update(value=html, visible=True), gr.update(value="", visible=False)


def _map_payload(turn_itinerary) -> str:
    """没有新行程时用默认空地图，不把右栏收起来。"""
    return itinerary_view.map_payload_text(turn_itinerary, config.AMAP_JS_KEY or "")


def create_gradio_app():
    """左文字、右地图。思考过程和工具日志放在下方的开发者折叠里。

    注意：Gradio 6 起 theme/css/head 在 launch() 时传入（见 main.py）。
    """
    empty_text = itinerary_view.conversation_html([], js_key=config.AMAP_JS_KEY or "")
    with gr.Blocks(title="旅游助手") as demo:
        gr.HTML(
            """
            <div id="ta-header">
              <h1>旅游助手</h1>
              <p>左边是聊过的话，右边是选中这一次的地点。</p>
            </div>
            """
        )
        history_state = gr.State([])
        thread_state = gr.State([])
        with gr.Row(elem_id="ta-main-row"):
            with gr.Column(scale=58, elem_id="ta-text-card"):
                text_panel = gr.HTML(empty_text)
                prose_panel = gr.Markdown(visible=False)
                with gr.Row(elem_id="ta-ask-row"):
                    txt = gr.Textbox(
                        placeholder="成都三天，轻松一点",
                        scale=8,
                        lines=2,
                        max_lines=4,
                        show_label=False,
                        autofocus=True,
                        elem_id="ta-input",
                    )
                    send_btn = gr.Button("发送", scale=1, variant="primary", elem_id="ta-send")
                clear_btn = gr.Button("清空对话", elem_id="ta-clear")
            with gr.Column(scale=42, elem_id="ta-map-card"):
                # 容器只创建一次。高德会改这个 div，不能再交给 Gradio 整段替换，否则换城市后还是上一张图。
                gr.HTML(
                    '<div id="trip-map" class="map-canvas"></div><p id="trip-map-legend"></p>'
                )
                map_payload_box = gr.Textbox(
                    value=_map_payload(None),
                    show_label=False,
                    elem_id="trip-map-payload",
                    container=False,
                )
        with gr.Accordion("开发者", open=False):
            reasoning_md = gr.Markdown(value="（尚无思考过程）")
            dev_mode = gr.Checkbox(label="开发者模式（显示原始事件 JSON）", value=False)
            logs_md = gr.Markdown(value="（本次尚无日志）")
            logs_json = gr.JSON(label="原始事件", visible=False)

        def on_submit(history, thread, user_text, dev_mode_flag, current_map):
            history = list(history or [])
            thread = list(thread or [])
            question = (user_text or "").strip()
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": ""})
            turn_id = itinerary_view.next_turn_id(thread)
            text_html, prose_html = _thread_view(thread, pending_question=question)
            reasoning = ""
            md_logs = "（本次尚无日志）"
            raw = None
            answer_text = ""
            last_text_itinerary = None
            last_map_itinerary = None
            # 地点还没回来时先回到默认图。上一张有点的行程先记着，没查到或只问天气再放回去。
            previous_map = current_map if itinerary_view.payload_has_stops(current_map) else ""
            map_payload = _map_payload(None)
            yield (
                history,
                thread,
                text_html,
                prose_html,
                map_payload,
                gr.update(value=question, interactive=True),
                gr.update(value="正在查", interactive=False),
                "（尚无思考过程）",
                "（本次尚无日志）",
                gr.update(value=None, visible=bool(dev_mode_flag)),
            )
            has_final_content = False
            try:
                for (
                    reasoning,
                    final_content,
                    md_logs,
                    raw,
                    turn_itinerary,
                    map_itinerary,
                ) in stream_answer(user_text, history, dev_mode_flag):
                    if final_content and not has_final_content:
                        has_final_content = True
                    if final_content:
                        answer_text = final_content
                    if turn_itinerary is not None:
                        last_text_itinerary = turn_itinerary
                    if map_itinerary is not None:
                        last_map_itinerary = map_itinerary
                    message_parts = []
                    if reasoning:
                        is_open = " open" if not has_final_content else ""
                        message_parts.append(
                            f"<details{is_open}>\n<summary><b>AI 思考过程</b></summary>\n\n"
                            f"{reasoning}\n\n</details>"
                        )
                    if final_content:
                        if reasoning:
                            message_parts.append("\n\n---\n\n")
                        message_parts.append(f"## 最终答案\n\n{final_content}")
                    history[-1]["content"] = "".join(message_parts)
                    preview = itinerary_view.freeze_exchange(
                        turn_id,
                        question,
                        answer_text,
                        last_text_itinerary,
                        last_map_itinerary,
                        config.AMAP_JS_KEY or "",
                    )
                    if preview["kind"] == "itinerary":
                        text_html, prose_html = _thread_view(thread + [preview], preview["id"])
                        card_map = itinerary_view.exchange_map_text(preview)
                        if card_map:
                            map_payload = card_map
                    else:
                        text_html, prose_html = _thread_view(
                            thread, pending_question="" if answer_text else question
                        )
                        if answer_text:
                            text_html, prose_html = _thread_view(thread + [preview])
                    yield (
                        history,
                        thread,
                        text_html,
                        prose_html,
                        map_payload,
                        gr.update(value=question, interactive=True),
                        gr.update(value="正在查", interactive=False),
                        reasoning or "（尚无思考过程）",
                        md_logs,
                        gr.update(value=raw if dev_mode_flag else None, visible=bool(dev_mode_flag)),
                    )
            finally:
                record = itinerary_view.freeze_exchange(
                    turn_id,
                    question,
                    answer_text,
                    last_text_itinerary,
                    last_map_itinerary,
                    config.AMAP_JS_KEY or "",
                )
                thread = thread + [record]
                if record["kind"] == "itinerary":
                    selected = record["id"]
                    card_map = itinerary_view.exchange_map_text(record)
                    if card_map:
                        map_payload = card_map
                else:
                    selected = itinerary_view.last_itinerary_id(thread[:-1])
                    if last_map_itinerary is None:
                        map_payload = itinerary_view.next_map_payload(
                            None,
                            config.AMAP_JS_KEY or "",
                            has_text=True,
                            previous=previous_map,
                            finished=True,
                        )
                    else:
                        map_payload = itinerary_view.map_payload_text(
                            last_map_itinerary, config.AMAP_JS_KEY or ""
                        )
                text_html, prose_html = _thread_view(thread, selected)
                yield (
                    history,
                    thread,
                    text_html,
                    prose_html,
                    map_payload,
                    gr.update(value="", interactive=True),
                    gr.update(value="发送", interactive=True),
                    reasoning or "（尚无思考过程）",
                    md_logs,
                    gr.update(value=raw if dev_mode_flag else None, visible=bool(dev_mode_flag)),
                )

        submit_kwargs = dict(
            fn=on_submit,
            inputs=[history_state, thread_state, txt, dev_mode, map_payload_box],
            outputs=[history_state, thread_state, text_panel, prose_panel, map_payload_box, txt, send_btn, reasoning_md, logs_md, logs_json],
            queue=True,
            show_progress=True,
            concurrency_limit="default",
            concurrency_id="chat",
        )
        txt.submit(**submit_kwargs)
        send_btn.click(**submit_kwargs)

        def _clear(dev_flag):
            text_html, prose_html = _thread_view([])
            return (
                [],
                [],
                text_html,
                prose_html,
                _map_payload(None),
                "",
                gr.update(value="发送", interactive=True),
                "（尚无思考过程）",
                "（本次尚无日志）",
                gr.update(value=None, visible=bool(dev_flag)),
            )

        clear_btn.click(
            _clear,
            inputs=[dev_mode],
            outputs=[history_state, thread_state, text_panel, prose_panel, map_payload_box, txt, send_btn, reasoning_md, logs_md, logs_json],
            queue=False,
        )

    return demo
