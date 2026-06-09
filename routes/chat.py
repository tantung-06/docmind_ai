"""
routes/chat.py — Quản lý phiên hội thoại và streaming chat
"""

import json
import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, Response, stream_with_context

from routes.auth import current_user
from store import documents_store, user_convs, save_convs
from services.chunker import retrieve_chunks
from services import ollama

chat_bp = Blueprint("chat", __name__)


# Helper

def make_title(text: str, max_len: int = 40) -> str:
    """Tự động đặt tiêu đề phiên từ tin nhắn đầu tiên."""
    t = text.strip().replace("\n", " ")
    return t[:max_len] + ("…" if len(t) > max_len else "")


# Conversations (phiên chat)

@chat_bp.route("/api/conversations", methods=["GET"])
def list_conversations():
    user = current_user()
    if not user:
        return jsonify({"conversations": []})

    convs = list(user_convs.get(user["id"], {}).values())
    convs.sort(key=lambda c: c["updated_at"], reverse=True)

    return jsonify({
        "conversations": [
            {
                "id":         c["id"],
                "title":      c["title"],
                "msg_count":  len(c["messages"]),
                "created_at": c["created_at"],
                "updated_at": c["updated_at"],
            }
            for c in convs
        ]
    })


@chat_bp.route("/api/conversations", methods=["POST"])
def create_conversation():
    user = current_user()
    if not user:
        return jsonify({"error": "Chưa đăng nhập"}), 401

    data    = request.get_json(force=True) or {}
    title   = (data.get("title") or "Cuộc trò chuyện mới").strip()
    conv_id = str(uuid.uuid4())
    now     = datetime.now().isoformat()

    conv = {"id": conv_id, "title": title, "messages": [],
            "created_at": now, "updated_at": now}
    user_convs.setdefault(user["id"], {})[conv_id] = conv

    save_convs()   # lưu xuống file

    return jsonify({"conversation": {
        "id": conv_id, "title": title,
        "msg_count": 0, "created_at": now, "updated_at": now,
    }})


@chat_bp.route("/api/conversations/<conv_id>", methods=["GET"])
def get_conversation(conv_id: str):
    user = current_user()
    if not user:
        return jsonify({"error": "Chưa đăng nhập"}), 401

    conv = user_convs.get(user["id"], {}).get(conv_id)
    if not conv:
        return jsonify({"error": "Không tìm thấy"}), 404
    return jsonify({"conversation": conv})


@chat_bp.route("/api/conversations/<conv_id>", methods=["PATCH"])
def rename_conversation(conv_id: str):
    user = current_user()
    if not user:
        return jsonify({"error": "Chưa đăng nhập"}), 401

    conv = user_convs.get(user["id"], {}).get(conv_id)
    if not conv:
        return jsonify({"error": "Không tìm thấy"}), 404

    data      = request.get_json(force=True) or {}
    new_title = (data.get("title") or "").strip()
    if new_title:
        conv["title"] = new_title
        save_convs()
    return jsonify({"ok": True})


@chat_bp.route("/api/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id: str):
    user = current_user()
    if not user:
        return jsonify({"error": "Chưa đăng nhập"}), 401

    user_convs.get(user["id"], {}).pop(conv_id, None)
    save_convs()
    return jsonify({"message": "Đã xóa"})


# Chat streaming

@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    data     = request.get_json(force=True)
    user_msg = data.get("message", "").strip()
    doc_ids  = data.get("doc_ids", [])
    conv_id  = data.get("conv_id")       # None = chưa có phiên

    if not user_msg:
        return jsonify({"error": "Tin nhắn rỗng"}), 400

    user         = current_user()
    is_logged_in = user is not None
    uid          = user["id"] if user else None

    # Tạo phiên mới tự động khi đã đăng nhập nhưng chưa có conv_id
    if is_logged_in and not conv_id:
        conv_id = str(uuid.uuid4())
        now     = datetime.now().isoformat()
        user_convs.setdefault(uid, {})[conv_id] = {
            "id":         conv_id,
            "title":      make_title(user_msg),
            "messages":   [],
            "created_at": now,
            "updated_at": now,
        }

    # Lấy lịch sử 10 lượt gần nhất
    if is_logged_in and conv_id:
        conv = user_convs.get(uid, {}).get(conv_id)
        if not conv:
            return jsonify({"error": "Phiên không tồn tại"}), 404
        history = conv["messages"][-10:]
    else:
        history = []

    # Xây dựng RAG context từ các tài liệu được chọn
    context_parts = []
    for did in doc_ids:
        doc = documents_store.get(did)
        if not doc:
            continue
        relevant = retrieve_chunks(user_msg, doc["chunks"], top_k=4)
        if relevant:
            context_parts.append(
                f"[Tài liệu: {doc['name']}]\n" + "\n---\n".join(relevant)
            )

    system_prompt = (
        "Bạn là trợ lý AI thông minh chuyên phân tích tài liệu. "
        "Trả lời bằng tiếng Việt, chính xác và có cấu trúc rõ ràng. "
        "Dựa vào nội dung tài liệu được cung cấp để trả lời. "
        "Nếu thông tin không có trong tài liệu, hãy nói rõ điều đó."
    )
    if context_parts:
        system_prompt += "\n\nNỘI DUNG TÀI LIỆU THAM KHẢO:\n" + "\n\n".join(context_parts)

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_msg})

    def generate():
        full_response = ""

        for token in ollama.chat_stream(messages):
            full_response += token
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Lưu tin nhắn vào lịch sử (chỉ khi đã đăng nhập)
        now = datetime.now().isoformat()
        if is_logged_in and conv_id and uid in user_convs and conv_id in user_convs[uid]:
            c = user_convs[uid][conv_id]
            c["messages"].append({"role": "user",      "content": user_msg,      "timestamp": now})
            c["messages"].append({"role": "assistant", "content": full_response, "timestamp": now})
            c["updated_at"] = now
            save_convs()

        yield f"data: {json.dumps({'done': True, 'saved': is_logged_in, 'conv_id': conv_id})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )