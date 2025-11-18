"""应用启动入口"""

from ui import create_gradio_app


if __name__ == "__main__":
    app = create_gradio_app()
    app.launch(server_name="127.0.0.1", share=False)
