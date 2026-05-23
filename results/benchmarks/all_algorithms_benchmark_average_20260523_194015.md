# All Algorithms Benchmark Average

Vehicle policy: `max_pairs_per_route = max(15, ceil(n_pairs / K_raw))`; `K_active = ceil(n_pairs / max_pairs_per_route)` unless overridden.

The table below is averaged across all selected files for each size.

| Size | Algorithm | Files | Avg requests | Avg K active | Avg max pairs/route | Avg cost | Avg routes | Avg time | Feasible rate | Statuses |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | greedy | 2 | 53.0 | 4.0 | 15.0 | 786.65 | 4.00 | 0.03s | 100.00% | ok:2 |
| 100 | local_search | 2 | 53.0 | 4.0 | 15.0 | 769.12 | 4.00 | 0.26s | 100.00% | max_passes:2 |
| 100 | milp | 2 | 53.0 | 4.0 | 15.0 | 937.35 | 4.00 | 0.51s | 100.00% | skipped_large_lp:2 |
