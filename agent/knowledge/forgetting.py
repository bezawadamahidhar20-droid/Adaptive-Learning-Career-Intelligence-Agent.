"""
Forgetting Curves & Spaced Repetition (SM-2 Inspired)
Models memory decay over time: p(t) = p(t0) * exp(-lambda * delta_t)
and triggers spaced reviews when knowledge falls below target thresholds.
"""
import math
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

class ForgettingEngine:
    def __init__(self, default_decay_rate: float = 0.015, review_threshold: float = 0.65):
        """
        default_decay_rate (lambda): decay constant per day.
        0.015 gives ~15% drop over 10 days of non-practice.
        review_threshold: mastery level below which spaced repetition is triggered.
        """
        self.default_decay_rate = default_decay_rate
        self.review_threshold = review_threshold

    def calculate_decayed_mastery(
        self,
        initial_mastery: float,
        last_practiced_timestamp: Optional[datetime],
        current_timestamp: Optional[datetime] = None,
        decay_rate: Optional[float] = None
    ) -> float:
        """
        Applies exponential forgetting curve:
        p(t) = p(t0) * exp(-lambda * delta_days)
        """
        if initial_mastery <= 0.0 or last_practiced_timestamp is None:
            return initial_mastery

        if current_timestamp is None:
            current_timestamp = datetime.now(timezone.utc)
            
        # Ensure both are timezone aware or both naive
        if last_practiced_timestamp.tzinfo is None and current_timestamp.tzinfo is not None:
            last_practiced_timestamp = last_practiced_timestamp.replace(tzinfo=timezone.utc)

        delta_seconds = max(0.0, (current_timestamp - last_practiced_timestamp).total_seconds())
        delta_days = delta_seconds / 86400.0

        lam = decay_rate if decay_rate is not None else self.default_decay_rate
        retention = math.exp(-lam * delta_days)
        decayed = initial_mastery * retention

        # Never decay completely to zero if once mastered (floor at 0.05)
        return max(0.05, min(1.0, decayed))

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
        decayed = self.calculate_decayed_mastery(
            current_mastery, last_practiced_timestamp, current_timestamp
        )
        needs_review = (current_mastery >= 0.5) and (decayed < self.review_threshold)
        return needs_review, decayed

    @staticmethod
    def compute_next_interval_days(repetition_number: int, ease_factor: float = 2.5) -> int:
        """
        SM-2 inspired interval generator:
        Repetition 1: 1 day
        Repetition 2: 3 days
        Repetition n: round(interval_(n-1) * ease_factor)
        """
        if repetition_number <= 1:
            return 1
        elif repetition_number == 2:
            return 3
        else:
            prev = 3
            for _ in range(3, repetition_number + 1):
                prev = int(round(prev * ease_factor))
            return prev
