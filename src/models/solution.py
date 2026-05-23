from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from .instance import PDPInstance
from .node import NodeType
from .vehicle import Vehicle

@dataclass
class PDPSolution:
    """
    Đại diện cho một lời giải của bài toán PDP.
    """
    instance: PDPInstance
    # Lộ trình của từng xe: vehicle_id -> List[node_id]
    routes: Dict[int, List[int]] = field(default_factory=dict)
    
    def calculate_total_cost(self) -> float:
        """
        Tính toán tổng khoảng cách di chuyển của toàn bộ các xe.
        """
        total_dist = 0.0
        for vehicle_id, route in self.routes.items():
            if not route or len(route) < 2:
                continue
            for i in range(len(route) - 1):
                total_dist += self.instance.get_distance(route[i], route[i+1])
        return total_dist

    def check_feasibility(self) -> Tuple[bool, List[str]]:
        """
        Kiểm tra tính hợp lệ của lời giải (Không còn Time Window):
        1. Ràng buộc Ghép cặp (Pairing): Pickup và Delivery của cùng một request phải trên cùng một xe.
        2. Ràng buộc Thứ tự (Precedence): Pickup phải thăm trước Delivery.
        3. Ràng buộc Tải trọng (Capacity): Tải trọng không vượt quá giới hạn xe tại mọi điểm.
        4. Điểm xuất phát/kết thúc: Đúng Depot của xe.
        """
        errors = []
        visited_pickups: Dict[int, int] = {}  # request_id -> vehicle_id
        visited_deliveries: Dict[int, int] = {}  # request_id -> vehicle_id

        # Ánh xạ node_id -> Request
        node_to_req = {}
        for req_id, req in self.instance.requests.items():
            node_to_req[req.pickup_node.id] = req
            node_to_req[req.delivery_node.id] = req

        # Ánh xạ vehicle_id -> Vehicle
        id_to_vehicle = {v.id: v for v in self.instance.vehicles}

        for vehicle_id, route in self.routes.items():
            if not route:
                continue
            
            vehicle = id_to_vehicle.get(vehicle_id)
            if not vehicle:
                errors.append(f"Không tìm thấy xe ID={vehicle_id} trong Instance.")
                continue

            # Kiểm tra điểm xuất phát/kết thúc depot
            if route[0] != vehicle.start_depot.id:
                errors.append(f"Xe {vehicle_id}: Bắt đầu tại nút {route[0]} thay vì Depot {vehicle.start_depot.id}.")
            if route[-1] != vehicle.end_depot.id:
                errors.append(f"Xe {vehicle_id}: Kết thúc tại nút {route[-1]} thay vì Depot {vehicle.end_depot.id}.")

            current_load = 0.0

            for idx, node_id in enumerate(route):
                node = self.instance.nodes.get(node_id)
                if not node:
                    errors.append(f"Xe {vehicle_id}: Ghé thăm nút ID={node_id} không tồn tại.")
                    continue

                # Kiểm tra Tải trọng (Capacity)
                current_load += node.demand
                if current_load > vehicle.capacity:
                    errors.append(f"Xe {vehicle_id}: Vượt quá tải trọng tại nút {node_id}. Hiện tại: {current_load}, Sức chứa: {vehicle.capacity}.")
                if current_load < 0:
                    errors.append(f"Xe {vehicle_id}: Tải trọng âm ({current_load}) tại nút {node_id}.")

                # Phân loại và kiểm tra Pickup/Delivery
                if node.node_type == NodeType.PICKUP:
                    req = node_to_req.get(node_id)
                    if req:
                        visited_pickups[req.id] = vehicle_id
                elif node.node_type == NodeType.DELIVERY:
                    req = node_to_req.get(node_id)
                    if req:
                        visited_deliveries[req.id] = vehicle_id
                        # Kiểm tra Thứ tự (Precedence)
                        if req.id not in visited_pickups or visited_pickups[req.id] != vehicle_id:
                            errors.append(f"Yêu cầu {req.id}: Điểm giao hàng {node_id} được thăm nhưng điểm lấy hàng tương ứng chưa được xe {vehicle_id} thăm.")
                        else:
                            p_idx = route.index(req.pickup_node.id)
                            d_idx = idx
                            if p_idx >= d_idx:
                                errors.append(f"Yêu cầu {req.id}: Điểm lấy hàng {req.pickup_node.id} nằm sau điểm giao hàng {node_id} trên xe {vehicle_id}.")

        # Kiểm tra Ghép cặp (Pairing)
        for req_id in self.instance.requests.keys():
            p_veh = visited_pickups.get(req_id)
            d_veh = visited_deliveries.get(req_id)
            if p_veh is not None or d_veh is not None:
                if p_veh != d_veh:
                    errors.append(f"Yêu cầu {req_id}: Lấy bởi xe {p_veh} nhưng giao bởi xe {d_veh} (Vi phạm ràng buộc pairing).")

        is_valid = len(errors) == 0
        return is_valid, errors

    def __repr__(self) -> str:
        feasible, _ = self.check_feasibility()
        return f"PDPSolution(Feasible={feasible}, TotalCost={self.calculate_total_cost():.2f})"
