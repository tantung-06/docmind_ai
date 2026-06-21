"""
services/chunker.py — Chia nhỏ văn bản và truy xuất đoạn liên quan (RAG)
Keyword matching cải tiến: phrase bonus + position bonus.
"""

import re


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """
    Chia văn bản thành các đoạn nhỏ theo từ (sliding window).
    """
    if not text.strip():
        return []

    words = text.split()
    chunks, buf, buf_len = [], [], 0

    for word in words:
        buf.append(word)
        buf_len += len(word) + 1
        if buf_len >= chunk_size:
            chunks.append(" ".join(buf))
            buf     = buf[-overlap // 6:] if overlap else []
            buf_len = sum(len(w) + 1 for w in buf)

    if buf:
        chunks.append(" ".join(buf))

    return chunks


def _normalize(text: str) -> str:
    """Lowercase, bỏ dấu câu thừa."""
    return re.sub(r'[^\w\s]', ' ', text.lower())


def retrieve_chunks(query: str, chunks: list[str], top_k: int = 6) -> list[str]:
    """
    Keyword matching cải tiến với 3 tầng điểm:

    1. Keyword score  — số từ của query xuất hiện trong chunk.
    2. Phrase bonus   — cộng thêm nếu chunk chứa cụm từ nguyên vẹn từ query.
    3. Position bonus — chunk đứng đầu tài liệu được ưu tiên nhẹ khi score bằng nhau.
    """
    if not chunks:
        return []

    q_norm   = _normalize(query)
    q_words  = set(q_norm.split())
    q_phrase = q_norm.strip()   # toàn bộ câu hỏi sau normalize

    if not q_words:
        return chunks[:top_k]

    scored = []
    for i, chunk in enumerate(chunks):
        c_norm  = _normalize(chunk)
        c_words = set(c_norm.split())

        # 1. Keyword score
        kw_score = len(q_words & c_words)

        # 2. Phrase bonus — chunk chứa cụm từ nguyên vẹn
        phrase_bonus = 2 if q_phrase in c_norm else 0

        # Thử từng cụm con 2-3 từ liên tiếp trong query
        q_tokens = q_norm.split()
        for size in (3, 2):
            for j in range(len(q_tokens) - size + 1):
                sub = " ".join(q_tokens[j:j+size])
                if sub in c_norm:
                    phrase_bonus += 1

        # 3. Position bonus - chunk ở đầu tài liệu ưu tiên nhẹ
        position_bonus = 1 / (i + 1)

        total = kw_score + phrase_bonus + position_bonus
        scored.append((total, i, chunk))

    scored.sort(key=lambda x: (-x[0], x[1]))  # sort by score desc, index asc

    # Nếu tất cả score = 0, trả về chunk đầu
    if scored[0][0] == 0:
        return chunks[:top_k]

    return [c for _, _, c in scored[:top_k]]