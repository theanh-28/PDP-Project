"""Sparse LP component builder for the PDP model.

This module keeps the mathematical model construction in one place.  The
constraint formulas are the same as pdp_bnb_solver.py:

OF, C1/C1b, C2/C3/C3b/C3c, C4/C4b, C5, C6, C7, C8-C10.
"""

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix

from src.utils.numba_kernels import (
    _numba_build_eq_constraints,
    _numba_build_objective,
    _numba_build_ub_constraints,
    _numba_build_variable_bounds,
)


@dataclass
class LPComponents:
    c_obj: np.ndarray
    A_ub: csr_matrix
    b_ub: np.ndarray
    A_eq: csr_matrix
    b_eq: np.ndarray
    base_bounds: np.ndarray
    n_x: int
    n_Q: int
    n_u: int
    n_vars: int
    n_eq: int
    n_ub: int


def build_lp_components(
    *,
    K: int,
    n_nodes: int,
    n_pairs: int,
    n_arcs: int,
    arc_idx_matrix: np.ndarray,
    arcs_i: np.ndarray,
    arcs_j: np.ndarray,
    service_arc_ids: np.ndarray,
    distance_matrix: np.ndarray,
    demand: np.ndarray,
    capacity: float,
    depot_end: int,
    M_order: float,
    M_load: float,
) -> LPComponents:
    n_x = K * n_arcs
    n_Q = K * n_nodes
    n_u = K * n_nodes
    n_vars = n_x + n_Q + n_u

    c_obj = _numba_build_objective(
        distance_matrix,
        arcs_i,
        arcs_j,
        K,
        n_arcs,
        n_vars,
    )

    lb, ub = _numba_build_variable_bounds(
        K,
        n_arcs,
        n_nodes,
        n_vars,
        float(capacity),
        depot_end,
    )
    base_bounds = np.column_stack((lb, ub))

    eq_rows, eq_cols, eq_vals, b_eq = _numba_build_eq_constraints(
        K,
        n_nodes,
        n_pairs,
        n_arcs,
        arc_idx_matrix,
        depot_end,
    )
    n_eq = int(b_eq.shape[0])
    A_eq = csr_matrix((eq_vals, (eq_rows, eq_cols)), shape=(n_eq, n_vars))

    ub_rows, ub_cols, ub_vals, b_ub = _numba_build_ub_constraints(
        K,
        n_nodes,
        n_pairs,
        n_arcs,
        n_x,
        n_Q,
        arc_idx_matrix,
        arcs_i,
        arcs_j,
        service_arc_ids,
        demand,
        depot_end,
        float(M_order),
        float(M_load),
    )
    n_ub = int(b_ub.shape[0])
    A_ub = csr_matrix((ub_vals, (ub_rows, ub_cols)), shape=(n_ub, n_vars))

    return LPComponents(
        c_obj=c_obj,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        base_bounds=base_bounds,
        n_x=n_x,
        n_Q=n_Q,
        n_u=n_u,
        n_vars=n_vars,
        n_eq=n_eq,
        n_ub=n_ub,
    )


def apply_fixed_arc_bounds(
    bounds: np.ndarray,
    fixed_to_1: set[tuple[int, int, int]],
    fixed_to_0: set[tuple[int, int, int]],
    *,
    K: int,
    n_nodes: int,
    n_arcs: int,
    arc_idx_matrix: np.ndarray,
) -> np.ndarray:
    if fixed_to_1 & fixed_to_0:
        raise ValueError("A branch fixes the same arc to both 0 and 1.")

    out = bounds.copy()
    for i, j, k in fixed_to_1:
        if 0 <= i < n_nodes and 0 <= j < n_nodes and 0 <= k < K:
            arc_id = arc_idx_matrix[i, j]
            if arc_id >= 0:
                vidx = k * n_arcs + arc_id
                out[vidx, 0] = 1.0
                out[vidx, 1] = 1.0

    for i, j, k in fixed_to_0:
        if 0 <= i < n_nodes and 0 <= j < n_nodes and 0 <= k < K:
            arc_id = arc_idx_matrix[i, j]
            if arc_id >= 0:
                vidx = k * n_arcs + arc_id
                out[vidx, 0] = 0.0
                out[vidx, 1] = 0.0

    return out
