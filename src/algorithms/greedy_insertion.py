import math
from src.algorithms.base import BaseSolver
from src.models.instance import PDPInstance
from src.models.solution import PDPSolution

class GreedyPairInsertionSolver(BaseSolver):
    """
    Thuật toán 1: Greedy Pair Insertion (Heuristic Dựng Lời Giải).
    Chèn tuần tự các cặp Pickup-Delivery của các yêu cầu vào lộ trình của xe
    sao cho tổng khoảng cách tăng thêm là nhỏ nhất và đảm bảo không vi phạm sức chứa (capacity).
    
    Tối ưu:
    - Chi phí tăng thêm tính O(1) bằng công thức detour thay vì tính lại toàn bộ route.
    - old_cost cache ngoài vòng lặp chèn.
    - Dùng index tracking thay vì list.remove().
    """
    def __init__(self, instance: PDPInstance):
        super().__init__(instance)

    def solve(self) -> PDPSolution:
        """
        Thực hiện thuật toán Greedy Pair Best Insertion.
        Trả về đối tượng lời giải hoàn chỉnh (PDPSolution).
        """
        # 1. Khởi tạo lộ trình rỗng cho từng xe (Depot xuất phát -> Depot kết thúc)
        routes = {}
        for vehicle in self.instance.vehicles:
            routes[vehicle.id] = [vehicle.start_depot.id, vehicle.end_depot.id]

        unassigned_requests = list(self.instance.requests.values())
        get_dist = self.instance.get_distance  # Cache method lookup

        # Giới hạn số request tối đa mỗi xe = ceil(tổng request / số xe)
        # Đảm bảo phân bổ đều các request giữa các xe
        num_requests = len(unassigned_requests)
        num_vehicles = len(self.instance.vehicles)
        max_requests_per_vehicle = math.ceil(num_requests / num_vehicles) if num_vehicles > 0 else num_requests

        # Đếm số request hiện tại của mỗi xe (ban đầu = 0)
        vehicle_request_count = {vehicle.id: 0 for vehicle in self.instance.vehicles}

        # Vòng lặp cho đến khi gán hết mọi yêu cầu hoặc không thể chèn thêm
        while unassigned_requests:
            best_cost_increase = float('inf')
            best_req_idx = -1
            best_insertion = None  # Tuple: (vehicle_id, pickup_index, delivery_index)

            # Duyệt qua mọi yêu cầu chưa được gán
            for req_idx, req in enumerate(unassigned_requests):
                p_node = req.pickup_node.id
                d_node = req.delivery_node.id

                # Duyệt qua từng xe
                for vehicle in self.instance.vehicles:
                    v_id = vehicle.id

                    # Bỏ qua xe đã đạt giới hạn số request tối đa
                    if vehicle_request_count[v_id] >= max_requests_per_vehicle:
                        continue

                    route = routes[v_id]
                    route_len = len(route)

                    # Thử chèn pickup tại vị trí p_idx (từ 1 đến len - 1)
                    for p_idx in range(1, route_len):
                        prev_p = route[p_idx - 1]
                        next_p = route[p_idx]

                        # Chi phí detour khi chèn pickup: dist(prev, P) + dist(P, next) - dist(prev, next)
                        delta_p = get_dist(prev_p, p_node) + get_dist(p_node, next_p) - get_dist(prev_p, next_p)

                        # Cắt tỉa sớm: nếu chỉ riêng delta_p đã >= best thì bỏ qua
                        if delta_p >= best_cost_increase:
                            continue

                        # Thử chèn delivery tại vị trí d_idx (phải đứng từ vị trí p_idx trở đi)
                        # Sau khi chèn pickup, route tạm thời thay đổi:
                        # route[:p_idx] + [p_node] + route[p_idx:]
                        # Nên delivery sẽ chèn vào route đã có pickup
                        for d_idx in range(p_idx, route_len):
                            # Xác định các node lân cận của vị trí chèn delivery
                            # Trong route đã chèn pickup:
                            if d_idx == p_idx:
                                # Delivery chèn ngay sau pickup
                                prev_d = p_node
                                next_d = route[p_idx]  # = next_p (node gốc sau p_idx)
                            else:
                                # d_idx > p_idx: delivery chèn vào vị trí route gốc
                                prev_d = route[d_idx - 1]
                                next_d = route[d_idx]

                            # Chi phí detour khi chèn delivery
                            delta_d = get_dist(prev_d, d_node) + get_dist(d_node, next_d) - get_dist(prev_d, next_d)

                            cost_increase = delta_p + delta_d

                            # Cắt tỉa sớm
                            if cost_increase >= best_cost_increase:
                                continue

                            # Kiểm tra tính khả thi tải trọng trên route thử nghiệm
                            test_route = route[:p_idx] + [p_node] + route[p_idx:d_idx] + [d_node] + route[d_idx:]
                            current_load = 0.0
                            feasible = True
                            for nid in test_route:
                                node = self.instance.nodes[nid]
                                current_load += node.demand
                                if current_load > vehicle.capacity or current_load < -1e-8:
                                    feasible = False
                                    break

                            if not feasible:
                                continue

                            # Tìm lượt chèn tối ưu toàn cục
                            best_cost_increase = cost_increase
                            best_req_idx = req_idx
                            best_insertion = (v_id, p_idx, d_idx)

            # 2. Áp dụng lượt chèn tốt nhất tìm được
            if best_req_idx >= 0 and best_insertion is not None:
                v_id, p_idx, d_idx = best_insertion
                best_req = unassigned_requests[best_req_idx]
                route = routes[v_id]

                # Thực hiện chèn thật vào lộ trình của xe
                routes[v_id] = route[:p_idx] + [best_req.pickup_node.id] + route[p_idx:d_idx] + [best_req.delivery_node.id] + route[d_idx:]

                # Cập nhật số request đã gán cho xe
                vehicle_request_count[v_id] += 1

                # Xóa yêu cầu đã được gán bằng index (O(1) swap-and-pop hoặc O(n) pop)
                unassigned_requests.pop(best_req_idx)
            else:
                # Nếu còn yêu cầu nhưng không thể chèn hợp lệ vào bất kỳ vị trí nào
                print(f"[Cảnh báo] Không tìm thấy vị trí chèn hợp lệ cho {len(unassigned_requests)} yêu cầu còn lại do giới hạn tải trọng xe.")
                break

        # Trả về kết quả lời giải hoàn chỉnh
        return PDPSolution(instance=self.instance, routes=routes)
