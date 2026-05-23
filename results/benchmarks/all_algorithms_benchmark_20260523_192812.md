# All Algorithms Benchmark

Vehicle policy: `max_pairs_per_route = max(15, ceil(n_pairs / K_raw))`; `K_active = ceil(n_pairs / max_pairs_per_route)` unless overridden.

| Size | Algorithm | Requests | K active | Max pairs/route | Cost | Routes | Time | Status | Feasible |
|---:|---|---:|---:|---:|---:|---:|---:|---|---|
| 100 | greedy | 53 | 4 | 15 | 791.12 | 4 | 0.05s | ok | True |
| 100 | local_search | 53 | 4 | 15 | 778.48 | 4 | 0.65s | max_passes | True |
| 100 | alns | 53 | 4 | 15 | 791.12 | 4 | 0.01s | baseline_only | True |
| 100 | milp | 53 | 4 | 15 | 912.99 | 4 | 1.49s | skipped_large_lp | True |
