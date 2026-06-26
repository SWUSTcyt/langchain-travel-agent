"""应用启动入口"""

import logging

from ui import create_gradio_app, APP_THEME, load_app_css


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    app = create_gradio_app()
    # Gradio 6：主题与自定义 CSS 在 launch() 时应用
    app.launch(
        server_name="127.0.0.1",
        share=False,
        theme=APP_THEME,
        css=load_app_css(),
    )
