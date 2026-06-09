"""
app.py — Entry point của ứng dụng DocMind AI

Chỉ làm 2 việc:
  1. Tạo Flask app và nạp config
  2. Đăng ký tất cả các Blueprint (route groups)

Logic nghiệp vụ nằm trong:
  config.py          — biến môi trường
  store.py           — in-memory data stores
  services/          — extractor, chunker, ollama
  routes/            — auth, documents, chat, health
"""

import secrets
from flask import Flask

from config import MAX_CONTENT_LENGTH
from routes.auth      import auth_bp
from routes.documents import documents_bp
from routes.chat      import chat_bp
from routes.health    import health_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["SECRET_KEY"]         = secrets.token_hex(32)

    # Đăng ký tất cả các route groups
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(health_bp)

    return app


if __name__ == "__main__":
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL

    app = create_app()

    print("=" * 60)
    print(f"DocMind AI  |  Ollama: {OLLAMA_BASE_URL}  |  Model: {OLLAMA_MODEL}")
    print("http://localhost:5000")
    print("=" * 60)

    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)