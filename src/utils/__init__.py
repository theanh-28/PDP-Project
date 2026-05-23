from .distance import (
    compute_distance_matrix_for_nodes,
    compute_distance_matrix_xy,
    euclidean_distance,
    manhattan_distance,
    route_cost,
)
from .numba_support import NUMBA_AVAILABLE

__all__ = [
    "euclidean_distance",
    "manhattan_distance",
    "compute_distance_matrix_xy",
    "compute_distance_matrix_for_nodes",
    "route_cost",
    "PDPParser",
    "PDPVisualizer",
    "NUMBA_AVAILABLE",
]


def __getattr__(name):
    if name == "PDPParser":
        from .parser import PDPParser

        return PDPParser
    if name == "PDPVisualizer":
        from .visualizer import PDPVisualizer

        return PDPVisualizer
    raise AttributeError(name)
