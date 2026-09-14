"""
2-Parameter Logistic (2PL) Item Response Theory Model
Provides closed-form response probability and Fisher Information functions.
"""

import math
from typing import List, Dict, Any, Tuple

EPSILON = 1e-4
SCALE_MIN = -4.0
SCALE_MAX = 4.0


class IRTModel:
    @staticmethod
    def probability_correct(theta: float, difficulty: float, discrimination: float = 1.0) -> float:
        """
        Computes the 2PL IRT response probability:
        P(y=1 | theta, a, b) = 1 / (1 + exp(-a * (theta - b)))
        """
        a = max(0.1, min(4.0, discrimination))
        b = max(-4.0, min(4.0, difficulty))
        z = a * (theta - b)
        
        # Guard against exp overflow
        if z > 35.0:
            return 1.0 - EPSILON
        if z < -35.0:
            return EPSILON

        p = 1.0 / (1.0 + math.exp(-z))
        return max(EPSILON, min(1.0 - EPSILON, p))

    @staticmethod
    def fisher_information(theta: float, difficulty: float, discrimination: float = 1.0) -> float:
        """
        Computes item Fisher Information:
        I(theta, a, b) = a^2 * P(theta, a, b) * (1 - P(theta, a, b))
        """
        a = max(0.1, min(4.0, discrimination))
        p = IRTModel.probability_correct(theta, difficulty, a)
        return (a ** 2) * p * (1.0 - p)

    @staticmethod
    def test_information(theta: float, items: List[Dict[str, Any]]) -> float:
        """
        Computes cumulative test information across a collection of items:
        I_total(theta) = sum_i I_i(theta)
        """
        total_info = 0.0
        for item in items:
            diff = float(item.get("difficulty", 0.0))
            disc = float(item.get("discrimination", 1.0))
            total_info += IRTModel.fisher_information(theta, diff, disc)
        return total_info
