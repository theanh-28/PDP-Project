# All Algorithms Benchmark

Vehicle policy: `max_pairs_per_route = max(15, ceil(n_pairs / K_raw))`; `K_active = ceil(n_pairs / max_pairs_per_route)` unless overridden.

| Size | Algorithm | Requests | K active | Max pairs/route | Cost | Routes | Time | Status | Feasible |
|---:|---|---:|---:|---:|---:|---:|---:|---|---|
| 100 | greedy | 53 | 4 | 15 | 791.12 | 4 | 0.02s | ok | True |
| 100 | local_search | 53 | 4 | 15 | 778.48 | 4 | 0.05s | max_passes | True |
| 100 | alns | 53 | 4 | 15 | 791.12 | 4 | 0.00s | baseline_only | True |
| 100 | milp | 53 | 4 | 15 | 912.99 | 4 | 0.03s | skipped_large_lp | True |
| 200 | greedy | 106 | 8 | 15 | 2112.52 | 8 | 0.11s | ok | True |
| 200 | local_search | 106 | 8 | 15 | 2087.81 | 8 | 0.10s | max_passes | True |
| 200 | alns | 106 | 8 | 15 | 2112.52 | 8 | 0.01s | baseline_only | True |
| 200 | milp | 106 | 8 | 15 | 2802.16 | 8 | 0.09s | skipped_large_lp | True |
| 400 | greedy | 211 | 15 | 15 | 4588.70 | 15 | 0.57s | ok | True |
| 400 | local_search | 211 | 15 | 15 | 4526.93 | 15 | 0.25s | max_passes | True |
| 400 | alns | 211 | 15 | 15 | 4588.70 | 15 | 0.02s | baseline_only | True |
| 400 | milp | 211 | 15 | 15 | 7893.27 | 15 | 0.53s | skipped_large_lp | True |
| 600 | greedy | 315 | 21 | 15 | 8076.95 | 21 | 1.27s | ok | True |
| 600 | local_search | 315 | 21 | 15 | 7972.83 | 21 | 0.37s | max_passes | True |
| 600 | alns | 315 | 21 | 15 | 8076.95 | 21 | 0.03s | baseline_only | True |
| 600 | milp | 315 | 21 | 15 | 15210.41 | 21 | 1.60s | skipped_large_lp | True |
| 800 | greedy | 420 | 28 | 15 | 13352.66 | 28 | 2.58s | ok | True |
| 800 | local_search | 420 | 28 | 15 | 13173.71 | 28 | 0.48s | max_passes | True |
| 800 | alns | 420 | 28 | 15 | 13352.66 | 28 | 0.04s | baseline_only | True |
| 800 | milp | 420 | 28 | 15 | 26834.44 | 28 | 3.64s | skipped_large_lp | True |
| 1000 | greedy | 527 | 36 | 15 | 21869.08 | 36 | 4.78s | ok | True |
| 1000 | local_search | 527 | 36 | 15 | 21668.89 | 36 | 0.59s | max_passes | True |
| 1000 | alns | 527 | 36 | 15 | 21869.08 | 36 | 0.05s | baseline_only | True |
| 1000 | milp | 527 | 36 | 15 | 44496.20 | 36 | 6.99s | skipped_large_lp | True |
