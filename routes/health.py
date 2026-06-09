"""
routes/health.py — Kiểm tra trạng thái Ollama và ứng dụng
"""

from datetime import datetime
from flask import Blueprint, jsonify

from routes.auth import current_user
from store import documents_store, users_store
from services import ollama

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health")
def health():
    user = current_user()
    return jsonify({
        "app":               "ok",
        "ollama":            ollama.health(),
        "documents_loaded":  len(documents_store),
        "registered_users":  len(users_store),
        "current_user":      user["username"] if user else None,
        "timestamp":         datetime.now().isoformat(),
    })