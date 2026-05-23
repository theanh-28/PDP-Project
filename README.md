# PDP Project

Một dự án Python rỗng đã được khởi tạo thành công.

## Cấu trúc thư mục hiện tại

```text
PDP-Project/
├── .gitignore         # File cấu hình Git để bỏ qua các file không cần thiết
├── README.md          # File hướng dẫn/giới thiệu dự án (file này)
├── requirements.txt   # File chứa các thư viện phụ thuộc (dependencies)
└── main.py            # File chạy chính của chương trình (Hello World)
```

## Hướng dẫn cài đặt & Chạy dự án

### 1. Khởi tạo Virtual Environment (Môi trường ảo)

Khuyến nghị sử dụng môi trường ảo để quản lý các gói thư viện riêng biệt cho dự án:

```bash
# Tạo môi trường ảo có tên là .venv
python -m venv .venv
```

### 2. Kích hoạt môi trường ảo

- **Trên Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Trên Windows (CMD):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Trên macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Cài đặt các thư viện phụ thuộc

Khi bạn thêm các thư viện vào `requirements.txt`, cài đặt chúng bằng lệnh:

```bash
pip install -r requirements.txt
```

### 4. Chạy dự án

Chạy file chạy chính `main.py`:

```bash
python main.py
```
