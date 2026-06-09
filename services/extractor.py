"""
services/extractor.py — Trích xuất văn bản từ PDF, DOCX, TXT
"""

from pathlib import Path
import fitz                              # PyMuPDF
from docx import Document as DocxDocument


def extract_pdf(path: Path) -> str:
    parts = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            parts.append(page.get_text())
    return "\n\n".join(parts)


def extract_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_txt(path: Path) -> str:
    for enc in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            pass
    return path.read_bytes().decode("utf-8", errors="replace")


def extract_text(path: Path, ext: str) -> str:
    """Tự động chọn extractor theo đuôi file."""
    extractors = {
        "pdf":  extract_pdf,
        "docx": extract_docx,
        "txt":  extract_txt,
    }
    fn = extractors.get(ext)
    if fn is None:
        raise ValueError(f"Định dạng không hỗ trợ: {ext}")
    return fn(path)