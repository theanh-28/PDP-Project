"""Distance utilities backed by the same Numba kernel as pdp_bnb_solver.py."""

import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from src.utils.numba_kernels import _numba_compute_dist_matrix, _numba_route_cost


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def manhattan_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return abs(x1 - x2) + abs(y1 - y2)


def compute_distance_matrix_xy(x: Sequence[float], y: Sequence[float]) -> np.ndarray:
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    if x_arr.shape != y_arr.shape:
        raise ValueError("x and y coordinate arrays must have the same shape.")
    return _numba_compute_dist_matrix(x_arr, y_arr)


def compute_distance_matrix_for_nodes(
    nodes: Mapping[int, Any],
    node_ids: Iterable[int] | None = None,
) -> np.ndarray:
    if node_ids is None:
        if not nodes:
            return np.zeros((0, 0), dtype=np.float64)
        size = max(nodes.keys()) + 1
        ordered_ids = list(range(size))
    else:
        ordered_ids = list(node_ids)
        size = len(ordered_ids)

    x = np.zeros(size, dtype=np.float64)
    y = np.zeros(size, dtype=np.float64)

    if node_ids is None:
        for node_id, node in nodes.items():
            x[node_id] = node.x
            y[node_id] = node.y
    else:
        for idx, node_id in enumerate(ordered_ids):
            node = nodes[node_id]
            x[idx] = node.x
            y[idx] = node.y

    return _numba_compute_dist_matrix(x, y)


def route_cost(route: Sequence[int], distance_matrix: np.ndarray) -> float:
    route_arr = np.asarray(route, dtype=np.int64)
    return float(_numba_route_cost(route_arr, route_arr.shape[0], distance_matrix))
