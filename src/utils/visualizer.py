from src.models.solution import PDPSolution
from src.models.node import NodeType

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

class PDPVisualizer:
    """
    Tiện ích trực quan hóa (vẽ đồ thị) lộ trình của các xe trong lời giải PDP (Không Time Window).
    """
    @staticmethod
    def plot_solution(solution: PDPSolution, save_path: str = None):
        """
        Vẽ đồ thị mạng lưới đường đi của các xe và lưu lại hoặc hiển thị.
        """
        if plt is None:
            print("[Warning] Chưa cài đặt thư viện 'matplotlib'. Vui lòng chạy 'pip install matplotlib' để vẽ lời giải.")
            return

        instance = solution.instance
        plt.figure(figsize=(10, 8))
        
        # 1. Vẽ tất cả các nút
        # Vẽ Depot xuất phát
        depot = instance.nodes.get(0)
        if depot:
            plt.scatter(depot.x, depot.y, color='red', marker='*', s=250, zorder=5, label='Depot (Kho)')
            plt.text(depot.x + 1, depot.y + 1, "DEPOT", fontsize=10, weight='bold', color='darkred')

        # Vẽ các điểm Pickup và Delivery
        for req_id, req in instance.requests.items():
            p = req.pickup_node
            d = req.delivery_node
            
            # Vẽ Pickup
            plt.scatter(p.x, p.y, color='green', marker='o', s=100, zorder=4)
            plt.text(p.x + 0.8, p.y + 0.8, f"P{req_id}", fontsize=8, weight='bold', color='darkgreen')
            
            # Vẽ Delivery
            plt.scatter(d.x, d.y, color='blue', marker='s', s=100, zorder=4)
            plt.text(d.x + 0.8, d.y + 0.8, f"D{req_id}", fontsize=8, weight='bold', color='darkblue')
            
            # Vẽ đường đứt quãng nối điểm Pickup và Delivery
            plt.plot([p.x, d.x], [p.y, d.y], color='gray', linestyle=':', alpha=0.5, zorder=1)

        # 2. Vẽ lộ trình di chuyển của từng xe
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        total_cost = solution.calculate_total_cost()  # Tính 1 lần duy nhất
        
        for idx, (vehicle_id, route) in enumerate(solution.routes.items()):
            if not route or len(route) < 2:
                continue
            
            color = colors[idx % len(colors)]
            
            x_coords = []
            y_coords = []
            for node_id in route:
                node = instance.nodes[node_id]
                x_coords.append(node.x)
                y_coords.append(node.y)

            # Vẽ đường lộ trình
            plt.plot(x_coords, y_coords, color=color, linewidth=2.5, alpha=0.8, zorder=2,
                     label=f'Vehicle {vehicle_id}')

            # Mũi tên chỉ hướng
            for i in range(len(route) - 1):
                n_from = instance.nodes[route[i]]
                n_to = instance.nodes[route[i+1]]
                
                dx = n_to.x - n_from.x
                dy = n_to.y - n_from.y
                
                if abs(dx) > 1e-2 or abs(dy) > 1e-2:
                    plt.annotate('', xy=(n_from.x + dx*0.6, n_from.y + dy*0.6), 
                                 xytext=(n_from.x, n_from.y),
                                 arrowprops=dict(arrowstyle="->", color=color, lw=1.5, ls='-'),
                                 zorder=3)

        plt.title(f"Trực Quan Hóa Lộ Trình PDP (Không Time Window) - Instance: {instance.name}\n"
                  f"Tổng quãng đường: {solution.calculate_total_cost():.2f}", 
                  fontsize=14, weight='bold', pad=15)
        
        plt.xlabel("Tọa độ X", fontsize=11, labelpad=10)
        plt.ylabel("Tọa độ Y", fontsize=11, labelpad=10)
        
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend(loc='upper right', frameon=True, shadow=True)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300)
            print(f"[Visualizer] Đã lưu đồ thị vào: {save_path}")
        else:
            plt.show()
