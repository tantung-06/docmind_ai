"""
AI Document Chatbot - Flask Application
Hỗ trợ: PDF, DOCX, TXT | Auth + Multi-session chat history
"""

import os, json, uuid, hashlib, secrets, requests
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, stream_with_context, Response, session

import fitz
from docx import Document as DocxDocument

# ─── Config ───────────────────────────────────────────────────────────────────

UPLOAD_FOLDER  = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024

OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# ─── In-memory stores ────────────────────────────────────────────────────────
documents_store: dict[str, dict] = {}
# user_id -> { conv_id: {id, title, created_at, updated_at, messages:[]} }
user_convs:     dict[str, dict]  = {}
users_store:    dict[str, dict]  = {}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", secrets.token_hex(32))

# ─── Helpers ──────────────────────────────────────────────────────────────────

def allowed_file(f): return "." in f and f.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def human_size(n):
    for u in ("B","KB","MB","GB"):
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def current_user():
    uid = session.get("user_id")
    if not uid: return None
    for u in users_store.values():
        if u["id"] == uid: return u
    return None

def make_title(text: str, max_len=40) -> str:
    """Lấy vài từ đầu của tin nhắn làm tiêu đề phiên."""
    t = text.strip().replace("\n", " ")
    return t[:max_len] + ("…" if len(t) > max_len else "")

# ─── Text extraction ──────────────────────────────────────────────────────────

def extract_pdf(p):
    parts = []
    with fitz.open(str(p)) as d:
        for page in d: parts.append(page.get_text())
    return "\n\n".join(parts)

def extract_docx(p):
    doc = DocxDocument(str(p))
    return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())

def extract_txt(p):
    for enc in ("utf-8","utf-16","cp1252","latin-1"):
        try: return p.read_text(encoding=enc)
        except: pass
    return p.read_bytes().decode("utf-8", errors="replace")

def extract_text(p, ext):
    return {"pdf": extract_pdf, "docx": extract_docx, "txt": extract_txt}[ext](p)

# ─── Chunking / RAG ──────────────────────────────────────────────────────────

def chunk_text(text, chunk_size=800, overlap=100):
    if not text.strip(): return []
    words = text.split()
    chunks, buf, buf_len = [], [], 0
    for w in words:
        buf.append(w); buf_len += len(w)+1
        if buf_len >= chunk_size:
            chunks.append(" ".join(buf))
            buf = buf[-overlap//6:] if overlap else []
            buf_len = sum(len(x)+1 for x in buf)
    if buf: chunks.append(" ".join(buf))
    return chunks

def retrieve_chunks(query, chunks, top_k=5):
    if not chunks: return []
    q = set(query.lower().split())
    scored = sorted([(len(q & set(c.lower().split())), c) for c in chunks], reverse=True)
    return [c for _, c in scored[:top_k]]

# ─── Ollama ───────────────────────────────────────────────────────────────────

def ollama_chat_stream(messages):
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {"model": OLLAMA_MODEL, "messages": messages, "stream": True,
                "options": {"temperature": 0.3, "num_ctx": 4096}}
    try:
        with requests.post(url, json=payload, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line: continue
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token: yield token
                if data.get("done"): break
    except requests.exceptions.ConnectionError:
        yield f"\n\n⚠️ Không thể kết nối Ollama tại {OLLAMA_BASE_URL}"
    except Exception as exc:
        yield f"\n\n⚠️ Lỗi: {exc}"

def ollama_health():
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        return {"ok": True, "models": models, "target_model": OLLAMA_MODEL,
                "model_ready": any(OLLAMA_MODEL in m for m in models)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "models": [], "model_ready": False}

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    username     = (data.get("username") or "").strip()
    password     = (data.get("password") or "").strip()
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
    users_store[username] = {"id": uid, "username": username,
                              "display_name": display_name,
                              "password_hash": hash_password(password),
                              "created_at": datetime.now().isoformat()}
    session.clear(); session["user_id"] = uid; session.permanent = True
    return jsonify({"message": "Đăng ký thành công!",
                    "user": {"id": uid, "username": username, "display_name": display_name}})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        return jsonify({"error": "Vui lòng nhập đầy đủ"}), 400
    user = users_store.get(username)
    if not user or user["password_hash"] != hash_password(password):
        return jsonify({"error": "Tên đăng nhập hoặc mật khẩu không đúng"}), 401
    session.clear(); session["user_id"] = user["id"]; session.permanent = True
    return jsonify({"message": "Đăng nhập thành công!",
                    "user": {"id": user["id"], "username": user["username"],
                             "display_name": user["display_name"]}})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Đã đăng xuất"})

@app.route("/api/me", methods=["GET"])
def me():
    user = current_user()
    if not user: return jsonify({"logged_in": False, "user": None})
    return jsonify({"logged_in": True,
                    "user": {"id": user["id"], "username": user["username"],
                             "display_name": user["display_name"]}})

# ─── Conversation (phiên chat) routes ────────────────────────────────────────

@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    user = current_user()
    if not user: return jsonify({"conversations": []})
    uid = user["id"]
    convs = list(user_convs.get(uid, {}).values())
    convs.sort(key=lambda c: c["updated_at"], reverse=True)
    # Trả về metadata (không gửi messages đầy đủ)
    result = [{
        "id":         c["id"],
        "title":      c["title"],
        "msg_count":  len(c["messages"]),
        "created_at": c["created_at"],
        "updated_at": c["updated_at"],
    } for c in convs]
    return jsonify({"conversations": result})

@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    user = current_user()
    if not user: return jsonify({"error": "Chưa đăng nhập"}), 401
    uid = user["id"]
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "Cuộc trò chuyện mới").strip()
    conv_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conv = {"id": conv_id, "title": title, "messages": [],
            "created_at": now, "updated_at": now}
    user_convs.setdefault(uid, {})[conv_id] = conv
    return jsonify({"conversation": {
        "id": conv_id, "title": title, "msg_count": 0,
        "created_at": now, "updated_at": now}})

@app.route("/api/conversations/<conv_id>", methods=["GET"])
def get_conversation(conv_id):
    user = current_user()
    if not user: return jsonify({"error": "Chưa đăng nhập"}), 401
    uid = user["id"]
    conv = user_convs.get(uid, {}).get(conv_id)
    if not conv: return jsonify({"error": "Không tìm thấy"}), 404
    return jsonify({"conversation": conv})

@app.route("/api/conversations/<conv_id>", methods=["PATCH"])
def rename_conversation(conv_id):
    user = current_user()
    if not user: return jsonify({"error": "Chưa đăng nhập"}), 401
    uid = user["id"]
    conv = user_convs.get(uid, {}).get(conv_id)
    if not conv: return jsonify({"error": "Không tìm thấy"}), 404
    data = request.get_json(force=True) or {}
    new_title = (data.get("title") or "").strip()
    if new_title: conv["title"] = new_title
    return jsonify({"ok": True})

@app.route("/api/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    user = current_user()
    if not user: return jsonify({"error": "Chưa đăng nhập"}), 401
    uid = user["id"]
    user_convs.get(uid, {}).pop(conv_id, None)
    return jsonify({"message": "Đã xóa"})

# ─── Document APIs ────────────────────────────────────────────────────────────

@app.route("/")
def index(): return render_template("index.html")

@app.route("/chat")
def chat_page(): return render_template("chat.html")

@app.route("/dashboard")
def dashboard_page(): return render_template("dashboard.html")

@app.route("/api/upload", methods=["POST"])
def upload_document():
    if "file" not in request.files: return jsonify({"error": "Không có file"}), 400
    file = request.files["file"]
    if not file.filename: return jsonify({"error": "Tên file rỗng"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Chỉ chấp nhận: PDF, DOCX, TXT"}), 400
    ext = file.filename.rsplit(".",1)[1].lower()
    doc_id = str(uuid.uuid4())
    save_path = UPLOAD_FOLDER / f"{doc_id}.{ext}"
    file.save(save_path)
    sz = save_path.stat().st_size
    try:
        raw = extract_text(save_path, ext)
    except Exception as exc:
        save_path.unlink(missing_ok=True)
        return jsonify({"error": f"Không thể đọc: {exc}"}), 422
    chunks = chunk_text(raw)
    documents_store[doc_id] = {
        "id": doc_id, "name": file.filename, "ext": ext,
        "size": sz, "size_human": human_size(sz),
        "chunks": chunks, "char_count": len(raw),
        "word_count": len(raw.split()), "chunk_count": len(chunks),
        "uploaded_at": datetime.now().isoformat(), "path": str(save_path),
    }
    return jsonify({"id": doc_id, "name": file.filename, "ext": ext,
                    "size_human": human_size(sz), "word_count": len(raw.split()),
                    "chunk_count": len(chunks), "message": "Thành công!"})

@app.route("/api/documents", methods=["GET"])
def list_documents():
    docs = [{"id": d["id"], "name": d["name"], "ext": d["ext"],
              "size_human": d["size_human"], "word_count": d["word_count"],
              "chunk_count": d["chunk_count"], "uploaded_at": d["uploaded_at"]}
             for d in documents_store.values()]
    docs.sort(key=lambda d: d["uploaded_at"], reverse=True)
    return jsonify({"documents": docs, "total": len(docs)})

@app.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    doc = documents_store.pop(doc_id, None)
    if not doc: return jsonify({"error": "Không tìm thấy"}), 404
    Path(doc["path"]).unlink(missing_ok=True)
    return jsonify({"message": "Đã xóa"})

# ─── Chat API ────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    data        = request.get_json(force=True)
    user_msg    = data.get("message", "").strip()
    doc_ids     = data.get("doc_ids", [])
    conv_id     = data.get("conv_id")   # None khi chưa đăng nhập / chưa chọn phiên

    if not user_msg: return jsonify({"error": "Tin nhắn rỗng"}), 400

    user = current_user()
    is_logged_in = user is not None
    uid = user["id"] if user else None

    # Nếu user đăng nhập và chưa có conv_id → tạo phiên mới
    if is_logged_in and not conv_id:
        conv_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        user_convs.setdefault(uid, {})[conv_id] = {
            "id": conv_id,
            "title": make_title(user_msg),
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }

    # Lấy history của phiên hiện tại
    if is_logged_in and conv_id:
        conv = user_convs.get(uid, {}).get(conv_id)
        if not conv: return jsonify({"error": "Phiên không tồn tại"}), 404
        history = conv["messages"][-10:]
    else:
        history = []

    # Build RAG context
    context_parts = []
    for did in doc_ids:
        doc = documents_store.get(did)
        if not doc: continue
        relevant = retrieve_chunks(user_msg, doc["chunks"], top_k=4)
        if relevant:
            context_parts.append(f"[Tài liệu: {doc['name']}]\n" + "\n---\n".join(relevant))

    system_prompt = (
        "Bạn là trợ lý AI thông minh chuyên phân tích tài liệu. "
        "Trả lời bằng tiếng Việt, chính xác và có cấu trúc rõ ràng. "
        "Dựa vào nội dung tài liệu được cung cấp để trả lời. "
        "Nếu thông tin không có trong tài liệu, hãy nói rõ điều đó."
    )
    if context_parts:
        system_prompt += f"\n\nNỘI DUNG TÀI LIỆU THAM KHẢO:\n" + "\n\n".join(context_parts)

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_msg})

    def generate():
        full_response = ""
        for token in ollama_chat_stream(messages):
            full_response += token
            yield f"data: {json.dumps({'token': token})}\n\n"

        now = datetime.now().isoformat()
        if is_logged_in and conv_id and uid in user_convs and conv_id in user_convs[uid]:
            c = user_convs[uid][conv_id]
            c["messages"].append({"role": "user",      "content": user_msg,       "timestamp": now})
            c["messages"].append({"role": "assistant", "content": full_response,  "timestamp": now})
            c["updated_at"] = now
            # Nếu chưa có tiêu đề (phiên mới vừa tạo), đặt title từ tin đầu
            if c["title"] == make_title(user_msg) or not c["title"]:
                c["title"] = make_title(user_msg)

        yield f"data: {json.dumps({'done': True, 'saved': is_logged_in, 'conv_id': conv_id})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ─── Health ──────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    user = current_user()
    return jsonify({"app": "ok", "ollama": ollama_health(),
                    "documents_loaded": len(documents_store),
                    "registered_users": len(users_store),
                    "current_user": user["username"] if user else None,
                    "timestamp": datetime.now().isoformat()})

# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("="*60)
    print(f"DocMind AI  |  Ollama: {OLLAMA_BASE_URL}  |  Model: {OLLAMA_MODEL}")
    print("http://localhost:5000")
    print("="*60)
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)