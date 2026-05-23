from abc import ABC, abstractmethod

from src.models.instance import PDPInstance
from src.models.solution import PDPSolution


class BaseSolver(ABC):
    """Base class for PDP solvers."""

    def __init__(self, instance: PDPInstance):
        self.instance = instance

    @abstractmethod
    def solve(self) -> PDPSolution:
        pass
