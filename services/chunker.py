"""
services/chunker.py — Chia nhỏ văn bản và truy xuất đoạn liên quan (RAG cơ bản)
Thay retrieve_chunks bằng ChromaDB + embeddings để chính xác hơn.
"""


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """
    Chia văn bản thành các đoạn nhỏ theo từ (sliding window).

    Args:
        text:       Văn bản đầu vào.
        chunk_size: Số ký tự tối đa mỗi đoạn.
        overlap:    Số ký tự overlap giữa các đoạn liên tiếp.

    Returns:
        Danh sách các đoạn văn bản.
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


def retrieve_chunks(query: str, chunks: list[str], top_k: int = 5) -> list[str]:
    """
    Tìm các đoạn liên quan nhất bằng keyword matching.

    Args:
        query:  Câu hỏi của người dùng.
        chunks: Danh sách đoạn văn bản đã chia.
        top_k:  Số đoạn trả về.

    Returns:
        top_k đoạn có điểm số cao nhất.
    """
    if not chunks:
        return []

    q_words = set(query.lower().split())
    scored  = sorted(
        [(len(q_words & set(c.lower().split())), c) for c in chunks],
        reverse=True,
    )
    return [c for _, c in scored[:top_k]]