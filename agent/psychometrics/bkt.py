"""
Closed-Form Bayesian Knowledge Tracing (BKT) Model
Maintains latent concept mastery P(L_t) using closed-form Bayesian posterior updates
and classifies descriptive soft mastery levels.
"""

from typing import Dict, Any, Tuple
from agent.psychometrics.forgetting import ForgettingEngine

EPSILON = 1e-4

# Default standard BKT parameter baseline
DEFAULT_BKT_PARAMS = {
    "prior": 0.20,       # P(L_0)
    "transit": 0.15,     # P(T)
    "guess": 0.20,       # P(G)
    "slip": 0.10         # P(S)
}


class BKTModel:
    def __init__(self, params: Dict[str, float] = None, forgetting_engine: ForgettingEngine = None):
        self.params = params or DEFAULT_BKT_PARAMS.copy()
        self._validate_params()
        self.forgetting_engine = forgetting_engine or ForgettingEngine()

    def _validate_params(self):
        for k in ["prior", "transit", "guess", "slip"]:
            val = float(self.params.get(k, DEFAULT_BKT_PARAMS[k]))
            self.params[k] = max(EPSILON, min(1.0 - EPSILON, val))
        
        # Plausibility constraints on Guess and Slip
        if self.params["guess"] >= 0.5:
            self.params["guess"] = 0.45
        if self.params["slip"] >= 0.5:
            self.params["slip"] = 0.45

    def update_mastery(
        self,
        current_mastery: float,
        is_correct: bool,
        custom_params: Dict[str, float] = None
    ) -> float:
        """
        Executes exact Bayesian posterior update:
        P(L_t | y) = [P(L_t) * (1-P(S))] / [P(L_t)(1-P(S)) + (1-P(L_t))P(G)] for y=1
        P(L_{t+1}) = P(L_t | y) + (1 - P(L_t | y)) * P(T)
        """
        p = custom_params or self.params
        p_transit = p.get("transit", self.params["transit"])
        p_guess = p.get("guess", self.params["guess"])
        p_slip = p.get("slip", self.params["slip"])

        l_prev = max(EPSILON, min(1.0 - EPSILON, float(current_mastery)))

        if is_correct:
            numerator = l_prev * (1.0 - p_slip)
            denominator = numerator + (1.0 - l_prev) * p_guess
        else:
            numerator = l_prev * p_slip
            denominator = numerator + (1.0 - l_prev) * (1.0 - p_guess)

        if denominator < 1e-9:
            denominator = 1e-9

        p_learned_given_obs = numerator / denominator
        p_next = p_learned_given_obs + (1.0 - p_learned_given_obs) * p_transit

        return max(EPSILON, min(1.0 - EPSILON, round(p_next, 4)))

    @staticmethod
    def get_mastery_level(mastery: float) -> str:
        """
        Maps continuous mastery probability to descriptive soft mastery level:
          - Foundational: < 0.40
          - Developing:   0.40 <= m < 0.70
          - Proficient:   0.70 <= m < 0.85
          - Mastered:     >= 0.85
        """
        m = float(mastery)
        if m < 0.40:
            return "Foundational"
        elif m < 0.70:
            return "Developing"
        elif m < 0.85:
            return "Proficient"
        else:
            return "Mastered"
