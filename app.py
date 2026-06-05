"""
AI Document Chatbot - Flask Application
Hỗ trợ: PDF, DOCX, TXT
AI Engine: Ollama với model qwen2.5:7b
"""

import os
import json
import uuid
import time
import threading
import requests
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, stream_with_context, Response

# Document processing
import fitz  # PyMuPDF for PDF
from docx import Document as DocxDocument

# ─── Config ───────────────────────────────────────────────────────────────────

UPLOAD_FOLDER   = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_CONTENT_LENGTH  = 50 * 1024 * 1024  # 50 MB

OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# In-memory stores (production: use Redis / SQLite)
documents_store: dict[str, dict] = {}   # doc_id -> {name, text, chunks, meta}
chat_sessions:   dict[str, list]  = {}  # session_id -> [messages]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["SECRET_KEY"] = os.urandom(24)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def human_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"


# ─── Text Extraction ──────────────────────────────────────────────────────────

def extract_pdf(path: Path) -> str:
    text_parts = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n\n".join(text_parts)


def extract_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_txt(path: Path) -> str:
    for enc in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


def extract_text(path: Path, ext: str) -> str:
    extractors = {"pdf": extract_pdf, "docx": extract_docx, "txt": extract_txt}
    extractor = extractors.get(ext)
    if extractor is None:
        raise ValueError(f"Unsupported format: {ext}")
    return extractor(path)


# ─── Chunking ─────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Simple character-level sliding-window chunker."""
    if not text.strip():
        return []
    words = text.split()
    chunks, buf = [], []
    buf_len = 0
    for word in words:
        buf.append(word)
        buf_len += len(word) + 1
        if buf_len >= chunk_size:
            chunks.append(" ".join(buf))
            # keep overlap words
            overlap_words = buf[-overlap // 6:] if overlap else []
            buf = overlap_words
            buf_len = sum(len(w) + 1 for w in buf)
    if buf:
        chunks.append(" ".join(buf))
    return chunks


def retrieve_chunks(query: str, chunks: list[str], top_k: int = 5) -> list[str]:
    """
    Keyword-based retrieval (no embedding required).
    For production replace with a proper vector store.
    """
    if not chunks:
        return []
    q_words = set(query.lower().split())
    scored = []
    for chunk in chunks:
        c_words = set(chunk.lower().split())
        score = len(q_words & c_words)
        scored.append((score, chunk))
    scored.sort(key=lambda x: -x[0])
    # Always return at least the first chunk even if score == 0
    return [c for _, c in scored[:top_k]]


# ─── Ollama ───────────────────────────────────────────────────────────────────

def ollama_chat_stream(messages: list[dict]):
    """Generator: yields text tokens from Ollama streaming API."""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.3, "num_ctx": 4096},
    }
    try:
        with requests.post(url, json=payload, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    yield token
                if data.get("done"):
                    break
    except requests.exceptions.ConnectionError:
        yield "\n\n⚠️ Không thể kết nối Ollama. Hãy chắc chắn Ollama đang chạy tại " + OLLAMA_BASE_URL
    except Exception as exc:
        yield f"\n\n⚠️ Lỗi: {exc}"


def ollama_health() -> dict:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        return {"ok": True, "models": models, "target_model": OLLAMA_MODEL,
                "model_ready": any(OLLAMA_MODEL in m for m in models)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "models": [], "model_ready": False}


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat")
def chat_page():
    return render_template("chat.html")


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


# ── Document APIs ─────────────────────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "Không có file"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Tên file rỗng"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Định dạng không hỗ trợ. Chỉ chấp nhận: PDF, DOCX, TXT"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    doc_id = str(uuid.uuid4())
    safe_name = f"{doc_id}.{ext}"
    save_path = UPLOAD_FOLDER / safe_name
    file.save(save_path)

    file_size = save_path.stat().st_size

    try:
        raw_text = extract_text(save_path, ext)
    except Exception as exc:
        save_path.unlink(missing_ok=True)
        return jsonify({"error": f"Không thể đọc file: {exc}"}), 422

    chunks = chunk_text(raw_text)

    documents_store[doc_id] = {
        "id": doc_id,
        "name": file.filename,
        "ext": ext,
        "size": file_size,
        "size_human": human_size(file_size),
        "chunks": chunks,
        "char_count": len(raw_text),
        "word_count": len(raw_text.split()),
        "chunk_count": len(chunks),
        "uploaded_at": datetime.now().isoformat(),
        "path": str(save_path),
    }

    return jsonify({
        "id": doc_id,
        "name": file.filename,
        "ext": ext,
        "size_human": human_size(file_size),
        "word_count": len(raw_text.split()),
        "chunk_count": len(chunks),
        "message": "Tải lên và xử lý thành công!",
    })


@app.route("/api/documents", methods=["GET"])
def list_documents():
    docs = []
    for doc in documents_store.values():
        docs.append({
            "id": doc["id"],
            "name": doc["name"],
            "ext": doc["ext"],
            "size_human": doc["size_human"],
            "word_count": doc["word_count"],
            "chunk_count": doc["chunk_count"],
            "uploaded_at": doc["uploaded_at"],
        })
    docs.sort(key=lambda d: d["uploaded_at"], reverse=True)
    return jsonify({"documents": docs, "total": len(docs)})


@app.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str):
    doc = documents_store.pop(doc_id, None)
    if doc is None:
        return jsonify({"error": "Không tìm thấy"}), 404
    Path(doc["path"]).unlink(missing_ok=True)
    return jsonify({"message": "Đã xóa"})


# ── Chat API ──────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    session_id  = data.get("session_id", "default")
    user_message = data.get("message", "").strip()
    doc_ids      = data.get("doc_ids", [])  # which docs to query

    if not user_message:
        return jsonify({"error": "Tin nhắn rỗng"}), 400

    # Init session
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    # Build context from selected documents
    context_parts = []
    for doc_id in doc_ids:
        doc = documents_store.get(doc_id)
        if not doc:
            continue
        relevant = retrieve_chunks(user_message, doc["chunks"], top_k=4)
        if relevant:
            block = f"[Tài liệu: {doc['name']}]\n" + "\n---\n".join(relevant)
            context_parts.append(block)

    system_prompt = (
        "Bạn là trợ lý AI thông minh chuyên phân tích tài liệu. "
        "Trả lời bằng tiếng Việt, chính xác và có cấu trúc rõ ràng. "
        "Dựa vào nội dung tài liệu được cung cấp để trả lời. "
        "Nếu thông tin không có trong tài liệu, hãy nói rõ điều đó."
    )

    if context_parts:
        context_text = "\n\n".join(context_parts)
        system_prompt += f"\n\nNỘI DUNG TÀI LIỆU THAM KHẢO:\n{context_text}"

    # Build message list for Ollama
    history = chat_sessions[session_id][-10:]  # keep last 10 turns
    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({"role": "user", "content": user_message})

    def generate():
        full_response = ""
        for token in ollama_chat_stream(messages):
            full_response += token
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Save to session history
        chat_sessions[session_id].append({"role": "user",    "content": user_message})
        chat_sessions[session_id].append({"role": "assistant","content": full_response})

        yield f"data: {json.dumps({'done': True, 'full': full_response})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/chat/history/<session_id>", methods=["GET"])
def get_history(session_id: str):
    return jsonify({"history": chat_sessions.get(session_id, [])})


@app.route("/api/chat/clear/<session_id>", methods=["DELETE"])
def clear_history(session_id: str):
    chat_sessions.pop(session_id, None)
    return jsonify({"message": "Đã xóa lịch sử"})


# ── Health / Status ───────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    ollama_status = ollama_health()
    return jsonify({
        "app": "ok",
        "ollama": ollama_status,
        "documents_loaded": len(documents_store),
        "active_sessions": len(chat_sessions),
        "timestamp": datetime.now().isoformat(),
    })


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("AI Document Chatbot")
    print(f"Ollama: {OLLAMA_BASE_URL}  |  Model: {OLLAMA_MODEL}")
    print("http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)