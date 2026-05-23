from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .instance import PDPInstance
from .node import NodeType


@dataclass
class PDPSolution:
    """Routes keyed by vehicle id, using raw node ids."""

    instance: PDPInstance
    routes: Dict[int, List[int]] = field(default_factory=dict)

    def calculate_total_cost(self) -> float:
        total_dist = 0.0
        for route in self.routes.values():
            if len(route) < 2:
                continue
            for i in range(len(route) - 1):
                total_dist += self.instance.get_distance(route[i], route[i + 1])
        return total_dist

    def check_feasibility(self) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        visited_pickups: Dict[int, int] = {}
        visited_deliveries: Dict[int, int] = {}

        node_to_request = {}
        for req in self.instance.requests.values():
            node_to_request[req.pickup_node.id] = req
            node_to_request[req.delivery_node.id] = req

        id_to_vehicle = {vehicle.id: vehicle for vehicle in self.instance.vehicles}

        for vehicle_id, route in self.routes.items():
            if not route:
                continue

            vehicle = id_to_vehicle.get(vehicle_id)
            if vehicle is None:
                errors.append(f"Vehicle {vehicle_id}: not found in instance.")
                continue

            if len(route) < 2:
                errors.append(f"Vehicle {vehicle_id}: route must contain start and end depot.")
                continue

            if route[0] != vehicle.start_depot.id:
                errors.append(
                    f"Vehicle {vehicle_id}: starts at node {route[0]} instead of depot "
                    f"{vehicle.start_depot.id} (C2)."
                )
            if route[-1] != vehicle.end_depot.id:
                errors.append(
                    f"Vehicle {vehicle_id}: ends at node {route[-1]} instead of depot "
                    f"{vehicle.end_depot.id} (C3)."
                )

            current_load = 0.0
            route_pickup_positions: Dict[int, int] = {}
            service_seen = set()

            for idx, node_id in enumerate(route):
                node = self.instance.nodes.get(node_id)
                if node is None:
                    errors.append(f"Vehicle {vehicle_id}: visits unknown node {node_id}.")
                    continue

                is_depot_position = idx == 0 or idx == len(route) - 1
                if not is_depot_position:
                    if node_id in service_seen:
                        errors.append(f"Vehicle {vehicle_id}: visits node {node_id} more than once.")
                    service_seen.add(node_id)

                    current_load += node.demand
                    if current_load > vehicle.capacity + 1e-8:
                        errors.append(
                            f"Vehicle {vehicle_id}: load {current_load} exceeds capacity "
                            f"{vehicle.capacity} at node {node_id} (C8)."
                        )
                    if current_load < -1e-8:
                        errors.append(
                            f"Vehicle {vehicle_id}: load is negative ({current_load}) "
                            f"at node {node_id} (C8)."
                        )

                if node.node_type == NodeType.PICKUP:
                    req = node_to_request.get(node_id)
                    if req is None:
                        continue
                    if req.id in visited_pickups:
                        errors.append(
                            f"Request {req.id}: pickup {node_id} served more than once "
                            f"(vehicles {visited_pickups[req.id]} and {vehicle_id}) (C1)."
                        )
                    visited_pickups[req.id] = vehicle_id
                    route_pickup_positions[req.id] = idx

                elif node.node_type == NodeType.DELIVERY:
                    req = node_to_request.get(node_id)
                    if req is None:
                        continue
                    if req.id in visited_deliveries:
                        errors.append(
                            f"Request {req.id}: delivery {node_id} served more than once "
                            f"(vehicles {visited_deliveries[req.id]} and {vehicle_id}) (C1)."
                        )
                    visited_deliveries[req.id] = vehicle_id

                    if visited_pickups.get(req.id) != vehicle_id:
                        errors.append(
                            f"Request {req.id}: delivery {node_id} is visited before or "
                            f"without pickup on vehicle {vehicle_id} (C6)."
                        )
                    else:
                        pickup_pos = route_pickup_positions.get(req.id)
                        if pickup_pos is not None and pickup_pos >= idx:
                            errors.append(
                                f"Request {req.id}: pickup {req.pickup_node.id} is not "
                                f"before delivery {node_id} on vehicle {vehicle_id} (C6)."
                            )

            if abs(current_load) > 1e-8:
                errors.append(
                    f"Vehicle {vehicle_id}: final load is {current_load} instead of 0.0 (C7)."
                )

        for req_id in self.instance.requests:
            pickup_vehicle = visited_pickups.get(req_id)
            delivery_vehicle = visited_deliveries.get(req_id)

            if pickup_vehicle is None:
                errors.append(f"Request {req_id}: pickup is not served (C1).")
            if delivery_vehicle is None:
                errors.append(f"Request {req_id}: delivery is not served (C1).")
            if pickup_vehicle is not None and delivery_vehicle is not None:
                if pickup_vehicle != delivery_vehicle:
                    errors.append(
                        f"Request {req_id}: pickup served by vehicle {pickup_vehicle}, "
                        f"delivery served by vehicle {delivery_vehicle} (C5)."
                    )

        return len(errors) == 0, errors

    def __repr__(self) -> str:
        return f"PDPSolution(routes={len(self.routes)}, cost={self.calculate_total_cost():.2f})"
