import math

def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Tính khoảng cách Euclidean giữa hai điểm (x1, y1) và (x2, y2).
    """
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

def manhattan_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Tính khoảng cách Manhattan giữa hai điểm (x1, y1) và (x2, y2).
    """
    return abs(x1 - x2) + abs(y1 - y2)
