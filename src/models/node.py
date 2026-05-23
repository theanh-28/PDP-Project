from dataclasses import dataclass
from enum import Enum

class NodeType(Enum):
    START_DEPOT = "START_DEPOT"
    END_DEPOT = "END_DEPOT"
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"

@dataclass
class Node:
    """
    Đại diện cho một nút trong mô hình PDP (đồng bộ với Java).
    """
    id: int
    original_id: int
    x: float
    y: float
    demand: float  # Số lượng hàng (+ cho pickup, - cho delivery, 0 cho depot)
    node_type: NodeType

    def is_depot(self) -> bool:
        return self.node_type in (NodeType.START_DEPOT, NodeType.END_DEPOT)

    def is_pickup(self) -> bool:
        return self.node_type == NodeType.PICKUP

    def is_delivery(self) -> bool:
        return self.node_type == NodeType.DELIVERY

    def __repr__(self) -> str:
        return f"Node(ID={self.id}, OrigID={self.original_id}, Type={self.node_type.value}, Demand={self.demand})"
