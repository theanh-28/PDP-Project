import math
from dataclasses import dataclass, field
from typing import List, Dict
from .node import Node
from .request import Request
from .vehicle import Vehicle

@dataclass
class PDPInstance:
    """
    Quản lý dữ liệu bài toán PDP (Pickup and Delivery Problem).
    """
    name: str
    nodes: Dict[int, Node] = field(default_factory=dict)
    requests: Dict[int, Request] = field(default_factory=dict)
    vehicles: List[Vehicle] = field(default_factory=list)
    distance_matrix: List[List[float]] = field(default_factory=list)

    def calculate_euclidean_distances(self):
        """
        Tính ma trận khoảng cách Euclidean giữa mọi nút dựa trên tọa độ.
        """
        n = max(self.nodes.keys()) + 1 if self.nodes else 0
        self.distance_matrix = [[0.0] * n for _ in range(n)]
        for i, node_i in self.nodes.items():
            for j, node_j in self.nodes.items():
                dist = math.sqrt((node_i.x - node_j.x) ** 2 + (node_i.y - node_j.y) ** 2)
                self.distance_matrix[i][j] = dist

    def get_distance(self, from_node_id: int, to_node_id: int) -> float:
        """
        Lấy khoảng cách giữa hai nút.
        """
        try:
            return self.distance_matrix[from_node_id][to_node_id]
        except IndexError:
            node_a = self.nodes[from_node_id]
            node_b = self.nodes[to_node_id]
            return math.sqrt((node_a.x - node_b.x) ** 2 + (node_a.y - node_b.y) ** 2)

    def __repr__(self) -> str:
        return (f"PDPInstance(Name={self.name}, "
                f"Nodes={len(self.nodes)}, "
                f"Requests={len(self.requests)}, "
                f"Vehicles={len(self.vehicles)})")
