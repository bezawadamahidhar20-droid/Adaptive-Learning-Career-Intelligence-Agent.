"""
Bayesian Knowledge Tracing (BKT) Engine
Standard BKT implementation with per-concept parameter configuration and update formulas.
"""
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, field
import json
import math
import os

# Default location of the artifact produced by agent/analytics/train_calibration.py
DEFAULT_CALIBRATION_FILENAME = "calibrated_bkt_params.json"

def default_calibration_path() -> str:
    """Path to the calibrated parameter artifact shipped with the agent."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", DEFAULT_CALIBRATION_FILENAME)

@dataclass
class BKTParameters:
    p_init: float = 0.1     # P(L0): Initial knowledge
    p_transit: float = 0.2  # P(T): Probability of learning from transition
    p_guess: float = 0.2    # P(G): Probability of guessing correctly without mastery
    p_slip: float = 0.1     # P(S): Probability of slipping (incorrect despite mastery)

    def validate(self):
        for name, val in [("p_init", self.p_init), ("p_transit", self.p_transit),
                          ("p_guess", self.p_guess), ("p_slip", self.p_slip)]:
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"Parameter {name} must be in [0, 1], got {val}")
        if self.p_guess + (1.0 - self.p_slip) <= 0.0:
            raise ValueError("Degenerate guess/slip parameters")

    def to_dict(self) -> Dict[str, float]:
        return {
            "p_init": self.p_init,
            "p_transit": self.p_transit,
            "p_guess": self.p_guess,
            "p_slip": self.p_slip,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BKTParameters":
        params = cls(
            p_init=float(data["p_init"]),
            p_transit=float(data["p_transit"]),
            p_guess=float(data["p_guess"]),
            p_slip=float(data["p_slip"]),
        )
        params.validate()
        return params


def save_concept_params(
    concept_params: Dict[str, BKTParameters],
    path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Persists calibrated per-concept parameters as a JSON artifact.
    Returns the path written to.
    """
    if path is None:
        path = default_calibration_path()

    payload = {
        "version": 1,
        "metadata": metadata or {},
        "concepts": {concept: params.to_dict() for concept, params in concept_params.items()},
    }

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)

    return path


def load_concept_params(path: Optional[str] = None, strict: bool = False) -> Dict[str, BKTParameters]:
    """
    Loads calibrated per-concept parameters. Returns an empty mapping when the artifact
    is absent (so callers fall back to defaults). Malformed artifacts raise unless
    strict=False, in which case they are also skipped.
    """
    if path is None:
        path = default_calibration_path()

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        concepts = payload.get("concepts", {}) if isinstance(payload, dict) else {}
        return {concept: BKTParameters.from_dict(values) for concept, values in concepts.items()}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        if strict:
            raise
        return {}


def load_calibration_metadata(path: Optional[str] = None) -> Dict[str, Any]:
    """Returns the metadata block of a calibration artifact (empty if unavailable)."""
    if path is None:
        path = default_calibration_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("metadata", {}) if isinstance(payload, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


class BKTKnowledgeTracer:
    def __init__(self, default_params: Optional[BKTParameters] = None,
                 concept_params: Optional[Dict[str, BKTParameters]] = None):
        self.default_params = default_params or BKTParameters()
        self.concept_params = concept_params or {}

    def get_params(self, concept: str) -> BKTParameters:
        return self.concept_params.get(concept, self.default_params)

    def update_mastery(self, concept: str, current_mastery: Optional[float], is_correct: bool) -> Tuple[float, float]:
        """
        Updates knowledge state given a binary response (correct = True, incorrect = False).
        Returns: (posterior_before_transit, next_mastery)
        """
        params = self.get_params(concept)
        p_l = current_mastery if current_mastery is not None else params.p_init
        
        # Clamp input
        p_l = max(0.0001, min(0.9999, p_l))

        # Posterior given observation
        if is_correct:
            numerator = p_l * (1.0 - params.p_slip)
            denominator = numerator + (1.0 - p_l) * params.p_guess
        else:
            numerator = p_l * params.p_slip
            denominator = numerator + (1.0 - p_l) * (1.0 - params.p_guess)

        p_learned_given_obs = numerator / max(denominator, 1e-9)
        
        # Transition to next time step
        next_mastery = p_learned_given_obs + (1.0 - p_learned_given_obs) * params.p_transit
        next_mastery = max(0.001, min(0.999, next_mastery))
        
        return p_learned_given_obs, next_mastery

    def predict_correctness_probability(self, concept: str, current_mastery: float) -> float:
        """P(C_t+1) = P(L_t) * (1 - P(S)) + (1 - P(L_t)) * P(G)"""
        params = self.get_params(concept)
        p_l = max(0.0, min(1.0, current_mastery))
        return p_l * (1.0 - params.p_slip) + (1.0 - p_l) * params.p_guess
