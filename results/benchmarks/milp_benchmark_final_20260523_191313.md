# PDP MILP Benchmark
Generated: 20260523_191313

## Zone A - Exact Success
| Requests | K | UB | LB | Gap | Time | Status |
|---:|---:|---:|---:|---:|---:|---|
| 3 | 1 | 47.04 | 47.04 | 0.00% | 5.4s | optimal |
| 4 | 1 | 56.31 | 56.31 | 0.00% | 70.6s | optimal |

Nhan xet: voi so request nho, Branch-and-Bound co the chung minh toi uu voi gap bang 0.

## Zone B - Exact Time Limit
| Requests | K | UB | LB | Gap | Time | Status |
|---:|---:|---:|---:|---:|---:|---|
| 5 | 2 | 58.46 | 32.90 | 43.71% | 20.0s | time_limit |
| 10 | 2 | 118.30 | 62.00 | 47.59% | 20.1s | time_limit |

Nhan xet: khi request tang, so node can duyet tang nhanh; solver van co incumbent kha thi nhung gap khong dong kip trong gioi han thoi gian.

## Zone C - Heuristic
| Size | Requests | UB | Routes | Time | Status | Feasible |
|---:|---:|---:|---:|---:|---|---|
| 106 | 53 | 912.99 | 4 | 0.0s | skipped_large_lp | True |
| 212 | 106 | 2802.16 | 8 | 0.1s | skipped_large_lp | True |
| 422 | 211 | 7893.27 | 15 | 0.6s | skipped_large_lp | True |
| 630 | 315 | 15210.41 | 21 | 1.6s | skipped_large_lp | True |
| 840 | 420 | 26834.44 | 28 | 3.7s | skipped_large_lp | True |
| 1054 | 527 | 44496.20 | 36 | 7.5s | skipped_large_lp | True |

Nhan xet: voi du lieu lon, heuristic cho nghiem kha thi nhanh va mo rong tot. Trong benchmark nay `max_lp_variables=1` duoc dung de ep nh?nh heuristic-only cho tat ca size.
