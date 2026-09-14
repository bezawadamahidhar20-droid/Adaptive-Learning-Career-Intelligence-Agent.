"""
Forgetting Curves & Spaced Repetition (Residual Floor & Skill-Specific Decay)
Models memory decay over time:
P(L_decayed) = P_min + (P(L_base) - P_min) * exp(-lambda_k * delta_days)
and triggers spaced reviews when knowledge falls below target thresholds.
"""
import math
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Any

EPSILON = 1e-4
P_MIN_DEFAULT = 0.15
DEFAULT_DECAY_RATE = 0.015


class ForgettingEngine:
    def __init__(self, default_decay_rate: float = DEFAULT_DECAY_RATE, review_threshold: float = 0.65, p_min: float = P_MIN_DEFAULT):
        """
        default_decay_rate (lambda): base daily decay parameter.
        review_threshold: mastery level below which spaced repetition is triggered.
        p_min: residual knowledge floor representing core schema retention.
        """
        self.default_decay_rate = default_decay_rate
        self.review_threshold = review_threshold
        self.p_min = p_min

    def compute_skill_decay_rate(
        self,
        base_lambda: float = DEFAULT_DECAY_RATE,
        difficulty: float = 0.5,
        practice_count: int = 0,
        recent_accuracy: float = 0.5
    ) -> float:
        """
        Skill-specific decay rate:
        lambda_k = lambda_0 * (difficulty_factor / (1 + practice_count)) * (2.0 - recent_accuracy)
        """
        diff_factor = max(0.2, min(2.0, (difficulty + 0.5)))
        freq_damping = 1.0 / (1.0 + 0.25 * max(0, practice_count))
        acc_damping = max(0.5, min(1.8, 2.0 - max(0.0, min(1.0, recent_accuracy))))
        
        lambda_k = base_lambda * diff_factor * freq_damping * acc_damping
        return max(1e-4, min(0.5, lambda_k))

    def calculate_decayed_mastery(
        self,
        initial_mastery: float,
        last_practiced_timestamp: Optional[datetime] = None,
        current_timestamp: Optional[datetime] = None,
        decay_rate: Optional[float] = None,
        elapsed_days: Optional[float] = None,
        p_min: Optional[float] = None,
        difficulty: float = 0.5,
        practice_count: int = 0,
        recent_accuracy: float = 0.5
    ) -> float:
        """
        Applies residual exponential forgetting curve:
        P(t) = P_min + (P_base - P_min) * exp(-lambda * delta_days)
        """
        if initial_mastery <= 0.0:
            return 0.0

        floor = self.p_min if p_min is None else max(0.0, min(0.5, p_min))

        if elapsed_days is not None:
            delta_days = max(0.0, float(elapsed_days))
        elif last_practiced_timestamp is not None:
            if current_timestamp is None:
                current_timestamp = datetime.now(timezone.utc)
            if last_practiced_timestamp.tzinfo is None and current_timestamp.tzinfo is not None:
                last_practiced_timestamp = last_practiced_timestamp.replace(tzinfo=timezone.utc)
            delta_seconds = max(0.0, (current_timestamp - last_practiced_timestamp).total_seconds())
            delta_days = delta_seconds / 86400.0
        else:
            return initial_mastery

        if decay_rate is not None:
            lam = max(1e-5, decay_rate)
        else:
            lam = self.compute_skill_decay_rate(
                base_lambda=self.default_decay_rate,
                difficulty=difficulty,
                practice_count=practice_count,
                recent_accuracy=recent_accuracy
            )

        if initial_mastery > floor:
            retention = math.exp(-lam * delta_days)
            decayed = floor + (initial_mastery - floor) * retention
        else:
            decayed = initial_mastery

        return max(EPSILON, min(1.0 - EPSILON, round(decayed, 4)))

    def needs_spaced_repetition(
        self,
        current_mastery: float,
        last_practiced_timestamp: Optional[datetime],
        current_timestamp: Optional[datetime] = None
    ) -> Tuple[bool, float]:
        """
        Evaluates whether a concept requires spaced review.
        Returns: (needs_review: bool, current_decayed_mastery: float)
        """
        decayed = self.calculate_decayed_mastery(current_mastery, last_practiced_timestamp, current_timestamp)
        return (decayed < self.review_threshold), decayed

    def calculate_review_urgency(self, current_mastery: float, target_mastery: float = 0.75) -> float:
        """Returns urgency score in [0, 1]."""
        if current_mastery >= target_mastery:
            return max(0.0, 1.0 - (current_mastery - target_mastery) / max(1e-4, 1.0 - target_mastery))
        gap = target_mastery - current_mastery
        return min(1.0, 0.5 + 0.5 * (gap / target_mastery))
