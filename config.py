"""
config.py — Cấu hình ứng dụng và biến môi trường
"""

import os
import secrets
from pathlib import Path

# Thư mục upload
UPLOAD_FOLDER      = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024          # 50 MB

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST",  "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# Flask
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))