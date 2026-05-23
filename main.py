from pathlib import Path

from src.algorithms.greedy_insertion import GreedyPairInsertionSolver
from src.algorithms.milp import MILPPDPSolver
from src.models.optimization_model import PDPLinearModel
from src.utils import NUMBA_AVAILABLE
from src.utils.parser import PDPParser


def run_pdp_showcase() -> None:
    print("=" * 60)
    print("PDP PROJECT - BASIC NUMBA COMPONENT CHECK")
    print("=" * 60)
    print(f"Numba enabled: {NUMBA_AVAILABLE}")

    root = Path(__file__).resolve().parent
    file_path = root / "data" / "pdp_100" / "pdp_100" / "lc101.txt"

    instance = PDPParser.parse_li_lim_format(file_path)
    print(
        f"Parsed instance: {instance.name} | nodes={len(instance.nodes)} | "
        f"requests={len(instance.requests)} | vehicles={instance.vehicle_count} | "
        f"capacity={instance.capacity}"
    )

    model = PDPLinearModel(instance)
    print(
        f"Model graph: n_pairs={model.n_pairs} | K={model.K} | "
        f"n_nodes={model.n_nodes} | n_arcs={model.n_arcs}"
    )
    print(f"Distance matrix shape: {model.dist.shape}")

    c, A_ub, b_ub, A_eq, b_eq, bounds, n_x = model.build_lp(log=False)
    print(
        f"LP components: vars={c.shape[0]} | x_vars={n_x} | "
        f"A_eq={A_eq.shape} | A_ub={A_ub.shape} | bounds={bounds.shape}"
    )
    print(f"RHS: b_eq={b_eq.shape} | b_ub={b_ub.shape}")

    greedy_solution = GreedyPairInsertionSolver(instance).solve()
    is_valid, errors = greedy_solution.check_feasibility()
    active_routes = sum(1 for route in greedy_solution.routes.values() if len(route) > 2)
    print(
        f"Greedy incumbent: cost={greedy_solution.calculate_total_cost():.4f} | "
        f"active_routes={active_routes} | feasible={is_valid} | errors={len(errors)}"
    )
    if errors:
        for error in errors[:5]:
            print(f"  - {error}")

    milp = MILPPDPSolver(instance, time_limit=5)
    milp.build_lp_relaxation(log=False)
    print("MILP facade: LP relaxation builder is ready.")


if __name__ == "__main__":
    run_pdp_showcase()
