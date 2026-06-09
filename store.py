"""
store.py — Bộ nhớ dùng chung toàn ứng dụng
- users_store và user_convs được lưu vào file JSON để giữ lại sau khi restart
- documents_store vẫn in-memory (file upload sẽ mất khi restart là bình thường)
"""

import json
from pathlib import Path

# Đường dẫn file lưu trữ
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
CONVS_FILE = DATA_DIR / "conversations.json"

# Helpers đọc/ghi JSON

def _load(path: Path) -> dict:
    """Đọc file JSON, trả về dict rỗng nếu file chưa tồn tại."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save(path: Path, data: dict) -> None:
    """Ghi dict ra file JSON."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# Stores

# doc_id -> { id, name, ext, size_human, chunks, word_count, ... }
# Không persist vì file upload cũng mất khi restart
documents_store: dict[str, dict] = {}

# username -> { id, username, display_name, password_hash, created_at }
users_store: dict[str, dict] = _load(USERS_FILE)

# user_id -> { conv_id -> { id, title, messages, created_at, updated_at } }
user_convs: dict[str, dict] = _load(CONVS_FILE)

# Hàm lưu (gọi sau mỗi thao tác thay đổi) 

def save_users() -> None:
    """Lưu users_store xuống file."""
    _save(USERS_FILE, users_store)

def save_convs() -> None:
    """Lưu user_convs xuống file."""
    _save(CONVS_FILE, user_convs)