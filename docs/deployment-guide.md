# LLM Message Normalization Adapter - Deployment Guide
# Hướng Dẫn Triển Khai Adapter Chuẩn Hóa Tin Nhắn LLM

This guide provides instructions for deploying and configuring the LLM Message Normalization Adapter for `llama.cpp`.

*Tài liệu này cung cấp hướng dẫn triển khai và cấu hình Adapter chuẩn hóa tin nhắn cho `llama.cpp`.*

---

## 1. Prerequisites / Điều Kiện Tiên Quyết

- **Python**: 3.11 or higher / 3.11 trở lên.
- **Upstream Server**: A running `llama.cpp` server with OpenAI-compatible API enabled (`--api` or `-cb`).
- **Upstream Server**: Máy chủ `llama.cpp` đang chạy với API tương thích OpenAI đã được bật.

---

## 2. Installation / Cài Đặt

### Step 1: Clone the repository / Bước 1: Sao chép mã nguồn
```bash
git clone <repository-url>
cd llamacpp-llm-adapter-api
```

### Step 2: Create a virtual environment / Bước 2: Tạo môi trường ảo
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install dependencies / Bước 3: Cài đặt thư viện
```bash
pip install -r requirements.txt
```

---

## 3. Configuration / Cấu Hình

The adapter uses environment variables for configuration. You can set these in a `.env` file in the project root.

*Adapter sử dụng các biến môi trường để cấu hình. Bạn có thể thiết lập chúng trong tệp `.env` tại thư mục gốc.*

| Variable / Biến | Description / Mô tả | Default / Mặc định |
| :--- | :--- | :--- |
| `UPSTREAM_BASE_URL` | URL of the `llama.cpp` server / URL của máy chủ `llama.cpp` | `http://127.0.0.1:8080` |
| `FAST_MODEL` | Model id used for FAST routing / Model id dùng cho tuyến FAST | `gemma-3-4b` |
| `DEEP_MODEL` | Model id used for DEEP routing / Model id dùng cho tuyến DEEP | `qwen3.5-2B` |
| `ENABLE_ROUTING` | Enable rule-based FAST/DEEP routing / Bật định tuyến FAST/DEEP theo luật | `true` |
| `ENABLE_DEBUG_ENDPOINTS` | Enable `/v1/chat/completions:normalize` / Bật endpoint debug | `true` |
| `LOG_NORMALIZED_REQUESTS` | Log the content of transformed messages / Ghi log tin nhắn đã chuẩn hóa | `true` |

---

## 4. Running the Application / Chạy Ứng Dụng

### Development / Phát triển
```bash
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

### Production / Sản xuất
```bash
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker / Docker
```bash
docker build -t llamacpp-llm-adapter-api .
docker run --rm -p 8000:8000 --env-file .env llamacpp-llm-adapter-api
```

### Docker Compose / Docker Compose
```bash
docker compose up --build
```

The repository includes example deployment files:

- [Dockerfile](/home/cuongpt/Workspaces/llamacpp-llm-adapter-api/Dockerfile)
- [docker-compose.yaml](/home/cuongpt/Workspaces/llamacpp-llm-adapter-api/docker-compose.yaml)

If `llama.cpp` runs on the host machine instead of another container, set:

```bash
UPSTREAM_BASE_URL=http://host.docker.internal:8080
```

---

## 5. Verification / Kiểm Tra

### Check Health / Kiểm tra liveness
```bash
curl http://localhost:8000/healthz
# Expected: {"status": "ok"}
```

### Check Upstream Connectivity / Kiểm tra kết nối llama.cpp
```bash
curl http://localhost:8000/readyz
# Expected: {"status": "ready", "upstream": "ok"}
```

---

## 6. Usage with Clients / Sử dụng với Client

Point your OpenAI-compatible client (e.g., ZeroClaw, LangChain) to the adapter URL instead of the direct `llama.cpp` URL.

*Trỏ client tương thích OpenAI của bạn tới URL của adapter thay vì URL trực tiếp của `llama.cpp`.*

- **Base URL**: `http://localhost:8000/v1`
- **Model**: Use any model prefix like `gemma-` to trigger strict normalization.

---

## 7. Troubleshooting / Xử Lý Sự Cố

- **422 Unprocessable Entity**: The conversation structure could not be normalized to satisfy the model's strict requirements (e.g., empty conversation or invalid roles).
- **502 Bad Gateway**: The adapter cannot reach the `UPSTREAM_BASE_URL`. Ensure `llama.cpp` is running and accessible.

---

*For further support, please check the internal documentation in `README.md`.*
*Để được hỗ trợ thêm, vui lòng kiểm tra tài liệu `README.md`.*
