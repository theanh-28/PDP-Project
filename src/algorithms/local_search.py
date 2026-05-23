import copy
from src.algorithms.base import BaseSolver
from src.models.instance import PDPInstance
from src.models.solution import PDPSolution

class LocalSearchSolver(BaseSolver):
    """
    Thuật toán 2: Local Search (Tìm Kiếm Cục Bộ).
    Nhận lời giải ban đầu và cải tiến thông qua các toán tử lân cận.
    """
    def __init__(self, instance: PDPInstance, initial_solution: PDPSolution = None):
        super().__init__(instance)
        self.initial_solution = initial_solution

    def solve(self) -> PDPSolution:
        """
        Khung xương chạy chính của tìm kiếm cục bộ (Local Search loop).
        Bạn cần gọi và quản lý vòng lặp các toán tử cải tiến tại đây.
        """
        if self.initial_solution is None:
            # Tự tạo lời giải ban đầu nếu chưa được truyền vào
            from src.algorithms.greedy_insertion import GreedyPairInsertionSolver
            greedy_solver = GreedyPairInsertionSolver(self.instance)
            current_sol = greedy_solver.solve()
        else:
            current_sol = copy.deepcopy(self.initial_solution)

        # =====================================================================
        # TODO: VIẾT VÒNG LẶP LOCAL SEARCH CỦA BẠN TẠI ĐÂY:
        #
        # Ý tưởng triển khai:
        # Lặp lại cho đến khi không có toán tử nào tìm thấy lời giải tốt hơn:
        #   1. Thử áp dụng self._apply_2opt(current_sol)
        #   2. Thử áp dụng self._apply_relocate(current_sol)
        #   3. Nếu có cải tiến, cập nhật current_sol và tiếp tục lặp.
        #   4. Nếu không cải tiến (đạt tối ưu cục bộ), dừng vòng lặp.
        # =====================================================================

        return current_sol

    def _apply_2opt(self, solution: PDPSolution) -> tuple[PDPSolution, bool]:
        """
        Toán tử 2-Opt nội bộ tuyến đường (Intra-route 2-Opt).
        Đảo ngược một phân đoạn của lộ trình xe để khử điểm giao cắt chéo.
        
        Trả về: Tuple[PDPSolution_mới, True/False nếu có cải tiến]
        """
        best_sol = copy.deepcopy(solution)
        improved = False

        # =====================================================================
        # TODO: VIẾT TOÁN TỬ 2-OPT CỦA BẠN TẠI ĐÂY:
        #
        # Ý tưởng triển khai:
        # 1. Duyệt qua từng tuyến đường của các xe.
        # 2. Chọn cặp chỉ số i, j (1 <= i < j < len(route)-1).
        # 3. Tạo route mới: route[:i] + route[i:j+1][::-1] + route[j+1:]
        # 4. Kiểm tra tính khả thi bằng test_sol.check_feasibility()
        # 5. Nếu khả thi và chi phí nhỏ hơn best_sol, cập nhật và gán improved = True.
        # =====================================================================

        return best_sol, improved

    def _apply_relocate(self, solution: PDPSolution) -> tuple[PDPSolution, bool]:
        """
        Toán tử Relocate (Di chuyển yêu cầu).
        Chuyển một yêu cầu (pickup và delivery tương ứng) sang vị trí khác hoặc xe khác.
        
        Trả về: Tuple[PDPSolution_mới, True/False nếu có cải tiến]
        """
        best_sol = copy.deepcopy(solution)
        improved = False

        # =====================================================================
        # TODO: VIẾT TOÁN TỬ RELOCATE CỦA BẠN TẠI ĐÂY:
        #
        # Ý tưởng triển khai:
        # 1. Quét qua từng request trong danh sách.
        # 2. Xóa các điểm pickup và delivery của request đó khỏi xe nguồn.
        # 3. Thử chèn cặp điểm này vào tất cả vị trí khả dĩ trên tất cả các xe (xe đích).
        # 4. Dùng check_feasibility() để đảm bảo tính hợp lệ.
        # 5. Lưu lại giải pháp tốt nhất có chi phí nhỏ hơn best_sol.
        # =====================================================================

        return best_sol, improved
