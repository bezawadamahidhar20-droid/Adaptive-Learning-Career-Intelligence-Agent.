"""
Iterative Maximum A Posteriori (MAP) & MLE Ability Estimation
Estimates latent ability theta with exact convergence tolerance, prior penalties,
and Hessian-derived posterior uncertainty.
"""

import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from agent.psychometrics.irt import IRTModel, SCALE_MIN, SCALE_MAX, EPSILON


@dataclass
class AbilityEstimate:
    theta: float
    initial_theta: float
    iterations: int
    converged: bool
    observed_information: float
    prior_information: float
    total_information: float
    posterior_se: float
    response_only_se: float
    item_count: int


class MAPAbilityEstimator:
    def __init__(
        self,
        prior_mean: float = 0.0,
        prior_std: float = 1.0,
        max_iterations: int = 50,
        tolerance: float = 1e-4,
        step_damping: float = 0.8
    ):
        self.prior_mean = prior_mean
        self.prior_std = max(0.1, prior_std)
        self.prior_variance = self.prior_std ** 2
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.step_damping = step_damping

    def estimate(
        self,
        responses: List[Dict[str, Any]],
        initial_theta: float = 0.0
    ) -> AbilityEstimate:
        """
        Estimates theta from a list of response dicts:
        Each dict must contain:
          - 'difficulty' (float)
          - 'discrimination' (float, optional, default 1.0)
          - 'is_correct' (int or bool: 1/True or 0/False)
        """
        n_items = len(responses)
        if n_items == 0:
            prior_info = 1.0 / self.prior_variance
            post_se = 1.0 / math.sqrt(prior_info)
            return AbilityEstimate(
                theta=self.prior_mean,
                initial_theta=initial_theta,
                iterations=0,
                converged=True,
                observed_information=0.0,
                prior_information=prior_info,
                total_information=prior_info,
                posterior_se=post_se,
                response_only_se=float("inf"),
                item_count=0
            )

        theta = max(SCALE_MIN, min(SCALE_MAX, initial_theta))
        converged = False
        iteration = 0

        for iteration in range(1, self.max_iterations + 1):
            grad = 0.0
            hessian = 0.0  # Note: hessian is negative of information

            for r in responses:
                diff = float(r.get("difficulty", 0.0))
                disc = float(r.get("discrimination", 1.0))
                y = 1.0 if bool(r.get("is_correct")) else 0.0

                p = IRTModel.probability_correct(theta, diff, disc)
                info = (disc ** 2) * p * (1.0 - p)

                grad += disc * (y - p)
                hessian -= info

            # Add Gaussian Prior log-density derivatives
            grad -= (theta - self.prior_mean) / self.prior_variance
            hessian -= 1.0 / self.prior_variance

            # Prevent zero division
            if abs(hessian) < 1e-6:
                break

            step = grad / hessian  # delta = -grad / (-hessian) = grad / hessian
            new_theta = max(SCALE_MIN, min(SCALE_MAX, theta - self.step_damping * step))

            if abs(new_theta - theta) < self.tolerance:
                theta = new_theta
                converged = True
                break

            theta = new_theta

        # Compute final observed and posterior information at estimated theta
        observed_info = 0.0
        for r in responses:
            diff = float(r.get("difficulty", 0.0))
            disc = float(r.get("discrimination", 1.0))
            observed_info += IRTModel.fisher_information(theta, diff, disc)

        prior_info = 1.0 / self.prior_variance
        total_info = observed_info + prior_info

        posterior_se = 1.0 / math.sqrt(max(1e-4, total_info))
        response_only_se = (1.0 / math.sqrt(observed_info)) if observed_info > 1e-4 else float("inf")

        return AbilityEstimate(
            theta=round(theta, 4),
            initial_theta=initial_theta,
            iterations=iteration,
            converged=converged,
            observed_information=round(observed_info, 4),
            prior_information=round(prior_info, 4),
            total_information=round(total_info, 4),
            posterior_se=round(posterior_se, 4),
            response_only_se=round(response_only_se, 4) if not math.isinf(response_only_se) else 9.99,
            item_count=n_items
        )
