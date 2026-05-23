from dataclasses import dataclass
from .node import Node, NodeType

@dataclass
class Request:
    """
    Đại diện cho một cặp yêu cầu Pickup & Delivery.
    """
    id: int
    pickup_node: Node
    delivery_node: Node
    demand: float

    def __post_init__(self):
        if self.demand <= 0:
            raise ValueError(f"Request {self.id}: demand phải lớn hơn 0 (đang là {self.demand})")
        # Đảm bảo loại nút đúng vai trò
        self.pickup_node.node_type = NodeType.PICKUP
        self.delivery_node.node_type = NodeType.DELIVERY
        # Đồng bộ demand
        self.pickup_node.demand = self.demand
        self.delivery_node.demand = -self.demand

    def __repr__(self) -> str:
        return f"Request(ID={self.id}, Pickup={self.pickup_node.id}, Delivery={self.delivery_node.id}, Demand={self.demand})"
