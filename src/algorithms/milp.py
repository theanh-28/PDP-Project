from src.algorithms.base import BaseSolver
from src.models.instance import PDPInstance
from src.models.solution import PDPSolution

class MILPPDPSolver(BaseSolver):
    """
    Thuật toán 4: Mixed-Integer Linear Programming (MILP Solver - Quy hoạch tuyến tính nguyên hỗn hợp).
    Dùng các mô hình toán học giải tối ưu toàn cục (ví dụ sử dụng PuLP, Gurobi, MIP...).
    """
    def __init__(self, instance: PDPInstance, time_limit: int = 30):
        super().__init__(instance)
        self.time_limit = time_limit

    def solve(self) -> PDPSolution:
        """
        Khung xương mô hình MILP cho bài toán PDP.
        Bạn có thể tự lập trình mô hình hóa toán học các ràng buộc (Flow conservation, capacity, precedence, pairing) tại đây.
        """
        # Khởi tạo lộ trình mặc định rỗng
        routes = {}
        for vehicle in self.instance.vehicles:
            routes[vehicle.id] = [vehicle.start_depot.id, vehicle.end_depot.id]

        # =====================================================================
        # TODO: THIẾT LẬP MÔ HÌNH TOÁN HỌC MILP CỦA BẠN TẠI ĐÂY:
        #
        # Các gợi ý thiết lập (sử dụng thư viện PuLP làm ví dụ):
        # 1. Khai báo biến nhị phân: x_ijk = 1 nếu xe k đi từ nút i đến nút j.
        # 2. Khai báo biến liên tục: L_i = tải trọng xe tại nút i.
        # 3. Hàm mục tiêu: Tối thiểu hóa tổng quãng đường di chuyển.
        # 4. Thiết lập các ràng buộc:
        #    - Mỗi điểm lấy hàng (pickup) được phục vụ đúng 1 lần bởi đúng 1 xe.
        #    - Bảo toàn dòng tại các nút trung gian (Tổng vào = Tổng ra).
        #    - Điểm pickup và delivery tương ứng phải cùng được phục vụ bởi cùng một xe k.
        #    - Ràng buộc thứ tự precedence: Điểm pickup phải phục vụ trước điểm delivery tương ứng.
        #    - Ràng buộc tải trọng của xe tại mỗi nút không vượt quá capacity của xe đó.
        # =====================================================================

        return PDPSolution(instance=self.instance, routes=routes)
