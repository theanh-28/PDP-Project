import math
import time
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from src.algorithms.base import BaseSolver
from src.models.instance import PDPInstance
from src.models.solution import PDPSolution
from src.utils.distance import compute_distance_matrix_xy
from src.utils.numba_kernels import (
    _numba_local_route_cost,
    _numba_local_route_feasible,
)


@dataclass
class _LocalRoute:
    nodes: list[int]
    cost: float = 0.0


class LocalSearchSolver(BaseSolver):
    """Sweep initial solution + intra-route 2-opt/Or-opt local search.

    Ported from pdptw_local_search.py. Routes are optimized in a dense internal
    index space for Numba kernels, then converted back to raw project node ids.
    Time-window columns remain metadata and are not enforced, matching the
    original script behavior.
    """

    def __init__(
        self,
        instance: PDPInstance,
        initial_solution: PDPSolution | None = None,
        time_limit: float = 60.0,
        max_passes: int = 2,
    ):
        super().__init__(instance)
        self.initial_solution = initial_solution
        self.time_limit = time_limit
        self.max_passes = max_passes

        self.depot_id = self._resolve_depot_id()
        self.raw_to_idx: dict[int, int] = {}
        self.idx_to_raw: dict[int, int] = {}
        self.pickup_of: dict[int, int] = {}
        self.delivery_of: dict[int, int] = {}
        self.dist = np.zeros((0, 0), dtype=np.float64)
        self.demands = np.zeros(0, dtype=np.float64)
        self.pickup_of_arr = np.zeros(0, dtype=np.int64)
        self.delivery_of_arr = np.zeros(0, dtype=np.int64)
        self.n_requests = 0
        self.status = "not_started"
        self.elapsed_time = 0.0

        self._prepare()

    def solve(self) -> PDPSolution:
        start = time.time()
        routes = self._initial_routes()
        self.status = "running"

        for _pass in range(max(0, int(self.max_passes))):
            if time.time() - start > self.time_limit:
                self.status = "time_limit"
                break

            improved = False
            for route in routes:
                if time.time() - start > self.time_limit:
                    self.status = "time_limit"
                    break
                if self._two_opt(route):
                    improved = True

            if self.status == "time_limit":
                break

            for route in routes:
                if time.time() - start > self.time_limit:
                    self.status = "time_limit"
                    break
                for seg_size in (2, 3):
                    if self._or_opt(route, seg_size):
                        improved = True

            if self.status == "time_limit":
                break
            if not improved:
                self.status = "local_optimum"
                break
        else:
            if self.status == "running":
                self.status = "max_passes"

        routes = [route for route in routes if route.nodes]
        self.elapsed_time = time.time() - start
        return self._to_solution(routes)

    def _prepare(self) -> None:
        service_ids = sorted(node_id for node_id in self.instance.nodes if node_id != self.depot_id)

        self.raw_to_idx = {self.depot_id: 0}
        self.idx_to_raw = {0: self.depot_id}
        for idx, raw_id in enumerate(service_ids, start=1):
            self.raw_to_idx[raw_id] = idx
            self.idx_to_raw[idx] = raw_id

        x = np.zeros(len(service_ids) + 1, dtype=np.float64)
        y = np.zeros(len(service_ids) + 1, dtype=np.float64)
        demands = np.zeros(len(service_ids) + 1, dtype=np.float64)

        depot = self.instance.nodes[self.depot_id]
        x[0] = depot.x
        y[0] = depot.y

        for raw_id in service_ids:
            idx = self.raw_to_idx[raw_id]
            node = self.instance.nodes[raw_id]
            x[idx] = node.x
            y[idx] = node.y
            demands[idx] = node.demand

        self.dist = compute_distance_matrix_xy(x, y)
        self.demands = demands
        self.pickup_of_arr = -np.ones(len(service_ids) + 1, dtype=np.int64)
        self.delivery_of_arr = -np.ones(len(service_ids) + 1, dtype=np.int64)

        for req in self.instance.requests.values():
            pickup_idx = self.raw_to_idx[req.pickup_node.id]
            delivery_idx = self.raw_to_idx[req.delivery_node.id]
            self.delivery_of[pickup_idx] = delivery_idx
            self.pickup_of[delivery_idx] = pickup_idx
            self.delivery_of_arr[pickup_idx] = delivery_idx
            self.pickup_of_arr[delivery_idx] = pickup_idx

        self.n_requests = len(self.instance.requests)

    def _initial_routes(self) -> list[_LocalRoute]:
        if self.initial_solution is not None:
            routes = []
            for raw_route in self.initial_solution.routes.values():
                internal = self._raw_route_to_internal(raw_route)
                if internal:
                    routes.append(_LocalRoute(internal, self._route_cost(internal)))
            if routes:
                return routes

        return self._sweep_initial_solution()

    def _sweep_initial_solution(self) -> list[_LocalRoute]:
        routes = []
        for group in self._sweep_groups():
            routes.append(self._build_route_from_group(group))
        return routes

    def _sweep_groups(self) -> list[list[tuple[int, int]]]:
        pickup_indices = list(self.delivery_of.keys())
        depot_x = self.instance.nodes[self.depot_id].x
        depot_y = self.instance.nodes[self.depot_id].y

        def angle(pickup_idx: int) -> float:
            node = self.instance.nodes[self.idx_to_raw[pickup_idx]]
            return math.atan2(node.y - depot_y, node.x - depot_x)

        pickup_indices.sort(key=angle)

        groups: list[list[tuple[int, int]]] = []
        current_group: list[tuple[int, int]] = []
        current_load = 0.0
        capacity = self.instance.capacity

        for pickup_idx in pickup_indices:
            delivery_idx = self.delivery_of[pickup_idx]
            request_load = self.demands[pickup_idx]
            if current_group and current_load + request_load > capacity + 1e-8:
                groups.append(current_group)
                current_group = [(pickup_idx, delivery_idx)]
                current_load = request_load
            else:
                current_group.append((pickup_idx, delivery_idx))
                current_load += request_load

        if current_group:
            groups.append(current_group)
        return groups

    def _build_route_from_group(self, group: list[tuple[int, int]]) -> _LocalRoute:
        if not group:
            return _LocalRoute([], 0.0)

        pickup_idx, delivery_idx = group[0]
        route_nodes = [pickup_idx, delivery_idx]

        for pickup_idx, delivery_idx in group[1:]:
            best_nodes = None
            best_cost = float("inf")

            for pickup_pos in range(len(route_nodes) + 1):
                with_pickup = route_nodes[:]
                with_pickup.insert(pickup_pos, pickup_idx)

                for delivery_pos in range(pickup_pos + 1, len(with_pickup) + 1):
                    trial = with_pickup[:]
                    trial.insert(delivery_pos, delivery_idx)
                    if self._is_feasible(trial):
                        cost = self._route_cost(trial)
                        if cost < best_cost:
                            best_cost = cost
                            best_nodes = trial

            if best_nodes is not None:
                route_nodes = best_nodes
            else:
                route_nodes.extend([pickup_idx, delivery_idx])

        return _LocalRoute(route_nodes, self._route_cost(route_nodes))

    def _two_opt(self, route: _LocalRoute) -> bool:
        nodes = route.nodes
        if len(nodes) < 4:
            return False

        best_cost = route.cost
        best_nodes = nodes[:]
        improved = False

        for i in range(len(nodes) - 1):
            for j in range(i + 2, len(nodes)):
                trial = nodes[: i + 1] + nodes[i + 1 : j + 1][::-1] + nodes[j + 1 :]
                if self._is_feasible(trial):
                    cost = self._route_cost(trial)
                    if cost < best_cost - 1e-6:
                        best_cost = cost
                        best_nodes = trial
                        improved = True

        if improved:
            route.nodes = best_nodes
            route.cost = best_cost
            return True
        return False

    def _or_opt(self, route: _LocalRoute, seg_size: int) -> bool:
        nodes = route.nodes
        if len(nodes) <= seg_size:
            return False

        best_cost = route.cost
        best_nodes = nodes[:]
        improved = False

        for i in range(len(nodes) - seg_size + 1):
            segment = nodes[i : i + seg_size]
            remaining = nodes[:i] + nodes[i + seg_size :]

            for j in range(len(remaining) + 1):
                trial = remaining[:j] + segment + remaining[j:]
                if trial != nodes and self._is_feasible(trial):
                    cost = self._route_cost(trial)
                    if cost < best_cost - 1e-6:
                        best_cost = cost
                        best_nodes = trial
                        improved = True

        if improved:
            route.nodes = best_nodes
            route.cost = best_cost
            return True
        return False

    def _route_cost(self, nodes: Iterable[int]) -> float:
        route = np.asarray(list(nodes), dtype=np.int64)
        return float(_numba_local_route_cost(route, route.shape[0], self.dist))

    def _is_feasible(self, nodes: Iterable[int]) -> bool:
        route = np.asarray(list(nodes), dtype=np.int64)
        return bool(
            _numba_local_route_feasible(
                route,
                route.shape[0],
                self.demands,
                self.pickup_of_arr,
                float(self.instance.capacity),
            )
        )

    def _raw_route_to_internal(self, raw_route: list[int]) -> list[int]:
        internal = []
        for raw_id in raw_route:
            if raw_id == self.depot_id:
                continue
            idx = self.raw_to_idx.get(raw_id)
            if idx is not None:
                internal.append(idx)
        return internal

    def _to_solution(self, routes: list[_LocalRoute]) -> PDPSolution:
        out: dict[int, list[int]] = {}
        vehicles = self.instance.vehicles

        for idx, vehicle in enumerate(vehicles):
            if idx < len(routes):
                raw_nodes = [self.idx_to_raw[node_idx] for node_idx in routes[idx].nodes]
                out[vehicle.id] = [vehicle.start_depot.id] + raw_nodes + [vehicle.end_depot.id]
            else:
                out[vehicle.id] = [vehicle.start_depot.id, vehicle.end_depot.id]

        if len(routes) > len(vehicles):
            print(
                f"[WARN] Local search built {len(routes)} routes but instance has "
                f"{len(vehicles)} vehicles; extra routes are not returned."
            )

        return PDPSolution(instance=self.instance, routes=out)

    def _resolve_depot_id(self) -> int:
        if self.instance.vehicles:
            return self.instance.vehicles[0].start_depot.id
        if 0 in self.instance.nodes:
            return 0
        return min(self.instance.nodes)
