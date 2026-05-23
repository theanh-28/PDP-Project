# All Algorithms Benchmark Average

Vehicle policy: `max_pairs_per_route = max(15, ceil(n_pairs / K_raw))`; `K_active = ceil(n_pairs / max_pairs_per_route)` unless overridden.

The table below is averaged across all selected files for each size.

| Size | Algorithm | Files | Avg requests | Avg K active | Avg max pairs/route | Avg cost | Avg routes | Avg time | Feasible rate | Statuses |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | alns | 1 | 53.0 | 4.0 | 15.0 | 688.79 | 4.00 | 19.46s | 100.00% | completed:1 |
| 100 | greedy | 1 | 53.0 | 4.0 | 15.0 | 791.12 | 4.00 | 0.04s | 100.00% | ok:1 |
