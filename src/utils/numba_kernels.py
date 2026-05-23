"""Numba kernels shared by PDP parsing/model/heuristic components.

The formulas mirror the kernels in the root-level pdp_bnb_solver.py.
"""

import numpy as np

from .numba_support import njit


@njit(cache=True)
def _numba_compute_dist_matrix(x, y):
    n = x.shape[0]
    dist = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(n):
            if i != j:
                dx = x[i] - x[j]
                dy = y[i] - y[j]
                dist[i, j] = (dx * dx + dy * dy) ** 0.5
    return dist


@njit(cache=True)
def _numba_build_objective(dist, arcs_i, arcs_j, vehicle_count, n_arcs, n_vars):
    c_obj = np.zeros(n_vars, dtype=np.float64)
    for k in range(vehicle_count):
        base = k * n_arcs
        for arc_id in range(n_arcs):
            c_obj[base + arc_id] = dist[arcs_i[arc_id], arcs_j[arc_id]]
    return c_obj


@njit(cache=True)
def _numba_fractional_variables(x_lp, arcs_i, arcs_j, vehicle_count, n_arcs, tol):
    max_count = x_lp.shape[0]
    out_i = np.empty(max_count, dtype=np.int64)
    out_j = np.empty(max_count, dtype=np.int64)
    out_k = np.empty(max_count, dtype=np.int64)
    out_val = np.empty(max_count, dtype=np.float64)
    count = 0

    for k in range(vehicle_count):
        base = k * n_arcs
        for arc_id in range(n_arcs):
            val = x_lp[base + arc_id]
            if tol < val < 1.0 - tol:
                out_i[count] = arcs_i[arc_id]
                out_j[count] = arcs_j[arc_id]
                out_k[count] = k
                out_val[count] = val
                count += 1

    return out_i[:count], out_j[:count], out_k[:count], out_val[:count]


@njit(cache=True)
def _numba_build_variable_bounds(K, nA, nV, n_vars, capacity, depot_end):
    n_x = K * nA
    n_Q = K * nV
    lb = np.zeros(n_vars, dtype=np.float64)
    ub = np.ones(n_vars, dtype=np.float64)

    for k in range(K):
        for i in range(nV):
            q_idx = n_x + k * nV + i
            u_idx = n_x + n_Q + k * nV + i
            if i == 0 or i == depot_end:
                ub[q_idx] = 0.0
                ub[u_idx] = 0.0
            else:
                ub[q_idx] = capacity
                ub[u_idx] = nV

    return lb, ub


@njit(cache=True)
def _numba_route_cost(route, route_len, dist):
    total = 0.0
    for idx in range(route_len - 1):
        total += dist[route[idx], route[idx + 1]]
    return total


@njit(cache=True)
def _numba_local_route_cost(route, route_len, dist):
    if route_len == 0:
        return 0.0

    total = dist[0, route[0]]
    for idx in range(route_len - 1):
        total += dist[route[idx], route[idx + 1]]
    total += dist[route[route_len - 1], 0]
    return total


@njit(cache=True)
def _numba_local_route_feasible(route, route_len, demands, pickup_of, capacity):
    n = demands.shape[0]
    picked = np.zeros(n, dtype=np.bool_)
    load = 0.0

    for idx in range(route_len):
        node = route[idx]
        if node <= 0 or node >= n:
            return False

        pickup = pickup_of[node]
        if pickup != -1:
            if pickup <= 0 or pickup >= n:
                return False
            if not picked[pickup]:
                return False
        else:
            picked[node] = True

        load += demands[node]
        if load < -1e-8 or load > capacity + 1e-8:
            return False

    return abs(load) <= 1e-8


@njit(cache=True)
def _numba_count_pickups_in_route_arr(route, route_len, n_pairs):
    count = 0
    for idx in range(route_len):
        node = route[idx]
        if 1 <= node <= n_pairs:
            count += 1
    return count


@njit(cache=True)
def _numba_is_route_feasible_fast(route, route_len, demand, capacity, depot_end, n_pairs):
    if route_len < 2:
        return False
    if route[0] != 0 or route[route_len - 1] != depot_end:
        return False

    nV = demand.shape[0]
    seen = np.zeros(nV, dtype=np.bool_)
    picked = np.zeros(n_pairs + 1, dtype=np.bool_)
    load = 0.0

    for idx in range(route_len):
        node = route[idx]

        if node < 0 or node >= nV:
            return False

        if seen[node]:
            return False
        seen[node] = True

        if idx == 0 or idx == route_len - 1:
            continue

        load += demand[node]
        if load < -1e-8 or load > capacity + 1e-8:
            return False

        if 1 <= node <= n_pairs:
            picked[node] = True
        elif n_pairs < node <= 2 * n_pairs:
            pickup = node - n_pairs
            if pickup < 1 or pickup > n_pairs:
                return False
            if not picked[pickup]:
                return False

    return abs(load) <= 1e-8


@njit(cache=True)
def _numba_find_best_insertion_for_route(
    route,
    route_len,
    pickup,
    delivery,
    dist,
    demand,
    capacity,
    depot_end,
    n_pairs,
    max_pairs_per_route,
):
    current_pairs = _numba_count_pickups_in_route_arr(route, route_len, n_pairs)
    if current_pairs >= max_pairs_per_route:
        return 1e100, -1, -1
    if current_pairs + 1 > max_pairs_per_route:
        return 1e100, -1, -1

    base_cost = _numba_route_cost(route, route_len, dist)

    best_delta = 1e100
    best_pickup_pos = -1
    best_delivery_pos = -1

    route_with_pickup = np.empty(route_len + 1, dtype=np.int64)
    candidate = np.empty(route_len + 2, dtype=np.int64)

    for pickup_pos in range(1, route_len):
        idx = 0

        for t in range(pickup_pos):
            route_with_pickup[idx] = route[t]
            idx += 1

        route_with_pickup[idx] = pickup
        idx += 1

        for t in range(pickup_pos, route_len):
            route_with_pickup[idx] = route[t]
            idx += 1

        for delivery_pos in range(pickup_pos + 1, route_len + 1):
            idx2 = 0

            for t in range(delivery_pos):
                candidate[idx2] = route_with_pickup[t]
                idx2 += 1

            candidate[idx2] = delivery
            idx2 += 1

            for t in range(delivery_pos, route_len + 1):
                candidate[idx2] = route_with_pickup[t]
                idx2 += 1

            candidate_len = route_len + 2

            if not _numba_is_route_feasible_fast(
                candidate,
                candidate_len,
                demand,
                capacity,
                depot_end,
                n_pairs,
            ):
                continue

            new_cost = _numba_route_cost(candidate, candidate_len, dist)
            delta = new_cost - base_cost

            if delta < best_delta:
                best_delta = delta
                best_pickup_pos = pickup_pos
                best_delivery_pos = delivery_pos

    return best_delta, best_pickup_pos, best_delivery_pos


@njit(cache=True)
def _numba_is_route_feasible(route, route_len, demand, pair_delivery, capacity, depot_end, n_pairs):
    if route_len < 2:
        return False
    if route[0] != 0 or route[route_len - 1] != depot_end:
        return False

    nV = demand.shape[0]
    pos = np.full(nV, -1, dtype=np.int64)
    load = 0.0

    for idx in range(route_len):
        node = route[idx]
        if node < 0 or node >= nV:
            return False
        if pos[node] >= 0 and node != depot_end:
            return False
        pos[node] = idx

        if idx > 0 and idx < route_len - 1:
            load += demand[node]
            if load < -1e-8 or load > capacity + 1e-8:
                return False

    if abs(load) > 1e-8:
        return False

    for pickup in range(1, n_pairs + 1):
        delivery = pair_delivery[pickup]
        has_pickup = pos[pickup] >= 0
        has_delivery = pos[delivery] >= 0
        if has_pickup != has_delivery:
            return False
        if has_pickup and pos[pickup] >= pos[delivery]:
            return False

    return True


@njit(cache=True)
def _numba_extract_routes_from_x(
    x_lp,
    arcs_i,
    arcs_j,
    K,
    nA,
    nV,
    depot_end,
    demand,
    pair_delivery,
    capacity,
    n_pairs,
    dist,
):
    routes = np.full((K, nV + 1), -1, dtype=np.int64)
    route_lengths = np.zeros(K, dtype=np.int64)
    pickup_counts = np.zeros(nV, dtype=np.int64)
    delivery_counts = np.zeros(nV, dtype=np.int64)
    total_cost = 0.0

    for k in range(K):
        out_next = np.full(nV, -1, dtype=np.int64)
        out_count = np.zeros(nV, dtype=np.int64)
        in_count = np.zeros(nV, dtype=np.int64)
        selected_count = 0

        base = k * nA
        for arc_id in range(nA):
            if x_lp[base + arc_id] > 0.5:
                i = arcs_i[arc_id]
                j = arcs_j[arc_id]
                if out_next[i] >= 0:
                    return False, routes, route_lengths, total_cost
                out_next[i] = j
                out_count[i] += 1
                in_count[j] += 1
                selected_count += 1

        if selected_count == 0:
            continue

        if out_count[0] != 1 or in_count[depot_end] != 1:
            return False, routes, route_lengths, total_cost

        for node in range(nV):
            if out_count[node] > 1 or in_count[node] > 1:
                return False, routes, route_lengths, total_cost

        visited = np.zeros(nV, dtype=np.bool_)
        cur = 0
        route_len = 0
        used_arcs = 0

        while True:
            if route_len >= nV + 1:
                return False, routes, route_lengths, total_cost
            routes[k, route_len] = cur
            route_len += 1

            if cur == depot_end:
                break

            if visited[cur]:
                return False, routes, route_lengths, total_cost
            visited[cur] = True

            nxt = out_next[cur]
            if nxt < 0:
                return False, routes, route_lengths, total_cost
            cur = nxt
            used_arcs += 1

        if used_arcs != selected_count:
            return False, routes, route_lengths, total_cost

        if not _numba_is_route_feasible(
            routes[k],
            route_len,
            demand,
            pair_delivery,
            capacity,
            depot_end,
            n_pairs,
        ):
            return False, routes, route_lengths, total_cost

        route_lengths[k] = route_len
        total_cost += _numba_route_cost(routes[k], route_len, dist)

        for idx in range(1, route_len - 1):
            node = routes[k, idx]
            if node >= 1 and node <= n_pairs:
                pickup_counts[node] += 1
            elif node > n_pairs and node <= 2 * n_pairs:
                delivery_counts[node] += 1

    for pickup in range(1, n_pairs + 1):
        delivery = pair_delivery[pickup]
        if pickup_counts[pickup] != 1 or delivery_counts[delivery] != 1:
            return False, routes, route_lengths, total_cost

    return True, routes, route_lengths, total_cost


@njit(cache=True)
def _numba_build_eq_constraints(K, nV, nP, nA, arc_idx_matrix, depot_end):
    service_arc_degree = nV - 2
    n_eq = 2 * nP + 2 * nP * K + nP * K + K
    max_nnz = (8 * nP * K + 2 * K) * service_arc_degree

    rows = np.empty(max_nnz, dtype=np.int64)
    cols = np.empty(max_nnz, dtype=np.int64)
    vals = np.empty(max_nnz, dtype=np.float64)
    rhs = np.zeros(n_eq, dtype=np.float64)

    pos = 0
    row_id = 0

    # (C1) Pickup assignment.
    for p_idx in range(nP):
        i = p_idx + 1
        for k in range(K):
            base = k * nA
            for j in range(nV):
                arc_id = arc_idx_matrix[i, j]
                if arc_id >= 0:
                    rows[pos] = row_id
                    cols[pos] = base + arc_id
                    vals[pos] = 1.0
                    pos += 1
        rhs[row_id] = 1.0
        row_id += 1

    # (C1b) Delivery assignment.
    for d_idx in range(nP):
        i = nP + d_idx + 1
        for k in range(K):
            base = k * nA
            for j in range(nV):
                arc_id = arc_idx_matrix[i, j]
                if arc_id >= 0:
                    rows[pos] = row_id
                    cols[pos] = base + arc_id
                    vals[pos] = 1.0
                    pos += 1
        rhs[row_id] = 1.0
        row_id += 1

    # (C4) Flow conservation for service nodes.
    for service_idx in range(2 * nP):
        i = service_idx + 1
        for k in range(K):
            base = k * nA
            for j in range(nV):
                arc_id = arc_idx_matrix[i, j]
                if arc_id >= 0:
                    rows[pos] = row_id
                    cols[pos] = base + arc_id
                    vals[pos] = 1.0
                    pos += 1
            for j in range(nV):
                arc_id = arc_idx_matrix[j, i]
                if arc_id >= 0:
                    rows[pos] = row_id
                    cols[pos] = base + arc_id
                    vals[pos] = -1.0
                    pos += 1
            row_id += 1

    # (C5) Same-vehicle pickup-delivery coupling.
    for p_idx in range(nP):
        i_p = p_idx + 1
        i_d = nP + p_idx + 1
        for k in range(K):
            base = k * nA
            for j in range(nV):
                arc_id = arc_idx_matrix[i_p, j]
                if arc_id >= 0:
                    rows[pos] = row_id
                    cols[pos] = base + arc_id
                    vals[pos] = 1.0
                    pos += 1
            for j in range(nV):
                arc_id = arc_idx_matrix[i_d, j]
                if arc_id >= 0:
                    rows[pos] = row_id
                    cols[pos] = base + arc_id
                    vals[pos] = -1.0
                    pos += 1
            row_id += 1

    # Depot balance for each vehicle.
    for k in range(K):
        base = k * nA
        for j in range(nV):
            arc_id = arc_idx_matrix[0, j]
            if arc_id >= 0:
                rows[pos] = row_id
                cols[pos] = base + arc_id
                vals[pos] = 1.0
                pos += 1
        for i in range(nV):
            arc_id = arc_idx_matrix[i, depot_end]
            if arc_id >= 0:
                rows[pos] = row_id
                cols[pos] = base + arc_id
                vals[pos] = -1.0
                pos += 1
        row_id += 1

    return rows[:pos], cols[:pos], vals[:pos], rhs


@njit(cache=True)
def _numba_build_ub_constraints(
    K,
    nV,
    nP,
    nA,
    n_x,
    n_Q,
    arc_idx_matrix,
    arcs_i,
    arcs_j,
    service_arc_ids,
    demand,
    depot_end,
    M_order,
    M_load,
):
    service_arc_degree = nV - 2
    n_service_arcs = service_arc_ids.shape[0]
    n_symmetry = max(0, K - 1)
    n_degree_tightening = 2 * nV * K
    n_ub = (
        2 * K
        + 2 * n_symmetry
        + n_degree_tightening
        + nP * K
        + n_service_arcs * K
        + nA * K
    )
    max_nnz = (
        2 * K * service_arc_degree
        + 2 * n_symmetry * service_arc_degree
        + 2 * n_symmetry * nA
        + 2 * nV * K * nV
        + nP * K * nV
        + 3 * n_service_arcs * K
        + 3 * nA * K
    )

    rows = np.empty(max_nnz, dtype=np.int64)
    cols = np.empty(max_nnz, dtype=np.int64)
    vals = np.empty(max_nnz, dtype=np.float64)
    rhs = np.empty(n_ub, dtype=np.float64)

    pos = 0
    row_id = 0

    # (C2) Start depot degree.
    for k in range(K):
        base = k * nA
        for j in range(nV):
            arc_id = arc_idx_matrix[0, j]
            if arc_id >= 0:
                rows[pos] = row_id
                cols[pos] = base + arc_id
                vals[pos] = 1.0
                pos += 1
        rhs[row_id] = 1.0
        row_id += 1

    # (C3) End depot degree.
    for k in range(K):
        base = k * nA
        for i in range(nV):
            arc_id = arc_idx_matrix[i, depot_end]
            if arc_id >= 0:
                rows[pos] = row_id
                cols[pos] = base + arc_id
                vals[pos] = 1.0
                pos += 1
        rhs[row_id] = 1.0
        row_id += 1

    # (C3b) used_k >= used_{k+1}.
    for k in range(K - 1):
        base = k * nA
        next_base = (k + 1) * nA
        for j in range(nV):
            arc_id = arc_idx_matrix[0, j]
            if arc_id >= 0:
                rows[pos] = row_id
                cols[pos] = base + arc_id
                vals[pos] = -1.0
                pos += 1
        for j in range(nV):
            arc_id = arc_idx_matrix[0, j]
            if arc_id >= 0:
                rows[pos] = row_id
                cols[pos] = next_base + arc_id
                vals[pos] = 1.0
                pos += 1
        rhs[row_id] = 0.0
        row_id += 1

    # (C3c) load symmetry breaking.
    for k in range(K - 1):
        base = k * nA
        next_base = (k + 1) * nA
        for arc_id in range(nA):
            rows[pos] = row_id
            cols[pos] = base + arc_id
            vals[pos] = -1.0
            pos += 1
        for arc_id in range(nA):
            rows[pos] = row_id
            cols[pos] = next_base + arc_id
            vals[pos] = 1.0
            pos += 1
        rhs[row_id] = 0.0
        row_id += 1

    # (C4b) One outgoing arc per node and vehicle.
    for k in range(K):
        base = k * nA
        for i in range(nV):
            for j in range(nV):
                arc_id = arc_idx_matrix[i, j]
                if arc_id >= 0:
                    rows[pos] = row_id
                    cols[pos] = base + arc_id
                    vals[pos] = 1.0
                    pos += 1
            rhs[row_id] = 1.0
            row_id += 1

    # (C4b) One incoming arc per node and vehicle.
    for k in range(K):
        base = k * nA
        for i in range(nV):
            for j in range(nV):
                arc_id = arc_idx_matrix[j, i]
                if arc_id >= 0:
                    rows[pos] = row_id
                    cols[pos] = base + arc_id
                    vals[pos] = 1.0
                    pos += 1
            rhs[row_id] = 1.0
            row_id += 1

    # (C6) Pair precedence.
    for p_idx in range(nP):
        i_p = p_idx + 1
        i_d = nP + p_idx + 1
        for k in range(K):
            base = k * nA
            rows[pos] = row_id
            cols[pos] = n_x + n_Q + k * nV + i_p
            vals[pos] = 1.0
            pos += 1

            rows[pos] = row_id
            cols[pos] = n_x + n_Q + k * nV + i_d
            vals[pos] = -1.0
            pos += 1

            for j in range(nV):
                arc_id = arc_idx_matrix[i_p, j]
                if arc_id >= 0:
                    rows[pos] = row_id
                    cols[pos] = base + arc_id
                    vals[pos] = M_order
                    pos += 1
            rhs[row_id] = M_order - 1.0
            row_id += 1

    # MTZ order constraints on service-to-service arcs.
    for service_pos in range(n_service_arcs):
        arc_id = service_arc_ids[service_pos]
        i = arcs_i[arc_id]
        j = arcs_j[arc_id]
        for k in range(K):
            rows[pos] = row_id
            cols[pos] = n_x + n_Q + k * nV + i
            vals[pos] = 1.0
            pos += 1

            rows[pos] = row_id
            cols[pos] = n_x + n_Q + k * nV + j
            vals[pos] = -1.0
            pos += 1

            rows[pos] = row_id
            cols[pos] = k * nA + arc_id
            vals[pos] = M_order
            pos += 1

            rhs[row_id] = M_order - 1.0
            row_id += 1

    # (C7) Load update.
    for arc_id in range(nA):
        i = arcs_i[arc_id]
        j = arcs_j[arc_id]
        dj = demand[j]
        for k in range(K):
            rows[pos] = row_id
            cols[pos] = n_x + k * nV + i
            vals[pos] = 1.0
            pos += 1

            rows[pos] = row_id
            cols[pos] = n_x + k * nV + j
            vals[pos] = -1.0
            pos += 1

            rows[pos] = row_id
            cols[pos] = k * nA + arc_id
            vals[pos] = M_load
            pos += 1

            rhs[row_id] = M_load - dj
            row_id += 1

    return rows[:pos], cols[:pos], vals[:pos], rhs
