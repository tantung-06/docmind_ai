"""
store.py — Bộ nhớ dùng chung toàn ứng dụng (in-memory)
Thay bằng SQLite / Redis khi cần persistence.
"""

# doc_id -> { id, name, ext, size_human, chunks, word_count, ... }
documents_store: dict[str, dict] = {}

# username -> { id, username, display_name, password_hash, created_at }
users_store: dict[str, dict] = {}

# user_id -> { conv_id -> { id, title, messages, created_at, updated_at } }
user_convs: dict[str, dict] = {}