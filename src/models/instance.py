from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np

from .node import Node
from .request import Request
from .vehicle import Vehicle
from src.utils.distance import compute_distance_matrix_for_nodes


@dataclass
class PDPInstance:
    """Container for a Li & Lim PDP/PDPTW instance without time windows."""

    name: str
    nodes: Dict[int, Node] = field(default_factory=dict)
    requests: Dict[int, Request] = field(default_factory=dict)
    vehicles: List[Vehicle] = field(default_factory=list)
    distance_matrix: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), dtype=np.float64))
    max_vehicles: int = 0
    vehicle_capacity: float = 0.0
    speed: float = 1.0
    raw_nodes: List[dict[str, Any]] = field(default_factory=list)

    def calculate_euclidean_distances(self) -> np.ndarray:
        self.distance_matrix = compute_distance_matrix_for_nodes(self.nodes)
        return self.distance_matrix

    def get_distance(self, from_node_id: int, to_node_id: int) -> float:
        if self.distance_matrix.size:
            try:
                return float(self.distance_matrix[from_node_id, to_node_id])
            except IndexError:
                pass

        node_a = self.nodes[from_node_id]
        node_b = self.nodes[to_node_id]
        return math.hypot(node_a.x - node_b.x, node_a.y - node_b.y)

    @property
    def vehicle_count(self) -> int:
        return self.max_vehicles or len(self.vehicles)

    @property
    def capacity(self) -> float:
        if self.vehicle_capacity > 0:
            return self.vehicle_capacity
        if self.vehicles:
            return self.vehicles[0].capacity
        return 0.0

    def to_solver_dict(self) -> dict[str, Any]:
        """Return the dictionary shape consumed by pdp_bnb_solver.PDPModel."""
        if self.raw_nodes:
            nodes = [dict(node) for node in self.raw_nodes]
        else:
            nodes = self._synthesize_raw_nodes()

        return {
            "n": len(self.requests),
            "K": self.vehicle_count,
            "C": self.capacity,
            "speed": self.speed,
            "nodes": nodes,
        }

    def _synthesize_raw_nodes(self) -> list[dict[str, Any]]:
        pickup_to_delivery = {
            req.pickup_node.id: req.delivery_node.id for req in self.requests.values()
        }
        delivery_to_pickup = {
            req.delivery_node.id: req.pickup_node.id for req in self.requests.values()
        }

        rows = []
        for node_id in sorted(self.nodes):
            node = self.nodes[node_id]
            rows.append(
                {
                    "id": node.id,
                    "x": float(node.x),
                    "y": float(node.y),
                    "demand": int(float(node.demand)),
                    "e": float(node.earliest),
                    "l": float(node.latest),
                    "s": float(node.service_time),
                    "pickup": int(delivery_to_pickup.get(node_id, 0)),
                    "delivery": int(pickup_to_delivery.get(node_id, 0)),
                }
            )
        return rows

    def __repr__(self) -> str:
        return (
            f"PDPInstance(name={self.name}, nodes={len(self.nodes)}, "
            f"requests={len(self.requests)}, vehicles={self.vehicle_count})"
        )
