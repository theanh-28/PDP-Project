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
        Kiểm tra tính hợp lệ của lời giải PDP theo đúng các ràng buộc của mô hình Branch-and-Bound:
        - (C1) Mỗi yêu cầu giao nhận (Pickup & Delivery) phải được phục vụ đúng 1 lần bởi đúng 1 xe.
        - (C2)/(C3) Xe chỉ có thể xuất phát từ Start Depot và quay về End Depot (tối đa 1 lần).
        - (C4) Bảo toàn luồng di chuyển (Flow Conservation - tự động thỏa mãn bởi cấu trúc chuỗi route).
        - (C5) Ghép cặp (Pairing): Pickup và Delivery của cùng một request phải trên cùng một xe.
        - (C6) Thứ tự (Precedence): Điểm lấy hàng (Pickup) phải được thăm trước điểm giao hàng (Delivery).
        - (C7)/(C8) Tải trọng xe tại mọi thời điểm phải trong khoảng [0, Capacity] và trả về đúng 0.0 tại Depot.
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
            if not route or len(route) < 2:
                continue
            
            vehicle = id_to_vehicle.get(vehicle_id)
            if not vehicle:
                errors.append(f"Không tìm thấy xe ID={vehicle_id} trong Instance.")
                continue

            # (C2)/(C3) Kiểm tra điểm xuất phát/kết thúc depot
            if route[0] != vehicle.start_depot.id:
                errors.append(f"Xe {vehicle_id}: Bắt đầu tại nút {route[0]} thay vì Depot {vehicle.start_depot.id} (Vi phạm C2).")
            if route[-1] != vehicle.end_depot.id:
                errors.append(f"Xe {vehicle_id}: Kết thúc tại nút {route[-1]} thay vì Depot {vehicle.end_depot.id} (Vi phạm C3).")

            current_load = 0.0
            pickup_positions = {}  # req_id -> index trong route (dùng cho kiểm tra C6)

            for idx, node_id in enumerate(route):
                node = self.instance.nodes.get(node_id)
                if not node:
                    errors.append(f"Xe {vehicle_id}: Ghé thăm nút ID={node_id} không tồn tại.")
                    continue

                # (C7)/(C8) Kiểm tra Tải trọng (Capacity) tại từng nút
                current_load += node.demand
                if current_load > vehicle.capacity:
                    errors.append(f"Xe {vehicle_id}: Vượt quá tải trọng tại nút {node_id}. Hiện tại: {current_load}, Sức chứa tối đa: {vehicle.capacity} (Vi phạm C8).")
                if current_load < -1e-8:
                    errors.append(f"Xe {vehicle_id}: Tải trọng âm ({current_load}) tại nút {node_id} (Vi phạm C8).")

                # Kiểm tra ghé thăm nhiều lần và lập bản đồ gán xe
                if node.node_type == NodeType.PICKUP:
                    req = node_to_req.get(node_id)
                    if req:
                        if req.id in visited_pickups:
                            errors.append(f"Yêu cầu {req.id}: Điểm lấy hàng {node_id} bị ghé thăm nhiều lần (Đã ghé bởi xe {visited_pickups[req.id]} và nay bởi xe {vehicle_id}) (Vi phạm C1).")
                        visited_pickups[req.id] = vehicle_id
                        pickup_positions[req.id] = idx  # Ghi nhận vị trí pickup
                elif node.node_type == NodeType.DELIVERY:
                    req = node_to_req.get(node_id)
                    if req:
                        if req.id in visited_deliveries:
                            errors.append(f"Yêu cầu {req.id}: Điểm giao hàng {node_id} bị ghé thăm nhiều lần (Đã ghé bởi xe {visited_deliveries[req.id]} và nay bởi xe {vehicle_id}) (Vi phạm C1).")
                        visited_deliveries[req.id] = vehicle_id
                        
                        # (C6) Kiểm tra Thứ tự (Precedence)
                        if req.id not in visited_pickups or visited_pickups[req.id] != vehicle_id:
                            errors.append(f"Yêu cầu {req.id}: Điểm giao hàng {node_id} được thăm nhưng điểm lấy hàng tương ứng chưa được xe {vehicle_id} thăm (Vi phạm C6).")
                        else:
                            p_idx = pickup_positions.get(req.id)
                            if p_idx is not None and p_idx >= idx:
                                errors.append(f"Yêu cầu {req.id}: Điểm lấy hàng {req.pickup_node.id} nằm sau điểm giao hàng {node_id} trên xe {vehicle_id} (Vi phạm C6).")

            # (C7) Đảm bảo xe rỗng khi quay về Depot cuối tuyến
            if abs(current_load) > 1e-8:
                errors.append(f"Xe {vehicle_id}: Tải trọng cuối tuyến khi quay về depot là {current_load} thay vì 0.0 (Vi phạm C7).")

        # (C1) Kiểm tra từng yêu cầu phải được thăm đầy đủ đúng 1 lần
        for req_id in self.instance.requests.keys():
            p_veh = visited_pickups.get(req_id)
            d_veh = visited_deliveries.get(req_id)
            
            if p_veh is None:
                errors.append(f"Yêu cầu {req_id}: Chưa được điểm lấy hàng (Pickup) phục vụ (Vi phạm C1).")
            if d_veh is None:
                errors.append(f"Yêu cầu {req_id}: Chưa được điểm giao hàng (Delivery) phục vụ (Vi phạm C1).")
            
            # (C5) Kiểm tra Ghép cặp (Pairing)
            if p_veh is not None and d_veh is not None:
                if p_veh != d_veh:
                    errors.append(f"Yêu cầu {req_id}: Điểm lấy hàng phục vụ bởi xe {p_veh} nhưng giao bởi xe {d_veh} (Vi phạm C5).")

        is_valid = len(errors) == 0
        return is_valid, errors

    def __repr__(self) -> str:
        return f"PDPSolution(Routes={len(self.routes)}, TotalCost={self.calculate_total_cost():.2f})"
