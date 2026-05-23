import math

from src.algorithms.base import BaseSolver
from src.models.instance import PDPInstance
from src.models.request import Request
from src.models.solution import PDPSolution


class GreedyPairInsertionSolver(BaseSolver):
    """Greedy Pair Best Insertion heuristic for PDP.

    This implementation follows the standalone greedy.py logic: at each step it
    scans all unassigned pickup-delivery requests, all vehicles, and all valid
    insertion positions, then applies the globally cheapest feasible insertion.
    """

    def __init__(
        self,
        instance: PDPInstance,
        max_requests_per_vehicle: int | None = None,
        balanced_vehicle_usage: bool = True,
    ):
        super().__init__(instance)
        self.max_requests_per_vehicle = max_requests_per_vehicle
        self.balanced_vehicle_usage = balanced_vehicle_usage
        self.unassigned_count = 0
        self.last_warning: str | None = None

    def solve(self) -> PDPSolution:
        routes = {
            vehicle.id: [vehicle.start_depot.id, vehicle.end_depot.id]
            for vehicle in self.instance.vehicles
        }
        unassigned_requests = list(self.instance.requests.values())
        get_dist = self.instance.get_distance

        max_requests_per_vehicle = self._resolve_max_requests_per_vehicle(
            request_count=len(unassigned_requests),
            vehicle_count=len(self.instance.vehicles),
        )
        vehicle_request_count = {vehicle.id: 0 for vehicle in self.instance.vehicles}

        while unassigned_requests:
            best_cost_increase = float("inf")
            best_req_idx = -1
            best_insertion = None

            for req_idx, req in enumerate(unassigned_requests):
                pickup_id = req.pickup_node.id
                delivery_id = req.delivery_node.id

                for vehicle in self.instance.vehicles:
                    vehicle_id = vehicle.id
                    if vehicle_request_count[vehicle_id] >= max_requests_per_vehicle:
                        continue

                    route = routes[vehicle_id]
                    route_len = len(route)

                    for pickup_pos in range(1, route_len):
                        prev_pickup = route[pickup_pos - 1]
                        next_pickup = route[pickup_pos]
                        delta_pickup = (
                            get_dist(prev_pickup, pickup_id)
                            + get_dist(pickup_id, next_pickup)
                            - get_dist(prev_pickup, next_pickup)
                        )

                        if delta_pickup >= best_cost_increase:
                            continue

                        for delivery_pos in range(pickup_pos, route_len):
                            if delivery_pos == pickup_pos:
                                prev_delivery = pickup_id
                                next_delivery = route[pickup_pos]
                            else:
                                prev_delivery = route[delivery_pos - 1]
                                next_delivery = route[delivery_pos]

                            delta_delivery = (
                                get_dist(prev_delivery, delivery_id)
                                + get_dist(delivery_id, next_delivery)
                                - get_dist(prev_delivery, next_delivery)
                            )
                            cost_increase = delta_pickup + delta_delivery

                            if cost_increase >= best_cost_increase:
                                continue

                            test_route = (
                                route[:pickup_pos]
                                + [pickup_id]
                                + route[pickup_pos:delivery_pos]
                                + [delivery_id]
                                + route[delivery_pos:]
                            )
                            if not self._route_capacity_feasible(test_route, vehicle.capacity):
                                continue

                            best_cost_increase = cost_increase
                            best_req_idx = req_idx
                            best_insertion = (vehicle_id, pickup_pos, delivery_pos)

            if best_req_idx < 0 or best_insertion is None:
                self.unassigned_count = len(unassigned_requests)
                self.last_warning = (
                    f"No feasible insertion found for {self.unassigned_count} "
                    "remaining requests."
                )
                print(f"[WARN] {self.last_warning}")
                break

            vehicle_id, pickup_pos, delivery_pos = best_insertion
            best_req = unassigned_requests[best_req_idx]
            self._insert_request(
                routes=routes,
                vehicle_id=vehicle_id,
                request=best_req,
                pickup_pos=pickup_pos,
                delivery_pos=delivery_pos,
            )
            vehicle_request_count[vehicle_id] += 1
            unassigned_requests.pop(best_req_idx)

        return PDPSolution(instance=self.instance, routes=routes)

    def _resolve_max_requests_per_vehicle(self, request_count: int, vehicle_count: int) -> int:
        if self.max_requests_per_vehicle is not None:
            return max(1, int(self.max_requests_per_vehicle))
        if request_count == 0:
            return 0
        if not self.balanced_vehicle_usage or vehicle_count <= 0:
            return request_count
        return math.ceil(request_count / vehicle_count)

    def _route_capacity_feasible(self, route: list[int], capacity: float) -> bool:
        current_load = 0.0
        for node_id in route:
            node = self.instance.nodes[node_id]
            current_load += node.demand
            if current_load > capacity + 1e-8 or current_load < -1e-8:
                return False
        return abs(current_load) <= 1e-8

    def _insert_request(
        self,
        routes: dict[int, list[int]],
        vehicle_id: int,
        request: Request,
        pickup_pos: int,
        delivery_pos: int,
    ) -> None:
        route = routes[vehicle_id]
        routes[vehicle_id] = (
            route[:pickup_pos]
            + [request.pickup_node.id]
            + route[pickup_pos:delivery_pos]
            + [request.delivery_node.id]
            + route[delivery_pos:]
        )
