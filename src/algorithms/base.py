from abc import ABC, abstractmethod
from src.models.instance import PDPInstance
from src.models.solution import PDPSolution

class BaseSolver(ABC):
    """
    Lớp cơ sở trừu tượng (Abstract Base Class) cho tất cả các thuật toán giải PDP.
    """
    def __init__(self, instance: PDPInstance):
        """
        Khởi tạo solver với một thực thể bài toán (Instance).
        """
        self.instance = instance

    @abstractmethod
    def solve(self) -> PDPSolution:
        """
        Thực hiện giải thuật và trả về đối tượng Lời giải (PDPSolution).
        Cần được triển khai cụ thể bởi các lớp con.
        """
        pass
