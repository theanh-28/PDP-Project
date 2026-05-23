import copy
import math
import random

from src.algorithms.base import BaseSolver
from src.models.instance import PDPInstance
from src.models.solution import PDPSolution


class ALNSSolver(BaseSolver):
    """Adaptive Large Neighborhood Search for PDP.

    Integrated from the standalone alns.py implementation:
    random/worst destroy, greedy/regret-2 repair, roulette operator selection,
    and simulated-annealing acceptance.
    """

    def __init__(
        self,
        instance: PDPInstance,
        initial_solution: PDPSolution | None = None,
        iterations: int = 100,
        destroy_rate: float = 0.2,
        random_seed: int | None = None,
        init_temperature: float = 1.0,
        final_temperature: float = 0.001,
    ):
        super().__init__(instance)
        self.initial_solution = initial_solution
        self.iterations = iterations
        self.destroy_rate = destroy_rate
        self.random = random.Random(random_seed)
        self.init_temperature = init_temperature
        self.final_temperature = final_temperature

        self.destroy_operators = [self._random_destroy, self._worst_destroy]
        self.repair_operators = [self._greedy_repair, self._regret_2_repair]
        self.destroy_weights = [1.0] * len(self.destroy_operators)
        self.repair_weights = [1.0] * len(self.repair_operators)

        self.node_to_request = self._build_node_to_request()
        self.best_cost = float("inf")
        self.current_cost = float("inf")
        self.status = "not_started"
        self.accepted_moves = 0
        self.best_updates = 0

    def solve(self) -> PDPSolution:
        if self.initial_solution is None:
            from src.algorithms.greedy_insertion import GreedyPairInsertionSolver

            current_sol = GreedyPairInsertionSolver(self.instance).solve()
        else:
            current_sol = copy.deepcopy(self.initial_solution)

        best_sol = copy.deepcopy(current_sol)
        current_cost = current_sol.calculate_total_cost()
        best_cost = best_sol.calculate_total_cost()

        n_remove = max(1, int(len(self.instance.requests) * self.destroy_rate))
        self.status = "running"

        for iteration in range(max(0, self.iterations)):
            temperature = self._temperature(iteration)

            destroy_idx = self._roulette_select(self.destroy_weights)
            repair_idx = self._roulette_select(self.repair_weights)
            destroy_op = self.destroy_operators[destroy_idx]
            repair_op = self.repair_operators[repair_idx]

            destroyed, removed = destroy_op(current_sol, n_remove)
            candidate = repair_op(destroyed, removed)
            candidate_cost = candidate.calculate_total_cost()
            is_valid, _errors = candidate.check_feasibility()

            accepted = False
            if is_valid:
                delta = candidate_cost - current_cost
                if delta <= 0:
                    accepted = True
                else:
                    probability = math.exp(-delta / max(1e-12, temperature))
                    accepted = self.random.random() < probability

            if is_valid and accepted:
                current_sol = candidate
                current_cost = candidate_cost
                self.accepted_moves += 1

                if candidate_cost < best_cost:
                    best_sol = copy.deepcopy(candidate)
                    best_cost = candidate_cost
                    self.best_updates += 1
                    self.destroy_weights[destroy_idx] += 5.0
                    self.repair_weights[repair_idx] += 5.0
                else:
                    self.destroy_weights[destroy_idx] += 1.0
                    self.repair_weights[repair_idx] += 1.0
            else:
                self.destroy_weights[destroy_idx] = max(0.1, self.destroy_weights[destroy_idx] * 0.99)
                self.repair_weights[repair_idx] = max(0.1, self.repair_weights[repair_idx] * 0.99)

            if iteration % 50 == 0:
                self._normalize_weights()

        self.current_cost = current_cost
        self.best_cost = best_cost
        self.status = "completed"
        return best_sol

    def _random_destroy(self, solution: PDPSolution, q: int) -> tuple[PDPSolution, list[int]]:
        destroyed = copy.deepcopy(solution)
        present_requests = sorted(self._present_requests(destroyed))
        if not present_requests:
            return destroyed, []

        chosen = self.random.sample(present_requests, min(q, len(present_requests)))
        removed = []
        for req_id in chosen:
            self._remove_request_from_routes(destroyed.routes, req_id)
            removed.append(req_id)

        return destroyed, removed

    def _worst_destroy(self, solution: PDPSolution, q: int) -> tuple[PDPSolution, list[int]]:
        destroyed = copy.deepcopy(solution)
        present_requests = self._present_requests(solution)
        if not present_requests:
            return destroyed, []

        original_cost = solution.calculate_total_cost()
        contributions = []
        for req_id in present_requests:
            temp = copy.deepcopy(solution)
            self._remove_request_from_routes(temp.routes, req_id)
            contribution = original_cost - temp.calculate_total_cost()
            contributions.append((req_id, contribution))

        contributions.sort(key=lambda item: item[1], reverse=True)
        chosen = [req_id for req_id, _contribution in contributions[:q]]

        removed = []
        for req_id in chosen:
            self._remove_request_from_routes(destroyed.routes, req_id)
            removed.append(req_id)

        return destroyed, removed

    def _greedy_repair(self, solution: PDPSolution, removed_req_ids: list[int]) -> PDPSolution:
        reconstructed = copy.deepcopy(solution)

        for req_id in list(removed_req_ids):
            best_move = self._best_insertion_for_request(reconstructed, req_id)
            if best_move is None:
                continue

            vehicle_id, pickup_pos, delivery_pos, _cost = best_move
            self._insert_request(reconstructed.routes, req_id, vehicle_id, pickup_pos, delivery_pos)
            try:
                removed_req_ids.remove(req_id)
            except ValueError:
                pass

        return reconstructed

    def _regret_2_repair(self, solution: PDPSolution, removed_req_ids: list[int]) -> PDPSolution:
        reconstructed = copy.deepcopy(solution)
        queue = list(removed_req_ids)

        while queue:
            best_req = None
            best_choice = None
            best_regret = -float("inf")

            for req_id in queue:
                insertion_costs = self._all_insertions_for_request(reconstructed, req_id)
                if not insertion_costs:
                    continue

                insertion_costs.sort(key=lambda item: item[3])
                c1 = insertion_costs[0][3]
                c2 = insertion_costs[1][3] if len(insertion_costs) > 1 else c1 + 1e6
                regret = c2 - c1

                if regret > best_regret:
                    best_regret = regret
                    best_req = req_id
                    best_choice = insertion_costs[0]

            if best_req is None or best_choice is None:
                break

            vehicle_id, pickup_pos, delivery_pos, _cost = best_choice
            self._insert_request(reconstructed.routes, best_req, vehicle_id, pickup_pos, delivery_pos)

            try:
                queue.remove(best_req)
            except ValueError:
                pass
            try:
                removed_req_ids.remove(best_req)
            except ValueError:
                pass

        return reconstructed

    def _all_insertions_for_request(self, solution: PDPSolution, req_id: int):
        req = self.instance.requests.get(req_id)
        if req is None:
            return []

        pickup_id = req.pickup_node.id
        delivery_id = req.delivery_node.id
        get_dist = self.instance.get_distance
        insertions = []

        for vehicle in self.instance.vehicles:
            route = solution.routes.get(vehicle.id)
            if route is None or len(route) < 2:
                continue

            route_len = len(route)
            for pickup_pos in range(1, route_len):
                prev_pickup = route[pickup_pos - 1]
                next_pickup = route[pickup_pos]
                delta_pickup = (
                    get_dist(prev_pickup, pickup_id)
                    + get_dist(pickup_id, next_pickup)
                    - get_dist(prev_pickup, next_pickup)
                )

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

                    trial = (
                        route[:pickup_pos]
                        + [pickup_id]
                        + route[pickup_pos:delivery_pos]
                        + [delivery_id]
                        + route[delivery_pos:]
                    )
                    if self._route_capacity_feasible(trial, vehicle.capacity):
                        insertions.append((vehicle.id, pickup_pos, delivery_pos, cost_increase))

        return insertions

    def _best_insertion_for_request(self, solution: PDPSolution, req_id: int):
        insertions = self._all_insertions_for_request(solution, req_id)
        if not insertions:
            return None
        return min(insertions, key=lambda item: item[3])

    def _route_capacity_feasible(self, route: list[int], capacity: float) -> bool:
        load = 0.0
        for node_id in route:
            node = self.instance.nodes[node_id]
            load += node.demand
            if load > capacity + 1e-8 or load < -1e-8:
                return False
        return abs(load) <= 1e-8

    def _present_requests(self, solution: PDPSolution) -> set[int]:
        present = set()
        for route in solution.routes.values():
            for node_id in route:
                req_id = self.node_to_request.get(node_id)
                if req_id is not None:
                    present.add(req_id)
        return present

    def _remove_request_from_routes(self, routes: dict[int, list[int]], req_id: int) -> None:
        req = self.instance.requests.get(req_id)
        if req is None:
            return

        pickup_id = req.pickup_node.id
        delivery_id = req.delivery_node.id
        for vehicle_id, route in routes.items():
            routes[vehicle_id] = [
                node_id
                for node_id in route
                if node_id != pickup_id and node_id != delivery_id
            ]

    def _insert_request(
        self,
        routes: dict[int, list[int]],
        req_id: int,
        vehicle_id: int,
        pickup_pos: int,
        delivery_pos: int,
    ) -> None:
        req = self.instance.requests[req_id]
        route = routes[vehicle_id]
        routes[vehicle_id] = (
            route[:pickup_pos]
            + [req.pickup_node.id]
            + route[pickup_pos:delivery_pos]
            + [req.delivery_node.id]
            + route[delivery_pos:]
        )

    def _roulette_select(self, weights: list[float]) -> int:
        total = sum(weights)
        if total <= 0:
            return self.random.randrange(len(weights))

        pick = self.random.random() * total
        cumulative = 0.0
        for idx, weight in enumerate(weights):
            cumulative += weight
            if pick <= cumulative:
                return idx
        return len(weights) - 1

    def _normalize_weights(self) -> None:
        for weights in (self.destroy_weights, self.repair_weights):
            total = sum(weights)
            if total <= 0:
                continue
            for idx in range(len(weights)):
                weights[idx] = max(0.1, weights[idx] / total * len(weights))

    def _temperature(self, iteration: int) -> float:
        if self.iterations <= 1:
            return self.final_temperature
        ratio = iteration / max(1, self.iterations - 1)
        return self.init_temperature * ((self.final_temperature / self.init_temperature) ** ratio)

    def _build_node_to_request(self) -> dict[int, int]:
        node_to_request = {}
        for req_id, req in self.instance.requests.items():
            node_to_request[req.pickup_node.id] = req_id
            node_to_request[req.delivery_node.id] = req_id
        return node_to_request
