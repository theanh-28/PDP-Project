# PDP MILP Benchmark
Generated: 20260523_191406

## Zone A - Exact Success
| Requests | K | UB | LB | Gap | Time | Status |
|---:|---:|---:|---:|---:|---:|---|
| 3 | 1 | 47.04 | 47.04 | 0.00% | 5.4s | optimal |
| 4 | 1 | 56.31 | 56.31 | 0.00% | 70.6s | optimal |

Comment: with very small request counts, Branch-and-Bound proves optimality and closes the gap to 0.

## Zone B - Exact Time Limit
| Requests | K | UB | LB | Gap | Time | Status |
|---:|---:|---:|---:|---:|---:|---|
| 5 | 2 | 58.46 | 32.90 | 43.71% | 20.0s | time_limit |
| 10 | 2 | 118.30 | 62.00 | 47.59% | 20.1s | time_limit |

Comment: as request count grows, the B&B tree expands quickly; the solver keeps a feasible incumbent but the LP lower bound does not close the gap within the time limit.

## Zone C - Heuristic
| Size | Requests | UB | Routes | Time | Status | Feasible |
|---:|---:|---:|---:|---:|---|---|
| 100 | 53 | 912.99 | 4 | 0.0s | skipped_large_lp | True |
| 200 | 106 | 2802.16 | 8 | 0.1s | skipped_large_lp | True |
| 400 | 211 | 7893.27 | 15 | 0.6s | skipped_large_lp | True |
| 600 | 315 | 15210.41 | 21 | 1.6s | skipped_large_lp | True |
| 800 | 420 | 26834.44 | 28 | 3.7s | skipped_large_lp | True |
| 1000 | 527 | 44496.20 | 36 | 7.5s | skipped_large_lp | True |

Comment: for large data, the heuristic gives feasible solutions quickly and scales well. This benchmark uses max_lp_variables=1 for Zone C to force the heuristic-only path for all sizes.
