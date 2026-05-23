from dataclasses import dataclass
from enum import Enum


class NodeType(Enum):
    START_DEPOT = "START_DEPOT"
    END_DEPOT = "END_DEPOT"
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"
    SERVICE = "SERVICE"


@dataclass
class Node:
    """Raw node/task from a Li & Lim PDP/PDPTW instance."""

    id: int
    original_id: int
    x: float
    y: float
    demand: float
    node_type: NodeType
    earliest: float = 0.0
    latest: float = 0.0
    service_time: float = 0.0
    pickup_id: int = 0
    delivery_id: int = 0

    def is_depot(self) -> bool:
        return self.node_type in (NodeType.START_DEPOT, NodeType.END_DEPOT)

    def is_pickup(self) -> bool:
        return self.node_type == NodeType.PICKUP

    def is_delivery(self) -> bool:
        return self.node_type == NodeType.DELIVERY

    def __repr__(self) -> str:
        return (
            f"Node(id={self.id}, original_id={self.original_id}, "
            f"type={self.node_type.value}, demand={self.demand})"
        )
