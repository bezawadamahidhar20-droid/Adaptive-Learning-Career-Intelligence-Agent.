"""
Multi-Criterion Computerized Adaptive Testing (CAT) Stopping Engine
Evaluates stopping criteria across assessment types (diagnostic, benchmark, mastery, reassessment)
considering item counts, standard error, concept coverage, and critical gaps.
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

TEST_TYPE_POLICIES = {
    "diagnostic": {
        "min_items": 8,
        "max_items": 15,
        "target_se": 0.40,
        "min_coverage": 0.60
    },
    "benchmark": {
        "min_items": 15,
        "max_items": 30,
        "target_se": 0.30,
        "min_coverage": 0.80
    },
    "mastery": {
        "min_items": 8,
        "max_items": 20,
        "target_se": 0.35,
        "min_coverage": 0.80
    },
    "reassessment": {
        "min_items": 6,
        "max_items": 15,
        "target_se": 0.35,
        "min_coverage": 0.60
    }
}


@dataclass
class StoppingDecision:
    should_stop: bool
    termination_reason: str  # 'in_progress', 'target_precision_reached', 'max_items_reached', 'concept_coverage_met'
    reliability_status: str  # 'reliable', 'moderate', 'provisional'
    item_count: int
    posterior_se: float
    target_se: float
    coverage_ratio: float
    min_coverage_required: float


class CATStoppingEngine:
    def __init__(self, test_type: str = "diagnostic", custom_policy: Dict[str, Any] = None):
        self.test_type = test_type if test_type in TEST_TYPE_POLICIES else "diagnostic"
        self.policy = custom_policy or TEST_TYPE_POLICIES[self.test_type].copy()

    def evaluate_stopping(
        self,
        item_count: int,
        posterior_se: float,
        tested_concepts_count: int,
        total_target_concepts: int,
        untested_critical_concepts: int = 0
    ) -> StoppingDecision:
        """
        Evaluates formal multi-criterion stopping rule:
        stop = (N >= min_items) and [(SE <= target_se) or (N == max_items)] and (coverage >= c_min) and (no critical gaps)
        """
        min_n = self.policy["min_items"]
        max_n = self.policy["max_items"]
        target_se = self.policy["target_se"]
        min_cov = self.policy["min_coverage"]

        tot_concepts = max(1, total_target_concepts)
        cov_ratio = min(1.0, tested_concepts_count / tot_concepts)

        # 1. Hard minimum threshold
        if item_count < min_n:
            return StoppingDecision(
                should_stop=False,
                termination_reason="in_progress",
                reliability_status="provisional",
                item_count=item_count,
                posterior_se=posterior_se,
                target_se=target_se,
                coverage_ratio=cov_ratio,
                min_coverage_required=min_cov
            )

        # 2. Maximum length reached
        if item_count >= max_n:
            # Check if target SE was attained
            status = "reliable" if (posterior_se <= target_se and cov_ratio >= min_cov) else "provisional"
            return StoppingDecision(
                should_stop=True,
                termination_reason="max_items_reached",
                reliability_status=status,
                item_count=item_count,
                posterior_se=posterior_se,
                target_se=target_se,
                coverage_ratio=cov_ratio,
                min_coverage_required=min_cov
            )

        # 3. Precision + Coverage + Critical Checks met
        precision_met = (posterior_se <= target_se)
        coverage_met = (cov_ratio >= min_cov)
        no_critical_untested = (untested_critical_concepts == 0)

        if precision_met and coverage_met and no_critical_untested:
            return StoppingDecision(
                should_stop=True,
                termination_reason="target_precision_reached",
                reliability_status="reliable",
                item_count=item_count,
                posterior_se=posterior_se,
                target_se=target_se,
                coverage_ratio=cov_ratio,
                min_coverage_required=min_cov
            )

        # Still in progress
        return StoppingDecision(
            should_stop=False,
            termination_reason="in_progress",
            reliability_status="moderate" if posterior_se <= (target_se + 0.08) else "provisional",
            item_count=item_count,
            posterior_se=posterior_se,
            target_se=target_se,
            coverage_ratio=cov_ratio,
            min_coverage_required=min_cov
        )
