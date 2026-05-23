from dataclasses import dataclass
from typing import Optional
from .node import Node, NodeType

@dataclass
class Vehicle:
    """
    Đại diện cho xe vận chuyển (Vehicle).
    """
    id: int
    capacity: float  # Sức chứa tải trọng của xe
    start_depot: Node
    end_depot: Optional[Node] = None

    def __post_init__(self):
        if self.capacity <= 0:
            raise ValueError(f"Vehicle {self.id}: capacity phải lớn hơn 0")
        if self.end_depot is None:
            self.end_depot = self.start_depot
        
        # Đồng bộ loại nút depot
        self.start_depot.node_type = NodeType.START_DEPOT
        if self.end_depot:
            self.end_depot.node_type = NodeType.END_DEPOT

    def __repr__(self) -> str:
        return f"Vehicle(ID={self.id}, Capacity={self.capacity}, StartDepot={self.start_depot.id})"
