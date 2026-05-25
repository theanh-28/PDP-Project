# PDP-Project: THIẾT KẾ VÀ ĐÁNH GIÁ THUẬT TOÁN GIẢI BÀI TOÁN PICKUP AND DELIVERY PROBLEM (PDP)

Khung chương trình Python chuyên nghiệp giải quyết bài toán giao nhận hàng hóa (**Pickup and Delivery Problem - PDP / PDPTW**). Dự án tích hợp các thuật toán tối ưu hóa chính xác và heuristic hiệu năng cao, được tăng tốc toàn diện bằng **Numba JIT**.

---

## 🚀 Các Giải Thuật Cốt Lõi

*   **Greedy Pair Insertion (`GreedyPairInsertionSolver`):** Thuật toán chèn cặp nhanh chóng kết hợp cân bằng tải trọng công việc ($M_{\max}$) để khởi tạo lời giải ban đầu.
*   **Local Search (`LocalSearchSolver`):** Tối ưu hóa lộ trình từng xe thông qua các phép toán lân cận kinh điển **2-opt** và **Or-opt** (di chuyển phân đoạn 2 hoặc 3 điểm dừng).
*   **ALNS Adaptation (`ALNSSolver`):** Tìm kiếm lân cận lớn thích ứng động với các toán tử phá hủy/tái thiết lộ trình kết hợp Simulated Annealing để tìm nghiệm cận tối ưu.
*   **MILP Solver (`MILPPDPSolver`):** Quy hoạch tuyến tính nguyên hỗn hợp giải bằng bộ giải toán học `CBC` thông qua thư viện `PuLP` để tìm nghiệm tối ưu tuyệt đối (quy mô nhỏ).

---

## 🛠️ Cài Đặt Nhanh

Khuyến nghị sử dụng môi trường ảo Python 3.10+:

```bash
# 1. Tạo môi trường ảo
python -m venv .venv

# 2. Kích hoạt môi trường ảo
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# 3. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

---

## 💻 Hướng Dẫn Vận Hành

*   **Chạy demo kiểm tra nhanh hệ thống:**
    ```bash
    python main.py
    ```
*   **Chạy toàn bộ thực nghiệm đánh giá hiệu năng (tất cả kích thước và thuật toán):**
    ```bash
    python benchmark_all.py
    ```
*   **Chỉ chạy thuật toán Greedy trên toàn bộ dữ liệu (cực nhanh):**
    ```bash
    python benchmark_all.py --algorithms greedy
    ```
*   **Chạy thử nghiệm nhanh (chỉ chạy 1 file đại diện cho mỗi kích thước để test nhanh):**
    ```bash
    python benchmark_all.py --algorithms greedy local_search alns --file-scope sample
    ```

---

## 📊 Kết Quả Thực Nghiệm

Các tệp báo cáo tổng hợp sau khi chạy thực nghiệm sẽ được lưu tự động trong thư mục `results/benchmarks/`:
*   `all_algorithms_benchmark_detail_<timestamp>.csv` (Báo cáo chi tiết từng tệp chạy).
*   `all_algorithms_benchmark_average_<timestamp>.csv` (Báo cáo trung bình dạng số liệu thô).
*   `all_algorithms_benchmark_average_<timestamp>.md` (Báo cáo trung bình dạng bảng Markdown).
