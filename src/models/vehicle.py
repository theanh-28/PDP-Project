from dataclasses import dataclass
from typing import Optional

from .node import Node, NodeType


@dataclass
class Vehicle:
    """Vehicle metadata used by the skeleton solvers."""

    id: int
    capacity: float
    start_depot: Node
    end_depot: Optional[Node] = None

    def __post_init__(self):
        if self.capacity <= 0:
            raise ValueError(f"Vehicle {self.id}: capacity must be positive.")

        if self.end_depot is None:
            self.end_depot = self.start_depot

        self.start_depot.node_type = NodeType.START_DEPOT
        if self.end_depot is not self.start_depot:
            self.end_depot.node_type = NodeType.END_DEPOT

    def __repr__(self) -> str:
        return (
            f"Vehicle(id={self.id}, capacity={self.capacity}, "
            f"start_depot={self.start_depot.id}, end_depot={self.end_depot.id})"
        )
