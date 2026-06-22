"""
routes/chat.py — Quản lý phiên hội thoại và streaming chat
"""

import json
import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, Response, stream_with_context

from routes.auth import current_user
from routes.documents import ensure_chunks, get_owner_id
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

    save_convs()

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
    conv_id  = data.get("conv_id")

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

    # Lấy lịch sử 6 lượt gần nhất
    if is_logged_in and conv_id:
        conv = user_convs.get(uid, {}).get(conv_id)
        if not conv:
            return jsonify({"error": "Phiên không tồn tại"}), 404
        history = conv["messages"][-6:]
    else:
        history = []

    # Xây dựng RAG context (chỉ dùng doc của owner hiện tại)
    owner_id      = get_owner_id()
    context_parts = []
    for did in doc_ids:
        doc = documents_store.get(did)
        if not doc:
            continue
        if doc.get("owner_id") != owner_id:
            continue
        ensure_chunks(doc)
        relevant = retrieve_chunks(user_msg, doc["chunks"], top_k=4)
        if relevant:
            context_parts.append(
                f"[Tài liệu: {doc['name']}]\n" + "\n---\n".join(relevant)
            )

    # System prompt
    if context_parts:
        context_text = "\n\n".join(context_parts)
        system_prompt = f"""
Bạn là trợ lý AI trả lời câu hỏi dựa trên CONTEXT.

QUY TẮC:
- Chỉ sử dụng thông tin trong CONTEXT.
- Không suy đoán.
- Nếu không tìm thấy thông tin, trả lời:
  "Tôi không tìm thấy thông tin này trong tài liệu."
- Trả lời đầy đủ và không bỏ sót ý.
- Nếu có nhiều thông tin liên quan, hãy liệt kê tất cả.
- Trả lời bằng ngôn ngữ của người dùng.

CONTEXT:
{context_text}
"""
    else:
        system_prompt = """Bạn là trợ lý AI chuyên hỏi đáp tài liệu.

Người dùng chưa chọn tài liệu nào. Hãy nhắc họ chọn tài liệu ở sidebar bên phải để bắt đầu.
Nếu câu hỏi mang tính chung chung (không cần tài liệu), vẫn trả lời bình thường."""

    # Gửi đến Ollama
    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_msg})

    def generate():
        full_response = ""

        for token in ollama.chat_stream(messages):
            full_response += token
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Lưu vào lịch sử (chỉ khi đã đăng nhập)
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