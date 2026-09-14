"""
Residual Memory Retention & Forgetting Curve Engine
Implements skill-specific exponential decay toward a residual knowledge floor:
P(L_decayed) = P_min + (P(L_base) - P_min) * exp(-lambda_k * delta_t)
"""

import math
from typing import Optional, Dict, Any

EPSILON = 1e-4
P_MIN_DEFAULT = 0.15
DEFAULT_DECAY_RATE = 0.05  # Base daily decay parameter


class ForgettingEngine:
    def __init__(self, default_decay_rate: float = DEFAULT_DECAY_RATE, p_min: float = P_MIN_DEFAULT):
        self.default_decay_rate = max(1e-5, default_decay_rate)
        self.p_min = max(0.0, min(0.5, p_min))

    def compute_skill_decay_rate(
        self,
        base_lambda: float = DEFAULT_DECAY_RATE,
        difficulty: float = 0.5,
        practice_count: int = 0,
        recent_accuracy: float = 0.5
    ) -> float:
        """
        Computes a skill-specific decay rate:
        lambda_k = lambda_0 * (difficulty_factor / (1 + practice_count)) * (2.0 - recent_accuracy)
        Frequently practiced, high-accuracy skills decay significantly slower than difficult, unpracticed concepts.
        """
        diff_factor = max(0.2, min(2.0, (difficulty + 0.5)))
        freq_damping = 1.0 / (1.0 + 0.3 * max(0, practice_count))
        acc_damping = max(0.5, min(1.8, 2.0 - max(0.0, min(1.0, recent_accuracy))))
        
        lambda_k = base_lambda * diff_factor * freq_damping * acc_damping
        return max(1e-4, min(0.5, lambda_k))

    def calculate_decayed_mastery(
        self,
        initial_mastery: float,
        elapsed_days: float,
        decay_rate: Optional[float] = None,
        p_min: Optional[float] = None,
        difficulty: float = 0.5,
        practice_count: int = 0,
        recent_accuracy: float = 0.5
    ) -> float:
        """
        Calculates mastery with residual retention floor.
        If initial_mastery <= P_min, no decay is applied below the floor.
        """
        if elapsed_days <= 0.0:
            return max(EPSILON, min(1.0 - EPSILON, initial_mastery))

        floor = self.p_min if p_min is None else max(0.0, min(0.5, p_min))
        
        if decay_rate is None:
            k = self.compute_skill_decay_rate(
                base_lambda=self.default_decay_rate,
                difficulty=difficulty,
                practice_count=practice_count,
                recent_accuracy=recent_accuracy
            )
        else:
            k = max(1e-5, decay_rate)

        # Apply residual exponential decay
        if initial_mastery > floor:
            decayed = floor + (initial_mastery - floor) * math.exp(-k * elapsed_days)
        else:
            decayed = initial_mastery  # Already at or below floor

        return max(EPSILON, min(1.0 - EPSILON, decayed))

    def calculate_review_urgency(self, current_mastery: float, target_mastery: float = 0.75) -> float:
        """
        Returns an urgency index in [0, 1] prioritizing concepts dropping below target.
        """
        if current_mastery >= target_mastery:
            return max(0.0, 1.0 - (current_mastery - target_mastery) / max(1e-4, 1.0 - target_mastery))
        gap = target_mastery - current_mastery
        return min(1.0, 0.5 + 0.5 * (gap / target_mastery))
