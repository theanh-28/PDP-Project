import os
from typing import Any, Mapping, Sequence

import numpy as np

from src.models.instance import PDPInstance
from src.utils.constraints import apply_fixed_arc_bounds, build_lp_components
from src.utils.distance import compute_distance_matrix_xy
from src.utils.numba_kernels import (
    _numba_is_route_feasible,
    _numba_route_cost,
)


ALLOW_INCOMPLETE_INSTANCE = (
    os.environ.get("PDP_ALLOW_INCOMPLETE_INSTANCE", "0").lower()
    in {"1", "true", "yes", "y"}
)


class PDPLinearModel:
    """PDP LP-relaxation model builder matching pdp_bnb_solver.PDPModel."""

    def __init__(self, instance: PDPInstance | Mapping[str, Any]):
        self.instance = instance if isinstance(instance, PDPInstance) else None
        self.inst = instance.to_solver_dict() if isinstance(instance, PDPInstance) else dict(instance)
        self.n = int(self.inst["n"])
        self.K_max = int(self.inst["K"])
        self.C = float(self.inst["C"])
        self.nodes = list(self.inst["nodes"])
        self._base_lp_cache = None

        self._build_graph()

    def _build_graph(self) -> None:
        raw = self.nodes
        raw_by_id = {node["id"]: node for node in raw}

        self.pickup_nodes = []
        self.delivery_nodes = []
        self.pairs = []
        skipped_pairs = []

        for node in raw:
            idx = node["id"]
            if idx == 0:
                continue
            if node["demand"] > 0 and node["pickup"] == 0 and node["delivery"] > 0:
                delivery_id = node["delivery"]
                delivery_node = raw_by_id.get(delivery_id)
                if delivery_node is None:
                    skipped_pairs.append((idx, delivery_id, "missing delivery node"))
                    continue
                if delivery_node["demand"] >= 0:
                    skipped_pairs.append((idx, delivery_id, "delivery has non-negative demand"))
                    continue
                if delivery_node["pickup"] != idx:
                    skipped_pairs.append((idx, delivery_id, "delivery does not point back to pickup"))
                    continue
                if delivery_node["delivery"] != 0:
                    skipped_pairs.append((idx, delivery_id, "delivery row has non-zero delivery sibling"))
                    continue
                if node["demand"] + delivery_node["demand"] != 0:
                    skipped_pairs.append((idx, delivery_id, "pickup/delivery demands do not balance"))
                    continue
                self.pickup_nodes.append(idx)
                self.pairs.append((idx, delivery_id))
            elif node["demand"] < 0 and node["pickup"] > 0:
                self.delivery_nodes.append(idx)

        self.n_pairs = len(self.pairs)
        if skipped_pairs:
            shown = ", ".join(
                f"{pickup}->{delivery} ({reason})"
                for pickup, delivery, reason in skipped_pairs[:5]
            )
            suffix = "" if len(skipped_pairs) <= 5 else f", ... +{len(skipped_pairs) - 5} more"
            message = f"Found {len(skipped_pairs)} invalid pickup-delivery pairs: {shown}{suffix}"
            if not ALLOW_INCOMPLETE_INSTANCE:
                raise ValueError(
                    message
                    + ". The instance is incomplete or not in Li & Lim sibling format. "
                    + "Set PDP_ALLOW_INCOMPLETE_INSTANCE=1 only if you intentionally "
                    + "want to solve the valid sub-instance."
                )
            print(f"[WARN] {message}; solving valid sub-instance only.")

        if self.n_pairs == 0:
            raise ValueError("No valid pickup-delivery pairs found in instance.")
        if self.n != self.n_pairs:
            print(
                f"[WARN] Header-derived request count {self.n} differs from "
                f"model request count {self.n_pairs}; using {self.n_pairs}."
            )
        self.n = self.n_pairs

        configured_k = os.environ.get("PDP_MODEL_K")
        if configured_k:
            self.K = min(int(configured_k), self.K_max, self.n_pairs)
        else:
            self.K = min(self.K_max, self.n_pairs)
        if self.K <= 0:
            raise ValueError("Instance has no available vehicles.")

        self.raw_to_model = {0: 0}
        self.model_to_raw = {0: 0}

        self.P = []
        for idx_enum, (p_raw, _d_raw) in enumerate(self.pairs):
            model_id = idx_enum + 1
            self.raw_to_model[p_raw] = model_id
            self.model_to_raw[model_id] = p_raw
            self.P.append(model_id)

        self.D = []
        for idx_enum, (_p_raw, d_raw) in enumerate(self.pairs):
            model_id = self.n_pairs + idx_enum + 1
            self.raw_to_model[d_raw] = model_id
            self.model_to_raw[model_id] = d_raw
            self.D.append(model_id)

        self.depot_end = 2 * self.n_pairs + 1
        self.raw_to_model[-1] = self.depot_end
        self.model_to_raw[self.depot_end] = 0

        self.n_nodes = self.depot_end + 1
        self.V = list(range(self.n_nodes))

        self.pair_map = {}
        self.pair_delivery = np.full(self.n_nodes, -1, dtype=np.int64)
        for idx_enum in range(self.n_pairs):
            p_model = idx_enum + 1
            d_model = self.n_pairs + idx_enum + 1
            self.pair_map[p_model] = d_model
            self.pair_delivery[p_model] = d_model

        self._compute_distances()

        self.demand = np.zeros(self.n_nodes, dtype=np.int32)
        for model_id in range(self.n_nodes):
            if model_id == 0 or model_id == self.depot_end:
                self.demand[model_id] = 0
            else:
                raw_id = self.model_to_raw[model_id]
                self.demand[model_id] = int(raw_by_id[raw_id]["demand"])

        self.arcs = []
        arcs_i = []
        arcs_j = []
        self.arc_idx = {}
        for i in self.V:
            if i == self.depot_end:
                continue
            for j in self.V:
                if i == j or j == 0:
                    continue
                if i == 0 and j == self.depot_end:
                    continue
                if i == 0 and j in self.D:
                    continue
                if i in self.P and j == self.depot_end:
                    continue
                if i in self.D and j in self.P and self.pair_map[j] == i:
                    continue
                idx = len(self.arcs)
                self.arcs.append((i, j))
                arcs_i.append(i)
                arcs_j.append(j)
                self.arc_idx[(i, j)] = idx

        self.n_arcs = len(self.arcs)
        self.arcs_i = np.array(arcs_i, dtype=np.int64)
        self.arcs_j = np.array(arcs_j, dtype=np.int64)
        self.arc_idx_matrix = np.full((self.n_nodes, self.n_nodes), -1, dtype=np.int64)
        for arc_id, (i, j) in enumerate(self.arcs):
            self.arc_idx_matrix[i, j] = arc_id

        service_set = set(self.P + self.D)
        self.service_arc_ids = np.array(
            [
                arc_id
                for arc_id, (i, j) in enumerate(self.arcs)
                if i in service_set and j in service_set
            ],
            dtype=np.int64,
        )

        self.M_order = self.n_nodes + 1
        self.M_load = self.C + max(0, int(np.max(self.demand)))

    def _compute_distances(self) -> None:
        raw_by_id = {node["id"]: node for node in self.nodes}
        depot = raw_by_id[0]
        self.x = np.zeros(self.n_nodes, dtype=np.float64)
        self.y = np.zeros(self.n_nodes, dtype=np.float64)

        for model_id in range(self.n_nodes):
            raw_id = self.model_to_raw.get(model_id, 0)
            raw_node = raw_by_id.get(raw_id, depot)
            self.x[model_id] = raw_node["x"]
            self.y[model_id] = raw_node["y"]

        self.dist = compute_distance_matrix_xy(self.x, self.y)

    def build_lp(self, fixed_to_1=None, fixed_to_0=None, log: bool = True):
        if fixed_to_1 is None:
            fixed_to_1 = set()
        if fixed_to_0 is None:
            fixed_to_0 = set()

        if self._base_lp_cache is None:
            self._base_lp_cache = build_lp_components(
                K=self.K,
                n_nodes=self.n_nodes,
                n_pairs=self.n_pairs,
                n_arcs=self.n_arcs,
                arc_idx_matrix=self.arc_idx_matrix,
                arcs_i=self.arcs_i,
                arcs_j=self.arcs_j,
                service_arc_ids=self.service_arc_ids,
                distance_matrix=self.dist,
                demand=self.demand,
                capacity=self.C,
                depot_end=self.depot_end,
                M_order=float(self.M_order),
                M_load=float(self.M_load),
            )

        cache = self._base_lp_cache
        bounds = apply_fixed_arc_bounds(
            cache.base_bounds,
            fixed_to_1,
            fixed_to_0,
            K=self.K,
            n_nodes=self.n_nodes,
            n_arcs=self.n_arcs,
            arc_idx_matrix=self.arc_idx_matrix,
        )

        if log:
            print(
                f"[LP] Variables: {cache.n_vars} "
                f"(x:{cache.n_x}, Q:{cache.n_Q}, u:{cache.n_u})"
            )
            print(f"[LP] Eq constraints: {cache.n_eq}, Ineq constraints: {cache.n_ub}")

        return (
            cache.c_obj,
            cache.A_ub,
            cache.b_ub,
            cache.A_eq,
            cache.b_eq,
            bounds,
            cache.n_x,
        )

    def route_cost(self, route: Sequence[int]) -> float:
        route_array = np.asarray(route, dtype=np.int64)
        return float(_numba_route_cost(route_array, route_array.shape[0], self.dist))

    def is_model_route_feasible(self, route: Sequence[int]) -> bool:
        if not route:
            return False
        route_array = np.asarray(route, dtype=np.int64)
        return bool(
            _numba_is_route_feasible(
                route_array,
                route_array.shape[0],
                self.demand,
                self.pair_delivery,
                float(self.C),
                self.depot_end,
                self.n_pairs,
            )
        )

    def model_route_to_raw(self, route: Sequence[int]) -> list[int]:
        return [self.model_to_raw.get(int(node), int(node)) for node in route]

    def model_routes_to_raw_by_vehicle(self, routes: Sequence[Sequence[int]]) -> dict[int, list[int]]:
        if self.instance is None:
            return {idx + 1: self.model_route_to_raw(route) for idx, route in enumerate(routes)}

        out = {}
        vehicles = self.instance.vehicles
        for idx, vehicle in enumerate(vehicles):
            if idx < len(routes):
                out[vehicle.id] = self.model_route_to_raw(routes[idx])
            else:
                out[vehicle.id] = [vehicle.start_depot.id, vehicle.end_depot.id]
        return out

PDPModel = PDPLinearModel
