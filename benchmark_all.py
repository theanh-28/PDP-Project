import argparse
import csv
import math
import os
import time
from copy import copy
from pathlib import Path

from src.algorithms.alns import ALNSSolver
from src.algorithms.greedy_insertion import GreedyPairInsertionSolver
from src.algorithms.local_search import LocalSearchSolver
from src.algorithms.milp import MILPPDPSolver
from src.models.instance import PDPInstance
from src.models.solution import PDPSolution
from src.utils.parser import PDPParser


DEFAULT_SIZE_FILES = {
    100: Path("data/pdp_100/pdp_100/lc101.txt"),
    200: Path("data/pdp_200/LC1_2_1.txt"),
    400: Path("data/pdp_400/LC1_4_1.txt"),
    600: Path("data/pdp_600/LC1_6_1.txt"),
    800: Path("data/pdptw800/LC1_8_1.txt"),
    1000: Path("data/pdptw1000/LC1_10_1.txt"),
}

DEFAULT_SIZE_DIRS = {
    100: Path("data/pdp_100/pdp_100"),
    200: Path("data/pdp_200"),
    400: Path("data/pdp_400"),
    600: Path("data/pdp_600"),
    800: Path("data/pdptw800"),
    1000: Path("data/pdptw1000"),
}


def resolve_max_pairs_per_route(n_pairs: int, k: int, override: int | None = None) -> int:
    if override is not None:
        return max(1, int(override))

    env_value = os.environ.get("PDP_HEURISTIC_MAX_PAIRS_PER_ROUTE")
    if env_value:
        return max(1, int(env_value))

    return max(15, math.ceil(n_pairs / max(1, k)))


def recommended_vehicle_count(n_pairs: int, k: int, max_pairs_per_route: int) -> int:
    if n_pairs <= 0:
        return 0
    return min(k, max(1, math.ceil(n_pairs / max(1, max_pairs_per_route))))


def with_vehicle_count(instance: PDPInstance, vehicle_count: int) -> PDPInstance:
    vehicle_count = min(max(1, vehicle_count), len(instance.vehicles))
    cloned = copy(instance)
    cloned.vehicles = list(instance.vehicles[:vehicle_count])
    cloned.max_vehicles = vehicle_count
    return cloned


def active_route_count(solution: PDPSolution) -> int:
    return sum(1 for route in solution.routes.values() if len(route) > 2)


def collect_instance_paths(project_root: Path, size: int, file_scope: str) -> list[Path]:
    if file_scope == "sample":
        return [project_root / DEFAULT_SIZE_FILES[size]]

    size_dir = project_root / DEFAULT_SIZE_DIRS[size]
    paths = sorted(size_dir.glob("*.txt"))
    if not paths:
        raise FileNotFoundError(f"No .txt instance files found in {size_dir}")
    return paths


def run_one_algorithm(
    algorithm: str,
    instance: PDPInstance,
    max_pairs_per_route: int,
    *,
    greedy_solution: PDPSolution | None,
    local_time_limit: float,
    local_max_passes: int,
    alns_iterations: int,
    milp_time_limit: float,
    milp_lp_time_limit: float | None,
    milp_mode: str,
) -> tuple[PDPSolution, dict]:
    start = time.perf_counter()
    status = "ok"
    ub = ""
    lb = ""
    gap = ""
    nodes = ""
    lps = ""

    if algorithm == "greedy":
        solver = GreedyPairInsertionSolver(
            instance,
            max_requests_per_vehicle=max_pairs_per_route,
            balanced_vehicle_usage=True,
        )
        solution = solver.solve()
        status = "ok" if solver.unassigned_count == 0 else "partial"

    elif algorithm == "local_search":
        if greedy_solution is None:
            greedy_solution = GreedyPairInsertionSolver(
                instance,
                max_requests_per_vehicle=max_pairs_per_route,
                balanced_vehicle_usage=True,
            ).solve()
        solver = LocalSearchSolver(
            instance,
            initial_solution=greedy_solution,
            time_limit=local_time_limit,
            max_passes=local_max_passes,
        )
        solution = solver.solve()
        status = solver.status

    elif algorithm == "alns":
        if greedy_solution is None:
            greedy_solution = GreedyPairInsertionSolver(
                instance,
                max_requests_per_vehicle=max_pairs_per_route,
                balanced_vehicle_usage=True,
            ).solve()
        solver = ALNSSolver(
            instance,
            initial_solution=greedy_solution,
            iterations=alns_iterations,
        )
        solution = solver.solve()
        status = solver.status

    elif algorithm == "milp":
        if milp_mode == "heuristic":
            max_lp_variables = 1
        elif milp_mode == "exact":
            max_lp_variables = 10**12
        else:
            max_lp_variables = None

        solver = MILPPDPSolver(
            instance,
            time_limit=milp_time_limit,
            lp_time_limit=milp_lp_time_limit,
            verbose=False,
            max_lp_variables=max_lp_variables,
        )
        solution = solver.solve()
        status = solver.status
        ub = solver.Z_UB
        lb = solver.Z_LB
        gap = solver._gap()
        nodes = solver.nodes_explored
        lps = solver.lps_solved

    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    elapsed = time.perf_counter() - start
    feasible, errors = solution.check_feasibility()
    cost = solution.calculate_total_cost()

    stats = {
        "algorithm": algorithm,
        "cost": cost,
        "routes": active_route_count(solution),
        "time_sec": elapsed,
        "status": status,
        "feasible": feasible,
        "errors": len(errors),
        "UB": ub,
        "LB": lb,
        "gap_percent": gap,
        "nodes_explored": nodes,
        "lps_solved": lps,
    }
    return solution, stats


def benchmark(args) -> list[dict]:
    project_root = Path(__file__).resolve().parent
    rows = []

    for size in args.sizes:
        instance_paths = collect_instance_paths(project_root, size, args.file_scope)
        if args.limit_files is not None:
            instance_paths = instance_paths[: args.limit_files]

        print(f"[SIZE] {size}: {len(instance_paths)} instance file(s)")

        for instance_path in instance_paths:
            instance = PDPParser.parse_li_lim_format(instance_path)

            n_pairs = len(instance.requests)
            original_k = instance.vehicle_count
            max_pairs = resolve_max_pairs_per_route(
                n_pairs,
                original_k,
                override=args.max_pairs_per_route,
            )
            min_routes = recommended_vehicle_count(n_pairs, original_k, max_pairs)
            active_k = min_routes if args.vehicle_policy == "heuristic" else original_k

            bench_instance = with_vehicle_count(instance, active_k)
            print(
                f"[DATA] size={size} file={instance_path.name} requests={n_pairs} "
                f"K_raw={original_k} K_active={active_k} "
                f"max_pairs_per_route={max_pairs}"
            )

            greedy_solution = None
            if any(name in args.algorithms for name in ("local_search", "alns")):
                greedy_solution = GreedyPairInsertionSolver(
                    bench_instance,
                    max_requests_per_vehicle=max_pairs,
                    balanced_vehicle_usage=True,
                ).solve()

            for algorithm in args.algorithms:
                print(f"  [RUN] {algorithm}")
                _solution, stats = run_one_algorithm(
                    algorithm,
                    bench_instance,
                    max_pairs,
                    greedy_solution=greedy_solution,
                    local_time_limit=args.local_time_limit,
                    local_max_passes=args.local_max_passes,
                    alns_iterations=args.alns_iterations,
                    milp_time_limit=args.milp_time_limit,
                    milp_lp_time_limit=args.milp_lp_time_limit,
                    milp_mode=args.milp_mode,
                )
                rows.append(
                    {
                        "size": size,
                        "instance": instance.name,
                        "file": str(instance_path.relative_to(project_root)),
                        "requests": n_pairs,
                        "K_raw": original_k,
                        "K_active": active_k,
                        "max_pairs_per_route": max_pairs,
                        "min_routes_by_policy": min_routes,
                        **stats,
                    }
                )

    return rows


def average(rows: list[dict], key: str) -> float:
    values = [float(row[key]) for row in rows if row[key] != ""]
    return sum(values) / len(values) if values else 0.0


def summarize_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[int, str], list[dict]] = {}
    for row in rows:
        grouped.setdefault((int(row["size"]), row["algorithm"]), []).append(row)

    summary = []
    for (size, algorithm), group in sorted(grouped.items()):
        feasible_count = sum(1 for row in group if bool(row["feasible"]))
        statuses = {}
        for row in group:
            statuses[row["status"]] = statuses.get(row["status"], 0) + 1

        summary.append(
            {
                "size": size,
                "algorithm": algorithm,
                "instances": len(group),
                "avg_requests": average(group, "requests"),
                "avg_K_raw": average(group, "K_raw"),
                "avg_K_active": average(group, "K_active"),
                "avg_max_pairs_per_route": average(group, "max_pairs_per_route"),
                "avg_cost": average(group, "cost"),
                "avg_routes": average(group, "routes"),
                "avg_time_sec": average(group, "time_sec"),
                "feasible_rate": feasible_count / len(group) if group else 0.0,
                "total_errors": sum(int(row["errors"]) for row in group),
                "statuses": "; ".join(f"{key}:{value}" for key, value in sorted(statuses.items())),
            }
        )
    return summary


def write_outputs(rows: list[dict], output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    detail_csv_path = output_dir / f"all_algorithms_benchmark_detail_{stamp}.csv"
    average_csv_path = output_dir / f"all_algorithms_benchmark_average_{stamp}.csv"
    md_path = output_dir / f"all_algorithms_benchmark_average_{stamp}.md"

    detail_fields = [
        "size",
        "instance",
        "file",
        "requests",
        "K_raw",
        "K_active",
        "max_pairs_per_route",
        "min_routes_by_policy",
        "algorithm",
        "cost",
        "routes",
        "time_sec",
        "status",
        "feasible",
        "errors",
        "UB",
        "LB",
        "gap_percent",
        "nodes_explored",
        "lps_solved",
    ]
    with detail_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = summarize_rows(rows)
    summary_fields = [
        "size",
        "algorithm",
        "instances",
        "avg_requests",
        "avg_K_raw",
        "avg_K_active",
        "avg_max_pairs_per_route",
        "avg_cost",
        "avg_routes",
        "avg_time_sec",
        "feasible_rate",
        "total_errors",
        "statuses",
    ]
    with average_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    md = ["# All Algorithms Benchmark Average\n\n"]
    md.append(
        "Vehicle policy: `max_pairs_per_route = max(15, ceil(n_pairs / K_raw))`; "
        "`K_active = ceil(n_pairs / max_pairs_per_route)` unless overridden.\n\n"
    )
    md.append("The table below is averaged across all selected files for each size.\n\n")
    md.append(
        "| Size | Algorithm | Files | Avg requests | Avg K active | "
        "Avg max pairs/route | Avg cost | Avg routes | Avg time | Feasible rate | Statuses |\n"
    )
    md.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|\n")
    for row in summary_rows:
        md.append(
            f"| {row['size']} | {row['algorithm']} | {row['instances']} | "
            f"{row['avg_requests']:.1f} | {row['avg_K_active']:.1f} | "
            f"{row['avg_max_pairs_per_route']:.1f} | {row['avg_cost']:.2f} | "
            f"{row['avg_routes']:.2f} | {row['avg_time_sec']:.2f}s | "
            f"{row['feasible_rate']:.2%} | {row['statuses']} |\n"
        )
    md_path.write_text("".join(md), encoding="utf-8")
    return detail_csv_path, average_csv_path, md_path


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark all PDP-Project algorithms.")
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[100, 200, 400, 600, 800, 1000],
        choices=sorted(DEFAULT_SIZE_FILES),
    )
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=["greedy", "local_search", "alns", "milp"],
        choices=["greedy", "local_search", "alns", "milp"],
    )
    parser.add_argument(
        "--file-scope",
        choices=["all", "sample"],
        default="all",
        help="all runs every .txt file in each size folder; sample runs one representative file.",
    )
    parser.add_argument(
        "--limit-files",
        type=int,
        default=None,
        help="Optional cap per size, useful for smoke tests.",
    )
    parser.add_argument(
        "--vehicle-policy",
        choices=["heuristic", "raw"],
        default="heuristic",
        help="heuristic limits active vehicles using the max-pairs-per-route formula.",
    )
    parser.add_argument("--max-pairs-per-route", type=int, default=None)
    parser.add_argument("--local-time-limit", type=float, default=30.0)
    parser.add_argument("--local-max-passes", type=int, default=2)
    parser.add_argument("--alns-iterations", type=int, default=100)
    parser.add_argument("--milp-time-limit", type=float, default=30.0)
    parser.add_argument("--milp-lp-time-limit", type=float, default=5.0)
    parser.add_argument(
        "--milp-mode",
        choices=["heuristic", "auto", "exact"],
        default="heuristic",
        help="heuristic forces MILP to return its greedy incumbent for large benchmark runs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/benchmarks"),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    rows = benchmark(args)
    project_root = Path(__file__).resolve().parent
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    detail_csv_path, average_csv_path, md_path = write_outputs(rows, output_dir)
    print(f"\nDetail CSV:  {detail_csv_path}")
    print(f"Average CSV: {average_csv_path}")
    print(f"Average MD:  {md_path}")


if __name__ == "__main__":
    main()
