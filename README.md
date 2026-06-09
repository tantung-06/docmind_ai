# DocMind AI — Chatbot Hỏi Đáp Tài Liệu

Hỏi đáp thông minh từ PDF, DOCX, TXT — chạy hoàn toàn cục bộ qua **Ollama + Qwen2.5:7b**

## Tính năng

- **Upload** PDF, DOCX, TXT (tối đa 50MB mỗi file)
- **Chat streaming** — câu trả lời hiện từng từ tức thì
- **RAG cơ bản** — tự động truy xuất đoạn văn liên quan trước khi trả lời
- **Đăng ký / Đăng nhập** — lưu lịch sử chat theo tài khoản
- **Lịch sử hội thoại** — nhiều phiên chat riêng biệt, đổi tên, xóa từng phiên
- **Chế độ khách** — dùng không cần đăng nhập, lịch sử không được lưu
- **Dashboard** — thống kê tài liệu và trạng thái hệ thống
- **Multi-doc** — chat với nhiều tài liệu cùng lúc
- **100% cục bộ** — dữ liệu không rời khỏi máy bạn

## Cài đặt

## 1. Cài Ollama & kéo model

### Cài Ollama

https://ollama.com

### Kéo model Qwen2.5:7b (khoảng 4.7GB)

ollama pull qwen2.5:7b

### Khởi động Ollama server (nếu chưa chạy)

ollama serve

## 2. Cài Python dependencies

cd docmind_ai
pip install -r requirements.txt

> Yêu cầu Python 3.11+

## 3. Chạy ứng dụng

python app.py

Mở trình duyệt tại: **http://localhost:5000**

### Biến môi trường

| Biến           | Mặc định                 | Mô tả                     |
| -------------- | ------------------------ | ------------------------- |
| `OLLAMA_HOST`  | `http://localhost:11434` | URL Ollama server         |
| `OLLAMA_MODEL` | `qwen2.5:7b`             | Model sử dụng             |
| `SECRET_KEY`   | Tự sinh ngẫu nhiên       | Khóa mã hóa Flask session |

### Ví dụ dùng model khác

OLLAMA_MODEL=llama3.2:3b python app.py

## Cấu trúc thư mục

```
docmind_ai/
│
├── routes/                   # Các nhóm API endpoint
│   ├── auth.py               # Đăng ký / Đăng nhập / Đăng xuất
│   ├── chat.py               # Gửi tin nhắn + quản lý phiên hội thoại
│   ├── documents.py          # Upload / Xem / Xóa tài liệu
│   └── health.py             # Kiểm tra trạng thái Ollama
│
├── services/                 # Logic xử lý nghiệp vụ
│   ├── chunker.py            # Chia văn bản thành đoạn nhỏ + tìm đoạn liên quan
│   ├── extractor.py          # Đọc nội dung từ PDF / DOCX / TXT
│   └── ollama.py             # Gọi Ollama API để sinh câu trả lời
│
├── static/
│   ├── css/
│   │   └── style.css         # Toàn bộ giao diện
│   └── js/
│       ├── app.js            # Logic trang chủ
│       ├── auth.js           # Modal đăng nhập + navbar user
│       ├── chat.js           # Logic trang chat
│       └── dashboard.js      # Logic trang dashboard
│
├── templates/
│   ├── index.html            # Trang chủ
│   ├── chat.html             # Trang chat
│   └── dashboard.html        # Trang thống kê
│
├── data/                     # Dữ liệu người dùng (tự tạo)
│   ├── users.json            # Tài khoản đăng ký
│   ├── conversations.json    # Lịch sử hội thoại
│   └── documents.json        # Metadata tài liệu đã tải lên
│
├── uploads/                  # File tải lên (tự tạo)
│
├── app.py                    # Entry point — khởi động Flask
├── config.py                 # Biến cấu hình
├── store.py                  # Đọc/ghi dữ liệu (user, tài liệu, lịch sử)
├── .gitignore                # Bỏ qua __pycache__, data/, uploads/
├── README.md
└── requirements.txt
```

## API Endpoints

### Auth

| Method | Endpoint        | Mô tả                        |
| ------ | --------------- | ---------------------------- |
| POST   | `/api/register` | Đăng ký tài khoản            |
| POST   | `/api/login`    | Đăng nhập                    |
| POST   | `/api/logout`   | Đăng xuất                    |
| GET    | `/api/me`       | Thông tin tài khoản hiện tại |

### Tài liệu

| Method | Endpoint              | Mô tả              |
| ------ | --------------------- | ------------------ |
| POST   | `/api/upload`         | Upload tài liệu    |
| GET    | `/api/documents`      | Danh sách tài liệu |
| DELETE | `/api/documents/<id>` | Xóa tài liệu       |

### Chat & Lịch sử

| Method | Endpoint                  | Mô tả                        |
| ------ | ------------------------- | ---------------------------- |
| POST   | `/api/chat`               | Gửi tin nhắn (SSE streaming) |
| GET    | `/api/conversations`      | Danh sách phiên hội thoại    |
| POST   | `/api/conversations`      | Tạo phiên mới                |
| GET    | `/api/conversations/<id>` | Lấy tin nhắn của một phiên   |
| PATCH  | `/api/conversations/<id>` | Đổi tên phiên                |
| DELETE | `/api/conversations/<id>` | Xóa phiên                    |

### Hệ thống

| Method | Endpoint      | Mô tả                 |
| ------ | ------------- | --------------------- |
| GET    | `/api/health` | Kiểm tra Ollama & app |

## Ghi chú

- **Lưu trữ in-memory** — dữ liệu mất khi restart. Để persistence, tích hợp SQLite.
- **RAG dùng keyword matching** — để chính xác hơn, thay bằng ChromaDB + embeddings.
- **Chunk size** mặc định: 1000 ký tự, overlap 100 ký tự.
- **Mật khẩu** được hash SHA-256 trước khi lưu.
