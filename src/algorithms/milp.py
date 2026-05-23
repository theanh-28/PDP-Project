import heapq
import os
import time

import numpy as np
from scipy.optimize import linprog

from src.algorithms.base import BaseSolver
from src.models.instance import PDPInstance
from src.models.optimization_model import PDPLinearModel
from src.models.solution import PDPSolution
from src.utils.numba_kernels import (
    _numba_extract_routes_from_x,
    _numba_fractional_variables,
)


MAX_LP_VARIABLES = int(os.environ.get("PDP_MAX_LP_VARIABLES", "35000"))
LP_TIME_LIMIT_REACHED = "LP_TIME_LIMIT_REACHED"


class BBNode:
    """One Branch-and-Bound node with arc-fixing decisions."""

    _counter = 0

    def __init__(self, fixed_1=None, fixed_0=None, parent_lb: float = 0.0, depth: int = 0):
        self.fixed_1 = fixed_1 or set()
        self.fixed_0 = fixed_0 or set()
        self.lb = parent_lb
        self.depth = depth
        self.lp_result = None
        BBNode._counter += 1
        self.id = BBNode._counter

    def __lt__(self, other):
        return self.lb < other.lb


class MILPPDPSolver(BaseSolver):
    """Branch-and-Bound + LP relaxation solver for PDP."""

    def __init__(
        self,
        instance: PDPInstance,
        time_limit: float | None = 30,
        lp_time_limit: float | None = None,
        gap_tol: float = 0.01,
        verbose: bool = True,
        max_lp_variables: int | None = None,
    ):
        super().__init__(instance)
        self.time_limit = time_limit
        self.lp_time_limit = lp_time_limit
        self.gap_tol = gap_tol
        self.verbose = verbose
        self.max_lp_variables = MAX_LP_VARIABLES if max_lp_variables is None else int(max_lp_variables)
        self.model: PDPLinearModel | None = None

        self.Z_UB = np.inf
        self.Z_LB = -np.inf
        self.best_model_routes: list[list[int]] | None = None

        self.nodes_explored = 0
        self.nodes_pruned = 0
        self.lps_solved = 0
        self.stopped_early = False
        self.status = "not_started"

    def build_lp_relaxation(self, fixed_to_1=None, fixed_to_0=None, log: bool = True):
        self.model = self.model or PDPLinearModel(self.instance)
        return self.model.build_lp(fixed_to_1=fixed_to_1, fixed_to_0=fixed_to_0, log=log)

    def solve(self) -> PDPSolution:
        t_start = time.time()
        self.model = self.model or PDPLinearModel(self.instance)
        self._reset_search_state()

        if self.verbose:
            print("=" * 60)
            print("PDP MILP Branch-and-Bound Solver")
            print("=" * 60)
            print("[INIT] Pure MILP mode: no initial incumbent.")

        estimated_vars = self.model.K * self.model.n_arcs + 2 * self.model.K * self.model.n_nodes
        if estimated_vars > self.max_lp_variables:
            self.Z_LB = 0.0
            self.status = "skipped_large_lp"
            if self.verbose:
                print(
                    f"[B&B] Skipping LP B&B: estimated variables {estimated_vars:,} "
                    f"> limit {self.max_lp_variables:,}."
                )
                print("[B&B] No MILP solution generated because LP B&B was skipped.")
                self._print_results(time.time() - t_start)
            return self._build_solution()

        root = BBNode()
        queue = [root]
        self.status = "running"

        if self.verbose:
            time_limit_label = "none" if self.time_limit is None else f"{self.time_limit}s"
            lp_limit_label = "none" if self.lp_time_limit is None else f"{self.lp_time_limit}s"
            print("[B&B] Starting Branch-and-Bound...")
            print(
                f"[B&B] Time limit: {time_limit_label}, "
                f"LP time limit: {lp_limit_label}, Gap tolerance: {self.gap_tol}"
            )

        while queue:
            elapsed = time.time() - t_start
            if self.time_limit is not None and elapsed > self.time_limit:
                self.stopped_early = True
                self.status = "time_limit"
                if self.verbose:
                    print(f"[B&B] Time limit reached ({elapsed:.1f}s).")
                break

            node = heapq.heappop(queue)
            self.nodes_explored += 1

            if self.verbose and self.nodes_explored % 10 == 0:
                print(
                    f"Node {self.nodes_explored:4d} | "
                    f"Depth {node.depth:3d} | "
                    f"LB {node.lb:10.4f} | "
                    f"UB {self.Z_UB:10.4f} | "
                    f"Gap {self._gap():7.3f}% | "
                    f"Queue {len(queue):4d}"
                )

            remaining_time = None
            if self.time_limit is not None:
                remaining_time = max(1.0, self.time_limit - (time.time() - t_start))

            lp_result = self._solve_node_lp(node, remaining_time)
            self.lps_solved += 1

            if lp_result == LP_TIME_LIMIT_REACHED:
                self.stopped_early = True
                self.status = "lp_time_limit"
                self.Z_LB = min((n.lb for n in queue), default=self.Z_LB)
                if self.verbose:
                    print("[B&B] LP solver time limit reached; stopping.")
                break

            if lp_result is None:
                self.nodes_pruned += 1
                if not queue and self.Z_UB < np.inf:
                    self.Z_LB = self.Z_UB
                continue

            lp_obj, x_lp = lp_result
            node.lb = lp_obj

            if lp_obj >= self.Z_UB - 1e-8:
                self.nodes_pruned += 1
                self._update_global_lb(queue, node)
                continue

            frac_vars = self._find_fractional(x_lp, node)
            if not frac_vars:
                routes, total = self._extract_routes(x_lp)
                if routes is not None and total < self.Z_UB:
                    self.Z_UB = total
                    self.best_model_routes = routes
                    if self.verbose:
                        print(f"*** Integer feasible solution found: {total:.4f} ***")
                elif routes is None and self.verbose:
                    print("[WARN] Integral LP solution failed route validation.")
                self.nodes_pruned += 1
                self._update_global_lb(queue, node)
                continue

            self._update_global_lb(queue, node)
            if self._gap() < self.gap_tol * 100:
                self.stopped_early = True
                self.status = "gap_tolerance"
                if self.verbose:
                    print(f"[B&B] Gap tolerance reached: {self._gap():.4f}%")
                break

            branch_var = self._select_branch_var(frac_vars)
            if branch_var is None:
                continue

            i, j, k, _val = branch_var
            heapq.heappush(
                queue,
                BBNode(
                    fixed_1=node.fixed_1 | {(i, j, k)},
                    fixed_0=node.fixed_0.copy(),
                    parent_lb=lp_obj,
                    depth=node.depth + 1,
                ),
            )
            heapq.heappush(
                queue,
                BBNode(
                    fixed_1=node.fixed_1.copy(),
                    fixed_0=node.fixed_0 | {(i, j, k)},
                    parent_lb=lp_obj,
                    depth=node.depth + 1,
                ),
            )

        if not queue and not self.stopped_early and self.Z_UB < np.inf:
            self.Z_LB = self.Z_UB
            self.status = "optimal"
        elif self.status == "running":
            self.status = "stopped"

        if self.verbose:
            self._print_results(time.time() - t_start)

        return self._build_solution()

    def _reset_search_state(self) -> None:
        BBNode._counter = 0
        self.Z_UB = np.inf
        self.Z_LB = -np.inf
        self.best_model_routes = None
        self.nodes_explored = 0
        self.nodes_pruned = 0
        self.lps_solved = 0
        self.stopped_early = False
        self.status = "not_started"

    def _solve_node_lp(self, node: BBNode, remaining_time: float | None = None):
        try:
            c, A_ub, b_ub, A_eq, b_eq, bounds, n_x = self.model.build_lp(
                fixed_to_1=node.fixed_1,
                fixed_to_0=node.fixed_0,
                log=self.verbose and (self.nodes_explored == 1 or self.nodes_explored % 10 == 0),
            )

            highs_options = {"presolve": True}
            active_lp_limit = self.lp_time_limit
            if remaining_time is not None:
                active_lp_limit = (
                    remaining_time
                    if active_lp_limit is None
                    else min(active_lp_limit, remaining_time)
                )
            if active_lp_limit is not None:
                highs_options["time_limit"] = active_lp_limit

            result = linprog(
                c,
                A_ub=A_ub,
                b_ub=b_ub,
                A_eq=A_eq,
                b_eq=b_eq,
                bounds=bounds,
                method="highs",
                options=highs_options,
            )

            if result.success and result.status == 0:
                return result.fun, result.x[:n_x]
            if result.status == 1:
                return LP_TIME_LIMIT_REACHED
            return None
        except Exception as exc:
            if self.verbose:
                print(f"[LP ERROR] {exc}")
            return None

    def _find_fractional(self, x_lp, node: BBNode, tol: float = 1e-5):
        frac_i, frac_j, frac_k, frac_val = _numba_fractional_variables(
            x_lp,
            self.model.arcs_i,
            self.model.arcs_j,
            self.model.K,
            self.model.n_arcs,
            tol,
        )
        out = []
        for idx in range(len(frac_val)):
            i = int(frac_i[idx])
            j = int(frac_j[idx])
            k = int(frac_k[idx])
            if (i, j, k) not in node.fixed_1 and (i, j, k) not in node.fixed_0:
                out.append((i, j, k, float(frac_val[idx])))
        return out

    def _select_branch_var(self, frac_vars):
        if not frac_vars:
            return None
        return min(frac_vars, key=lambda item: abs(item[3] - 0.5))

    def _extract_routes(self, x_lp):
        valid, route_matrix, route_lengths, total = _numba_extract_routes_from_x(
            x_lp,
            self.model.arcs_i,
            self.model.arcs_j,
            self.model.K,
            self.model.n_arcs,
            self.model.n_nodes,
            self.model.depot_end,
            self.model.demand,
            self.model.pair_delivery,
            float(self.model.C),
            self.model.n_pairs,
            self.model.dist,
        )
        if not valid:
            return None, None

        routes = []
        for k in range(self.model.K):
            route_len = int(route_lengths[k])
            if route_len > 0:
                routes.append(route_matrix[k, :route_len].astype(np.int64).tolist())

        return routes, float(total)

    def _update_global_lb(self, queue, current_node: BBNode) -> None:
        if queue:
            self.Z_LB = min(node.lb for node in queue)
        else:
            self.Z_LB = current_node.lb

    def _gap(self) -> float:
        if self.Z_UB == 0 or self.Z_UB == np.inf:
            return 100.0
        if self.Z_LB == -np.inf:
            return 100.0
        return max(0.0, (self.Z_UB - self.Z_LB) / self.Z_UB * 100.0)

    def _build_solution(self) -> PDPSolution:
        if self.best_model_routes is None:
            routes = {
                vehicle.id: [vehicle.start_depot.id, vehicle.end_depot.id]
                for vehicle in self.instance.vehicles
            }
        else:
            routes = self.model.model_routes_to_raw_by_vehicle(self.best_model_routes)
        return PDPSolution(instance=self.instance, routes=routes)

    def _print_results(self, elapsed: float) -> None:
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Status:                 {self.status}")
        print(f"Best incumbent (Z_UB):  {self.Z_UB:.4f}")
        print(f"Best lower bound:       {self.Z_LB:.4f}")
        print(f"Optimality gap:         {self._gap():.4f}%")
        print(f"Nodes explored:         {self.nodes_explored}")
        print(f"Nodes pruned:           {self.nodes_pruned}")
        print(f"LPs solved:             {self.lps_solved}")
        print(f"Time elapsed:           {elapsed:.2f}s")
        print(f"Number of routes:       {len(self.best_model_routes) if self.best_model_routes else 0}")
        if self.best_model_routes:
            for idx, route in enumerate(self.best_model_routes, start=1):
                raw_route = self.model.model_route_to_raw(route)
                route_cost = self.model.route_cost(route)
                print(f"Route {idx}: {raw_route} cost={route_cost:.4f}")
        print("=" * 60)
