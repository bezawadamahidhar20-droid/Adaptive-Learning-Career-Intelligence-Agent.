"""
Item Response Theory (IRT) - 2PL Model & Fisher Information
Provides student ability (theta) estimation, item response probability,
and Fisher Information calculation for Computerized Adaptive Testing (CAT).
"""
import math
from typing import List, Tuple, Optional

class IRTModel:
    def __init__(self, default_a: float = 1.0, default_b: float = 0.0, default_c: float = 0.0):
        self.default_a = default_a # Discrimination
        self.default_b = default_b # Difficulty
        self.default_c = default_c # Guessing parameter (0 for 2PL)

    @staticmethod
    def probability_correct(theta: float, a: float = 1.0, b: float = 0.0) -> float:
        """
        Calculates P(theta) under 2PL model:
        P(theta) = 1 / (1 + exp(-a * (theta - b)))
        """
        # Protect against overflow
        exponent = -a * (theta - b)
        if exponent > 40:
            return 0.0
        elif exponent < -40:
            return 1.0
        return 1.0 / (1.0 + math.exp(exponent))

    @staticmethod
    def fisher_information(theta: float, a: float = 1.0, b: float = 0.0) -> float:
        """
        Computes Fisher Information:
        I(theta) = a^2 * P(theta) * (1 - P(theta))
        This reaches its maximum at theta = b (when item difficulty matches student ability).
        """
        p = IRTModel.probability_correct(theta, a, b)
        return (a ** 2) * p * (1.0 - p)

    @staticmethod
    def update_theta_map(
        current_theta: float,
        responses: List[Tuple[float, float, int]],  # List of (a, b, is_correct: 0 or 1)
        prior_mean: float = 0.0,
        prior_std: float = 1.0,
        learning_rate: float = 0.3,
        max_iter: int = 15
    ) -> float:
        """
        Updates student ability estimate (theta) using Maximum A Posteriori (MAP) Newton-Raphson
        or gradient descent with a standard normal prior N(prior_mean, prior_std^2).
        """
        if not responses:
            return current_theta

        theta = current_theta
        for _ in range(max_iter):
            # First and second derivative of log-posterior
            # log P(responses | theta) + log P(theta)
            # Prior gradient: -(theta - prior_mean) / prior_std^2
            # Prior hessian: -1 / prior_std^2
            
            grad = -(theta - prior_mean) / (prior_std ** 2)
            hess = -1.0 / (prior_std ** 2)

            for a, b, y in responses:
                p = IRTModel.probability_correct(theta, a, b)
                # Likelihood gradient component: a * (y - p)
                grad += a * (y - p)
                # Likelihood hessian component: -a^2 * p * (1 - p)
                hess -= (a ** 2) * p * (1.0 - p)

            if abs(hess) < 1e-6:
                break

            delta = -grad / hess
            # Step size clamping for stability
            delta = max(-0.8, min(0.8, delta))
            theta += delta

            if abs(delta) < 1e-4:
                break

        # Keep theta in a reasonable psychometric range [-4.0, +4.0]
        return max(-4.0, min(4.0, theta))

    @staticmethod
    def single_step_theta_update(current_theta: float, a: float, b: float, is_correct: bool, step_size: float = 0.25) -> float:
        """
        Lightweight online update for theta after a single question response.
        Uses gradient of log-likelihood: d/d_theta = a * (y - P(theta))
        """
        y = 1.0 if is_correct else 0.0
        p = IRTModel.probability_correct(current_theta, a, b)
        grad = a * (y - p)
        # Apply step with mild regularization toward 0
        reg = -0.05 * current_theta
        new_theta = current_theta + step_size * (grad + reg)
        return max(-4.0, min(4.0, new_theta))
