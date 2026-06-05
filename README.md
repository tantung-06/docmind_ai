# DocMind AI — Chatbot Hỏi Đáp Tài Liệu

Hỏi đáp thông minh từ PDF, DOCX, TXT — chạy hoàn toàn cục bộ qua **Ollama + Qwen2.5:7b**

## Tính năng

- **Upload** PDF, DOCX, TXT (tối đa 50MB mỗi file)
- **Chat streaming** — câu trả lời hiện từng từ tức thì
- **RAG cơ bản** — tự động truy xuất đoạn văn liên quan trước khi trả lời
- **100% cục bộ** — dữ liệu không rời khỏi máy bạn
- **Dashboard** — thống kê tài liệu và trạng thái hệ thống
- **Multi-doc** — chat với nhiều tài liệu cùng lúc

## Cài đặt

### 1. Cài Ollama & kéo model

# Cài Ollama (https://ollama.com)

# Kéo model Qwen2.5:7b (khoảng 4.7GB)

ollama pull qwen2.5:7b

# Khởi động Ollama server (nếu chưa chạy)

ollama serve

### 2. Cài Python dependencies

cd docmind_ai
pip install -r requirements.txt

Cần Python 3.10+

### 3. Chạy ứng dụng

python app.py

Mở trình duyệt tại: **http://localhost:5000**

## Biến môi trường

| Biến           | Mặc định                 | Mô tả             |
| -------------- | ------------------------ | ----------------- |
| `OLLAMA_HOST`  | `http://localhost:11434` | URL Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:7b`             | Model sử dụng     |

# Ví dụ dùng model khác

OLLAMA_MODEL=llama3.2:3b python app.py

## Cấu trúc thư mục

docmind_ai/
├── app.py # Flask app chính
├── requirements.txt
├── uploads/ # File tải lên (tự tạo)
├── templates/
│ ├── index.html # Trang chủ
│ ├── chat.html # Trang chat
│ └── dashboard.html # Dashboard
└── static/
├── css/style.css # Giao diện
└── js/
├── app.js # Logic trang chủ
├── chat.js # Logic chat
└── dashboard.js # Logic dashboard

## API Endpoints

| Method | Endpoint                      | Mô tả                 |
| ------ | ----------------------------- | --------------------- |
| GET    | `/api/health`                 | Kiểm tra Ollama & app |
| POST   | `/api/upload`                 | Upload tài liệu       |
| GET    | `/api/documents`              | Danh sách tài liệu    |
| DELETE | `/api/documents/<id>`         | Xóa tài liệu          |
| POST   | `/api/chat`                   | Chat (SSE streaming)  |
| GET    | `/api/chat/history/<session>` | Lịch sử chat          |
| DELETE | `/api/chat/clear/<session>`   | Xóa lịch sử           |

## Ghi chú

- Lưu trữ in-memory — dữ liệu mất khi restart. Để persistence, tích hợp SQLite.
- RAG dùng keyword matching — để độ chính xác cao hơn, thay bằng ChromaDB + embeddings.
- Chunk size mặc định: 800 ký tự, overlap 100 ký tự.
