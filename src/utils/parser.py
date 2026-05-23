from src.models.node import Node, NodeType
from src.models.request import Request
from src.models.vehicle import Vehicle
from src.models.instance import PDPInstance

class PDPParser:
    """
    Tiện ích đọc dữ liệu bài toán PDP từ tệp tin định dạng chuẩn (Không Time Window).
    """
    @staticmethod
    def parse_li_lim_format(file_path: str) -> PDPInstance:
        """
        Đọc tệp tin dữ liệu định dạng chuẩn Li & Lim cho bài toán PDP.
        Bỏ qua các trường liên quan đến khung thời gian (Time Windows).
        """
        print(f"[Parser] Đang đọc file dữ liệu PDP: {file_path}")
        instance_name = file_path.split("/")[-1].split("\\")[-1].replace(".txt", "")
        instance = PDPInstance(name=instance_name)

        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            raise ValueError(f"Tệp tin rỗng: {file_path}")

        # Dòng 1 chứa: [Số lượng xe] [Tải trọng xe] [Tốc độ / Tham số khác]
        first_line_parts = lines[0].split()
        if len(first_line_parts) >= 2:
            vehicle_count = int(first_line_parts[0])
            vehicle_capacity = float(first_line_parts[1])
        else:
            raise ValueError(f"Dòng đầu tiên không đúng định dạng chứa xe: {lines[0]}")

        # Đọc danh sách các nút từ dòng thứ 2 trở đi
        temp_pickups = {}  # node_id -> delivery_pair_id (để ghép cặp sau)
        
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 9:
                continue  # Bỏ qua dòng tiêu đề hoặc dòng không đủ cột

            node_id = int(parts[0])
            x = float(parts[1])
            y = float(parts[2])
            demand = float(parts[3])
            
            # Chỉ số index 7 là pickup, index 8 là delivery trong tệp Li & Lim
            pickup_pair = int(parts[7])
            delivery_pair = int(parts[8])

            # Xác định loại nút sơ bộ
            if node_id == 0:
                node_type = NodeType.START_DEPOT
            elif demand > 0:
                node_type = NodeType.PICKUP
            elif demand < 0:
                node_type = NodeType.DELIVERY
            else:
                node_type = NodeType.PICKUP  # mặc định

            # Tạo thực thể Node (không lưu thông tin time window)
            node = Node(
                id=node_id,
                original_id=node_id,
                x=x,
                y=y,
                demand=demand,
                node_type=node_type
            )
            instance.nodes[node_id] = node

            # Đăng ký thông tin ghép cặp phục vụ tạo Request sau
            if node_type == NodeType.PICKUP and delivery_pair > 0:
                temp_pickups[node_id] = delivery_pair

        # Khởi tạo danh sách các xe (Depot bắt đầu/kết thúc là nút ID 0)
        depot_node = instance.nodes.get(0)
        if depot_node is None:
            # Tạo depot mặc định nếu tệp không bắt đầu từ 0
            depot_node = Node(id=0, original_id=0, x=40.0, y=50.0, demand=0.0, node_type=NodeType.START_DEPOT)
            instance.nodes[0] = depot_node

        # Thiết lập loại nút của depot
        depot_node.node_type = NodeType.START_DEPOT
        end_depot_node = Node(
            id=depot_node.id,
            original_id=depot_node.original_id,
            x=depot_node.x,
            y=depot_node.y,
            demand=0.0,
            node_type=NodeType.END_DEPOT
        )

        for k in range(1, vehicle_count + 1):
            vehicle = Vehicle(id=k, capacity=vehicle_capacity, start_depot=depot_node, end_depot=end_depot_node)
            instance.vehicles.append(vehicle)

        # Ghép cặp và tạo các đối tượng Request
        request_id = 1
        for p_id, d_id in temp_pickups.items():
            pickup_node = instance.nodes.get(p_id)
            delivery_node = instance.nodes.get(d_id)
            if pickup_node and delivery_node:
                request = Request(
                    id=request_id,
                    pickup_node=pickup_node,
                    delivery_node=delivery_node,
                    demand=pickup_node.demand
                )
                instance.requests[request_id] = request
                request_id += 1

        # Tự động tính ma trận khoảng cách
        instance.calculate_euclidean_distances()
        return instance


