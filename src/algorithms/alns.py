import copy
import random
from src.algorithms.base import BaseSolver
from src.models.instance import PDPInstance
from src.models.solution import PDPSolution

class ALNSSolver(BaseSolver):
    """
    Thuật toán 3: Adaptive Large Neighborhood Search (ALNS - Giải thuật Metaheuristic).
    Sử dụng cơ chế phá hủy (Destroy) và tái thiết (Repair) thích nghi để liên tục tìm lời giải tối ưu.
    """
    def __init__(self, instance: PDPInstance, 
                 initial_solution: PDPSolution = None, 
                 iterations: int = 100, 
                 destroy_rate: float = 0.2):
        super().__init__(instance)
        self.initial_solution = initial_solution
        self.iterations = iterations
        self.destroy_rate = destroy_rate
        
        # Đăng ký danh sách các toán tử phá hủy và tái thiết
        self.destroy_operators = [self._random_destroy, self._worst_destroy]
        self.repair_operators = [self._greedy_repair, self._regret_2_repair]
        
        # Khởi tạo trọng số thích nghi ban đầu bằng nhau
        self.destroy_weights = [1.0] * len(self.destroy_operators)
        self.repair_weights = [1.0] * len(self.repair_operators)

    def solve(self) -> PDPSolution:
        """
        Khung xương chạy chính của giải thuật ALNS.
        """
        if self.initial_solution is None:
            from src.algorithms.greedy_insertion import GreedyPairInsertionSolver
            greedy_solver = GreedyPairInsertionSolver(self.instance)
            current_sol = greedy_solver.solve()
        else:
            current_sol = copy.deepcopy(self.initial_solution)

        best_sol = copy.deepcopy(current_sol)
        
        # Xác định số lượng request bị loại bỏ mỗi vòng lặp
        n_remove = max(1, int(len(self.instance.requests) * self.destroy_rate))

        # =====================================================================
        # TODO: VIẾT VÒNG LẶP ALNS CỦA BẠN TẠI ĐÂY:
        #
        # Ý tưởng triển khai:
        # Lặp qua số lượng iterations:
        #   1. Sử dụng Roulette Wheel Selection chọn 1 toán tử Destroy và 1 toán tử Repair dựa trên trọng số.
        #   2. Gọi toán tử Destroy: destroyed_sol, removed_reqs = destroy_op(current_sol, n_remove)
        #   3. Gọi toán tử Repair: candidate_sol = repair_op(destroyed_sol, removed_reqs)
        #   4. Kiểm tra hợp lệ candidate_sol.check_feasibility()
        #   5. Đánh giá chi phí và chấp nhận lời giải mới (ví dụ: dùng tiêu chí Simulated Annealing hoặc Hill Climbing).
        #   6. Cập nhật điểm số/trọng số thích nghi của các toán tử dựa trên hiệu năng thực tế.
        # =====================================================================

        return best_sol

    # --- TOÁN TỬ PHÁ HỦY KHUNG XƯƠNG (DESTROY SKELETONS) ---

    def _random_destroy(self, solution: PDPSolution, q: int) -> tuple[PDPSolution, list[int]]:
        """
        Toán tử Phá hủy Ngẫu nhiên: Chọn ngẫu nhiên q yêu cầu và gỡ chúng ra khỏi lộ trình các xe.
        """
        destroyed = copy.deepcopy(solution)
        removed_req_ids = []

        # =====================================================================
        # TODO: VIẾT LOGIC PHÁ HỦY NGẪU NHIÊN:
        # 1. Lấy ngẫu nhiên q ID yêu cầu từ danh sách self.instance.requests.keys()
        # 2. Với mỗi ID chọn được: Xóa các node tương ứng (pickup & delivery) khỏi routes của các xe.
        # 3. Thêm ID vào danh sách removed_req_ids.
        # =====================================================================

        return destroyed, removed_req_ids

    def _worst_destroy(self, solution: PDPSolution, q: int) -> tuple[PDPSolution, list[int]]:
        """
        Toán tử Phá hủy Tệ nhất: Phá hủy q yêu cầu đóng góp chi phí (khoảng cách) lớn nhất trong lời giải hiện tại.
        """
        destroyed = copy.deepcopy(solution)
        removed_req_ids = []

        # =====================================================================
        # TODO: VIẾT LOGIC PHÁ HỦY TỆ NHẤT:
        # 1. Tính toán mức đóng góp chi phí của từng request:
        #    Đóng góp = [Chi phí Solution gốc] - [Chi phí Solution khi gỡ request đó ra]
        # 2. Sắp xếp các request giảm dần theo mức đóng góp chi phí.
        # 3. Chọn q request tệ nhất ở đầu danh sách để xóa khỏi destroyed.routes.
        # =====================================================================

        return destroyed, removed_req_ids

    # --- TOÁN TỬ TÁI THIẾT KHUNG XƯƠNG (REPAIR SKELETONS) ---

    def _greedy_repair(self, solution: PDPSolution, removed_req_ids: list[int]) -> PDPSolution:
        """
        Toán tử Tái thiết Tham lam: Chèn lại lần lượt từng request bị gỡ vào vị trí tối ưu chi phí nhất.
        """
        reconstructed = copy.deepcopy(solution)

        # =====================================================================
        # TODO: VIẾT LOGIC TÁI THIẾT THAM LAM:
        # Duyệt qua từng req_id trong removed_req_ids:
        #   Tìm xe và vị trí (p_idx, d_idx) chèn tốt nhất sao cho:
        #     - Lời giải sau chèn hợp lệ (check_feasibility() == True).
        #     - Khoảng cách tăng thêm (cost increase) là nhỏ nhất.
        #   Áp dụng thực hiện chèn vào reconstructed.
        # =====================================================================

        return reconstructed

    def _regret_2_repair(self, solution: PDPSolution, removed_req_ids: list[int]) -> PDPSolution:
        """
        Toán tử Tái thiết Regret-2: Chèn yêu cầu có sự chênh lệch lớn nhất giữa vị trí chèn tốt thứ nhất và tốt thứ hai.
        """
        reconstructed = copy.deepcopy(solution)

        # =====================================================================
        # TODO: VIẾT LOGIC TÁI THIẾT REGRET-2:
        # 1. Lập một hàng chờ chứa các request bị loại bỏ.
        # 2. Với mỗi request trong hàng chờ, tính toán chi phí chèn hợp lệ tốt nhất (c1) và tốt thứ nhì (c2) trên các xe.
        # 3. Độ tiếc nuối (Regret) = c2 - c1.
        # 4. Chọn request có Regret lớn nhất để thực hiện chèn trước vào reconstructed.
        # 5. Lặp lại cho đến khi hàng chờ rỗng.
        # =====================================================================

        return reconstructed
