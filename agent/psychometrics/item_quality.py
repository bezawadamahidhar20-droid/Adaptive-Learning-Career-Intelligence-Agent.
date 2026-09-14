"""
Item Quality & Psychometric Metadata Engine
Validates item calibration parameters, cognitive levels, exposure limits, and versioning.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

VALID_COGNITIVE_LEVELS = {"recall", "understand", "apply", "analyze", "evaluate"}
VALID_STATUSES = {"draft", "reviewed", "pilot", "calibrated", "active", "retired"}


@dataclass
class ItemMetadata:
    item_id: str
    concept_id: str
    difficulty: float          # b in [-3.0, 3.0]
    discrimination: float      # a in [0.2, 3.0]
    guessing: float            # c in [0.0, 0.40]
    cognitive_level: str       # 'recall', 'understand', 'apply', 'analyze', 'evaluate'
    estimated_seconds: int     # Expected completion time
    prerequisites: List[str]   # Prerequisite concept IDs
    exposure_limit: float      # Max test exposure rate (e.g. 0.25)
    version: int               # Monotonic version
    status: str                # 'active', 'calibrated', 'pilot', etc.
    distractor_rationales: Optional[Dict[str, str]] = None

    def validate(self) -> List[str]:
        """Returns validation errors if any."""
        errors = []
        if not self.item_id:
            errors.append("item_id must not be empty.")
        if not self.concept_id:
            errors.append("concept_id must not be empty.")
        if not (-3.5 <= self.difficulty <= 3.5):
            errors.append(f"difficulty {self.difficulty} out of range [-3.5, 3.5].")
        if not (0.1 <= self.discrimination <= 4.0):
            errors.append(f"discrimination {self.discrimination} out of range [0.1, 4.0].")
        if not (0.0 <= self.guessing <= 0.5):
            errors.append(f"guessing {self.guessing} out of range [0.0, 0.5].")
        if self.cognitive_level not in VALID_COGNITIVE_LEVELS:
            errors.append(f"cognitive_level '{self.cognitive_level}' invalid. Allowed: {VALID_COGNITIVE_LEVELS}")
        if self.status not in VALID_STATUSES:
            errors.append(f"status '{self.status}' invalid. Allowed: {VALID_STATUSES}")
        if not (0.05 <= self.exposure_limit <= 1.0):
            errors.append(f"exposure_limit {self.exposure_limit} out of range [0.05, 1.0].")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
