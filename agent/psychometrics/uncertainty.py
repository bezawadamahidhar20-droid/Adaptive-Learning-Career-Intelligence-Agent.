"""
Measurement Uncertainty & Reliability Engine
Calculates posterior and response-only standard errors, raw and display credible intervals,
and classifies psychometric reliability.
"""

import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict

from agent.psychometrics.irt import SCALE_MIN, SCALE_MAX
from agent.psychometrics.estimation import AbilityEstimate


@dataclass
class AssessmentReliability:
    theta: float
    posterior_standard_error: float
    response_only_standard_error: float
    observed_information: float
    prior_information: float
    raw_interval: List[float]
    display_interval: List[float]
    scale_bounds: List[float]
    near_boundary_warning: bool
    boundary_message: Optional[str]
    item_count: int
    concept_count: int
    concept_coverage_ratio: float
    reliability_status: str  # 'reliable', 'moderate', 'provisional'
    termination_reason: str  # 'target_precision_reached', 'max_items_reached', 'concept_coverage_met', 'in_progress'
    estimation_method: str  # 'MAP'
    item_bank_version: str  # '2026.09'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MeasurementUncertainty:
    @staticmethod
    def calculate_credible_interval(
        theta: float,
        standard_error: float,
        z_score: float = 1.96
    ) -> Tuple[List[float], List[float], bool]:
        """
        Computes 95% credible interval.
        Returns:
          - raw_interval: [theta - z*se, theta + z*se]
          - display_interval: clamped to [SCALE_MIN, SCALE_MAX]
          - near_boundary: True if estimate is within 0.5 of boundary
        """
        margin = z_score * max(1e-4, standard_error)
        raw_low = theta - margin
        raw_high = theta + margin

        disp_low = max(SCALE_MIN, raw_low)
        disp_high = min(SCALE_MAX, raw_high)

        near_boundary = (theta <= (SCALE_MIN + 0.5)) or (theta >= (SCALE_MAX - 0.5))

        return (
            [round(raw_low, 3), round(raw_high, 3)],
            [round(disp_low, 2), round(disp_high, 2)],
            near_boundary
        )

    @staticmethod
    def evaluate_reliability(
        ability_estimate: AbilityEstimate,
        unique_concepts_tested: int,
        total_target_concepts: int,
        target_se: float = 0.30,
        min_items: int = 8,
        termination_reason: str = "in_progress",
        item_bank_version: str = "2026.09"
    ) -> AssessmentReliability:
        """
        Evaluates full psychometric reliability and returns a validated AssessmentReliability object.
        """
        theta = ability_estimate.theta
        post_se = ability_estimate.posterior_se
        resp_se = ability_estimate.response_only_se
        n_items = ability_estimate.item_count

        tot_concepts = max(1, total_target_concepts)
        coverage_ratio = round(min(1.0, unique_concepts_tested / tot_concepts), 3)

        raw_ci, disp_ci, near_boundary = MeasurementUncertainty.calculate_credible_interval(
            theta=theta,
            standard_error=post_se
        )

        boundary_msg = None
        if near_boundary:
            boundary_msg = (
                f"Ability estimate ({theta:+.2f}) is near the scale boundary [{SCALE_MIN}, {SCALE_MAX}]. "
                "Additional calibrated items at this frontier are recommended."
            )

        # Determine reliability status
        if n_items < min_items or coverage_ratio < 0.50:
            status = "provisional"
        elif post_se <= target_se and coverage_ratio >= 0.70 and termination_reason != "max_items_reached":
            status = "reliable"
        elif post_se <= (target_se + 0.10):
            status = "moderate"
        else:
            status = "provisional"

        return AssessmentReliability(
            theta=theta,
            posterior_standard_error=post_se,
            response_only_standard_error=resp_se,
            observed_information=ability_estimate.observed_information,
            prior_information=ability_estimate.prior_information,
            raw_interval=raw_ci,
            display_interval=disp_ci,
            scale_bounds=[SCALE_MIN, SCALE_MAX],
            near_boundary_warning=near_boundary,
            boundary_message=boundary_msg,
            item_count=n_items,
            concept_count=unique_concepts_tested,
            concept_coverage_ratio=coverage_ratio,
            reliability_status=status,
            termination_reason=termination_reason,
            estimation_method="MAP",
            item_bank_version=item_bank_version
        )
