"""
store.py — Bộ nhớ dùng chung toàn ứng dụng
Tất cả stores đều được persist xuống file JSON trong thư mục data/
"""

import json
from pathlib import Path

# Đường dẫn file lưu trữ
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
CONVS_FILE = DATA_DIR / "conversations.json"
DOCS_FILE  = DATA_DIR / "documents.json"

# Helpers đọc/ghi JSON

def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# Stores

# username -> { id, username, display_name, password_hash, created_at }
users_store: dict[str, dict] = _load(USERS_FILE)

# user_id -> { conv_id -> { id, title, messages, created_at, updated_at } }
user_convs: dict[str, dict] = _load(CONVS_FILE)

# doc_id -> { id, name, ext, size_human, chunks, word_count, path, owner_id, ... }
# owner_id = user_id nếu đã đăng nhập, hoặc guest_<session_id> nếu khách
# Lọc bỏ những doc có file vật lý không còn tồn tại
def _load_documents() -> dict:
    docs  = _load(DOCS_FILE)
    valid = {k: v for k, v in docs.items() if Path(v.get("path", "")).exists()}
    return valid

documents_store: dict[str, dict] = _load_documents()

# Hàm lưu

def save_users() -> None:
    _save(USERS_FILE, users_store)

def save_convs() -> None:
    _save(CONVS_FILE, user_convs)

def save_documents() -> None:
    """Lưu documents_store xuống file (bỏ qua field chunks vì quá nặng)."""
    light = {
        doc_id: {k: v for k, v in doc.items() if k != "chunks"}
        for doc_id, doc in documents_store.items()
    }
    _save(DOCS_FILE, light)