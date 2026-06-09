"""
routes/auth.py — Đăng ký / Đăng nhập / Đăng xuất / Thông tin tài khoản
"""

import uuid
import hashlib
from datetime import datetime

from flask import Blueprint, request, jsonify, session
from store import users_store, save_users

auth_bp = Blueprint("auth", __name__)


# Helpers

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def current_user() -> dict | None:
    """Trả về user hiện tại từ Flask session, hoặc None nếu chưa đăng nhập."""
    uid = session.get("user_id")
    if not uid:
        return None
    for u in users_store.values():
        if u["id"] == uid:
            return u
    return None


# Routes

@auth_bp.route("/api/register", methods=["POST"])
def register():
    data         = request.get_json(force=True)
    username     = (data.get("username")     or "").strip()
    password     = (data.get("password")     or "").strip()
    display_name = (data.get("display_name") or username).strip()

    if not username or not password:
        return jsonify({"error": "Vui lòng nhập đầy đủ"}), 400
    if len(username) < 3:
        return jsonify({"error": "Tên đăng nhập phải ≥ 3 ký tự"}), 400
    if len(password) < 6:
        return jsonify({"error": "Mật khẩu phải ≥ 6 ký tự"}), 400
    if username in users_store:
        return jsonify({"error": "Tên đăng nhập đã tồn tại"}), 409

    uid = str(uuid.uuid4())
    users_store[username] = {
        "id":            uid,
        "username":      username,
        "display_name":  display_name,
        "password_hash": hash_password(password),
        "created_at":    datetime.now().isoformat(),
    }

    session.clear()
    session["user_id"] = uid
    session.permanent  = True

    save_users()   # lưu xuống file

    return jsonify({
        "message": "Đăng ký thành công!",
        "user": {"id": uid, "username": username, "display_name": display_name},
    })


@auth_bp.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "Vui lòng nhập đầy đủ"}), 400

    user = users_store.get(username)
    if not user or user["password_hash"] != hash_password(password):
        return jsonify({"error": "Tên đăng nhập hoặc mật khẩu không đúng"}), 401

    session.clear()
    session["user_id"] = user["id"]
    session.permanent  = True

    return jsonify({
        "message": "Đăng nhập thành công!",
        "user": {
            "id":           user["id"],
            "username":     user["username"],
            "display_name": user["display_name"],
        },
    })


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Đã đăng xuất"})


@auth_bp.route("/api/me", methods=["GET"])
def me():
    user = current_user()
    if not user:
        return jsonify({"logged_in": False, "user": None})
    return jsonify({
        "logged_in": True,
        "user": {
            "id":           user["id"],
            "username":     user["username"],
            "display_name": user["display_name"],
        },
    })