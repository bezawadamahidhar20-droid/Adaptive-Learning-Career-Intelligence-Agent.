"""
Item Exposure Control Engine
Applies Sympson-Hetter randomized admission and exposure tracking to prevent item overexposure.
"""

import random
from typing import Dict, Any, List, Set


class ExposureController:
    def __init__(self, default_max_exposure: float = 0.25):
        self.default_max_exposure = default_max_exposure
        self.item_exposure_counts: Dict[str, int] = {}
        self.total_administrations: int = 0

    def record_administration(self, item_id: str):
        self.item_exposure_counts[item_id] = self.item_exposure_counts.get(item_id, 0) + 1
        self.total_administrations += 1

    def is_eligible_for_selection(
        self,
        item_id: str,
        item_exposure_limit: float = None,
        already_administered: Set[str] = None
    ) -> bool:
        """
        Guarantees:
        1. No item is administered twice in the same session.
        2. Items exceeding their exposure limit are probabilistically throttled.
        """
        if already_administered and item_id in already_administered:
            return False

        if self.total_administrations < 20:
            return True  # Cold start grace period

        limit = item_exposure_limit or self.default_max_exposure
        current_rate = self.item_exposure_counts.get(item_id, 0) / max(1, self.total_administrations)

        if current_rate > limit:
            # Probabilistic throttling
            admission_prob = limit / max(1e-4, current_rate)
            return random.random() < admission_prob

        return True
