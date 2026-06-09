"""
routes/documents.py — Upload, liệt kê và xoá tài liệu
"""

import uuid
from pathlib import Path
from datetime import datetime

from flask import Blueprint, request, jsonify, render_template
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from store import documents_store
from services.extractor import extract_text
from services.chunker import chunk_text

documents_bp = Blueprint("documents", __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ── Trang HTML ────────────────────────────────────────────────────────────────

@documents_bp.route("/")
def index():
    return render_template("index.html")


@documents_bp.route("/chat")
def chat_page():
    return render_template("chat.html")


@documents_bp.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


# ── API ───────────────────────────────────────────────────────────────────────

@documents_bp.route("/api/upload", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "Không có file"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Tên file rỗng"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Chỉ chấp nhận: PDF, DOCX, TXT"}), 400

    ext       = file.filename.rsplit(".", 1)[1].lower()
    doc_id    = str(uuid.uuid4())
    save_path = UPLOAD_FOLDER / f"{doc_id}.{ext}"
    file.save(save_path)

    file_size = save_path.stat().st_size

    try:
        raw_text = extract_text(save_path, ext)
    except Exception as exc:
        save_path.unlink(missing_ok=True)
        return jsonify({"error": f"Không thể đọc: {exc}"}), 422

    chunks = chunk_text(raw_text)

    documents_store[doc_id] = {
        "id":          doc_id,
        "name":        file.filename,
        "ext":         ext,
        "size":        file_size,
        "size_human":  human_size(file_size),
        "chunks":      chunks,
        "char_count":  len(raw_text),
        "word_count":  len(raw_text.split()),
        "chunk_count": len(chunks),
        "uploaded_at": datetime.now().isoformat(),
        "path":        str(save_path),
    }

    return jsonify({
        "id":          doc_id,
        "name":        file.filename,
        "ext":         ext,
        "size_human":  human_size(file_size),
        "word_count":  len(raw_text.split()),
        "chunk_count": len(chunks),
        "message":     "Tải lên thành công!",
    })


@documents_bp.route("/api/documents", methods=["GET"])
def list_documents():
    docs = [
        {
            "id":          d["id"],
            "name":        d["name"],
            "ext":         d["ext"],
            "size_human":  d["size_human"],
            "word_count":  d["word_count"],
            "chunk_count": d["chunk_count"],
            "uploaded_at": d["uploaded_at"],
        }
        for d in documents_store.values()
    ]
    docs.sort(key=lambda d: d["uploaded_at"], reverse=True)
    return jsonify({"documents": docs, "total": len(docs)})


@documents_bp.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str):
    doc = documents_store.pop(doc_id, None)
    if not doc:
        return jsonify({"error": "Không tìm thấy"}), 404
    Path(doc["path"]).unlink(missing_ok=True)
    return jsonify({"message": "Đã xóa"})