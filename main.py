import time
from src.utils.parser import PDPParser
from src.algorithms.greedy_insertion import GreedyPairInsertionSolver
from src.algorithms.local_search import LocalSearchSolver
from src.algorithms.alns import ALNSSolver
from src.algorithms.milp import MILPPDPSolver
from src.utils.visualizer import PDPVisualizer

def run_pdp_showcase():
    print("=" * 60)
    print("      PDP SOLVER SUITE - SKELETON DEMO (KHÔNG TIME WINDOW)      ")
    print("=" * 60)

    # 1. Đọc dữ liệu từ tệp tin thực tế trong thư mục data của dự án
    print("\n[Bước 1] Đọc dữ liệu từ tệp tin lc101.txt...")
    file_path = "data/pdp_100/pdp_100/lc101.txt"
    try:
        instance = PDPParser.parse_li_lim_format(file_path)
    except FileNotFoundError:
        import os
        base_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_path, "data", "pdp_100", "pdp_100", "lc101.txt")
        instance = PDPParser.parse_li_lim_format(file_path)

    print(f"  -> Đã tải thành công thực thể: {instance}")
    # In ra một số Request đầu tiên để kiểm tra
    print("     * Một số yêu cầu giao nhận tiêu biểu trong tệp tin:")
    sample_requests = list(instance.requests.items())[:5]
    for req_id, req in sample_requests:
        print(f"       Request {req_id}: Pickup Node {req.pickup_node.id} ({req.pickup_node.x:.1f}, {req.pickup_node.y:.1f}) -> Delivery Node {req.delivery_node.id} ({req.delivery_node.x:.1f}, {req.delivery_node.y:.1f}) | Demand: {req.demand}")

    # 2. Khởi tạo thuật toán 1: Greedy Pair Insertion (Khung xương)
    print("\n[Bước 2] Gọi thuật toán: Greedy Pair Insertion (Khung xương)...")
    greedy_solver = GreedyPairInsertionSolver(instance)
    greedy_sol = greedy_solver.solve()
    
    is_feasible, errors = greedy_sol.check_feasibility()
    print(f"  -> Kết quả Greedy:")
    print(f"     * Tổng quãng đường: {greedy_sol.calculate_total_cost():.2f}")
    print(f"     * Hợp lệ (Feasible): {is_feasible} (Lỗi: {len(errors)})")
    for v_id, route in greedy_sol.routes.items():
        print(f"     * Lộ trình Xe {v_id}: {route}")

    # 3. Khởi tạo thuật toán 2: Local Search (Khung xương)
    print("\n[Bước 3] Gọi thuật toán: Local Search (Khung xương)...")
    ls_solver = LocalSearchSolver(instance, initial_solution=greedy_sol)
    ls_sol = ls_solver.solve()
    
    is_feasible, errors = ls_sol.check_feasibility()
    print(f"  -> Kết quả Local Search:")
    print(f"     * Tổng quãng đường: {ls_sol.calculate_total_cost():.2f}")
    print(f"     * Hợp lệ (Feasible): {is_feasible}")
    for v_id, route in ls_sol.routes.items():
        print(f"     * Lộ trình Xe {v_id}: {route}")

    # 4. Khởi tạo thuật toán 3: ALNS (Khung xương)
    print("\n[Bước 4] Gọi thuật toán: ALNS (Khung xương)...")
    alns_solver = ALNSSolver(instance, initial_solution=greedy_sol, iterations=10)
    alns_sol = alns_solver.solve()
    
    is_feasible, errors = alns_sol.check_feasibility()
    print(f"  -> Kết quả ALNS:")
    print(f"     * Tổng quãng đường: {alns_sol.calculate_total_cost():.2f}")
    print(f"     * Hợp lệ (Feasible): {is_feasible}")
    for v_id, route in alns_sol.routes.items():
        print(f"     * Lộ trình Xe {v_id}: {route}")

    # 5. Khởi tạo thuật toán 4: MILP (Khung xương)
    print("\n[Bước 5] Gọi thuật toán: MILP (Khung xương)...")
    milp_solver = MILPPDPSolver(instance, time_limit=5)
    milp_sol = milp_solver.solve()
    
    is_feasible, errors = milp_sol.check_feasibility()
    print(f"  -> Kết quả MILP:")
    print(f"     * Tổng quãng đường: {milp_sol.calculate_total_cost():.2f}")
    print(f"     * Hợp lệ (Feasible): {is_feasible}")
    for v_id, route in milp_sol.routes.items():
        print(f"     * Lộ trình Xe {v_id}: {route}")

    print("\n" + "=" * 60)
    print(" DỰ ÁN SẴN SÀNG! Bạn có thể bắt đầu lập trình logic trong src/algorithms/ ")
    print("=" * 60)

if __name__ == "__main__":
    run_pdp_showcase()
