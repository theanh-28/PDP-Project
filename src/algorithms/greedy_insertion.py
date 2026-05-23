from src.algorithms.base import BaseSolver
from src.models.instance import PDPInstance
from src.models.solution import PDPSolution

class GreedyPairInsertionSolver(BaseSolver):
    """
    Thuật toán 1: Greedy Pair Insertion (Heuristic Dựng Lời Giải).
    Chèn tuần tự các cặp Pickup-Delivery vào các lộ trình sao cho chi phí tăng thêm là nhỏ nhất.
    """
    def __init__(self, instance: PDPInstance):
        super().__init__(instance)

    def solve(self) -> PDPSolution:
        """
        Khung xương triển khai giải thuật Greedy Pair Insertion.
        Bạn cần tự lập trình logic chèn cặp Pickup-Delivery vào đây.
        """
        # Khởi tạo lộ trình rỗng cho từng xe (Depot xuất phát -> Depot kết thúc)
        routes = {}
        for vehicle in self.instance.vehicles:
            routes[vehicle.id] = [vehicle.start_depot.id, vehicle.end_depot.id]

        # =====================================================================
        # TODO: VIẾT THUẬT TOÁN GREEDY INSERTION CỦA BẠN TẠI ĐÂY:
        #
        # Ý tưởng triển khai:
        # 1. Lấy danh sách các request chưa được xếp tuyến: list(self.instance.requests.values())
        # 2. Với mỗi request:
        #    a. Thử chèn pickup_node vào tất cả vị trí p_idx (từ 1 đến len(route)-1).
        #    b. Thử chèn delivery_node vào tất cả vị trí d_idx (đứng sau p_idx).
        #    c. Dùng solution.check_feasibility() để kiểm tra ràng buộc (tải trọng, pairing, precedence).
        #    d. Lưu lại lượt chèn hợp lệ có khoảng cách tăng thêm (cost increase) là nhỏ nhất.
        # 3. Cập nhật lượt chèn tốt nhất vào routes và lặp lại cho request tiếp theo.
        # =====================================================================

        return PDPSolution(instance=self.instance, routes=routes)
