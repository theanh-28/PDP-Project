from dataclasses import dataclass

from .node import Node, NodeType


@dataclass
class Request:
    """One pickup-delivery pair."""

    id: int
    pickup_node: Node
    delivery_node: Node
    demand: float

    def __post_init__(self):
        if self.demand <= 0:
            raise ValueError(f"Request {self.id}: demand must be positive.")

        self.pickup_node.node_type = NodeType.PICKUP
        self.delivery_node.node_type = NodeType.DELIVERY
        self.pickup_node.demand = self.demand
        self.delivery_node.demand = -self.demand
        self.pickup_node.delivery_id = self.delivery_node.id
        self.delivery_node.pickup_id = self.pickup_node.id

    def __repr__(self) -> str:
        return (
            f"Request(id={self.id}, pickup={self.pickup_node.id}, "
            f"delivery={self.delivery_node.id}, demand={self.demand})"
        )
