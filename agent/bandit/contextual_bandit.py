"""
Contextual Bandit (LinUCB with Disjoint Linear Models)
Selects question strategies conditioned on student state features:
[current_mastery, theta_ability, recent_accuracy, days_since_practice, role_relevance]
"""
import math
from typing import Dict, List, Tuple, Optional

def _invert_matrix_pure(matrix: List[List[float]]) -> List[List[float]]:
    """Pure Python Gauss-Jordan matrix inversion for d x d matrix (d small <= 6)."""
    n = len(matrix)
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(matrix)]
    
    for i in range(n):
        # Pivot
        pivot_row = max(range(i, n), key=lambda r: abs(aug[r][i]))
        aug[i], aug[pivot_row] = aug[pivot_row], aug[i]
        
        pivot_val = aug[i][i]
        if abs(pivot_val) < 1e-9:
            # Degenerate matrix, return identity fallback
            return [[1.0 if r == c else 0.0 for c in range(n)] for r in range(n)]
        
        for j in range(2 * n):
            aug[i][j] /= pivot_val
            
        for k in range(n):
            if k != i:
                factor = aug[k][i]
                for j in range(2 * n):
                    aug[k][j] -= factor * aug[i][j]
                    
    return [row[n:] for row in aug]

def _mat_vec_mul(mat: List[List[float]], vec: List[float]) -> List[float]:
    return [sum(mat[i][j] * vec[j] for j in range(len(vec))) for i in range(len(mat))]

def _dot_prod(v1: List[float], v2: List[float]) -> float:
    return sum(x * y for x, y in zip(v1, v2))


class LinUCBContextualBandit:
    def __init__(self, feature_dim: int = 5, alpha: float = 0.5):
        """
        feature_dim: dimension of context vector
        alpha: exploration coefficient for confidence bound
        """
        self.d = feature_dim
        self.alpha = alpha
        # Arm matrices: A_a (d x d), b_a (d x 1)
        self.A: Dict[str, List[List[float]]] = {}
        self.b: Dict[str, List[float]] = {}

    def _init_arm_if_absent(self, arm_id: str):
        if arm_id not in self.A:
            # A = I_d
            self.A[arm_id] = [[1.0 if i == j else 0.0 for j in range(self.d)] for i in range(self.d)]
            self.b[arm_id] = [0.0] * self.d

    def select_arm(self, context_vector: List[float], candidate_arms: List[str]) -> str:
        """
        Computes LinUCB score for each candidate arm and selects arm with max score.
        score_a = theta_a^T * x + alpha * sqrt(x^T * A_a^-1 * x)
        """
        if not candidate_arms:
            raise ValueError("Candidate arms cannot be empty")

        best_arm = candidate_arms[0]
        best_ucb = -float("inf")

        for arm in candidate_arms:
            self._init_arm_if_absent(arm)
            A_inv = _invert_matrix_pure(self.A[arm])
            
            # theta_hat = A_inv * b
            theta_hat = _mat_vec_mul(A_inv, self.b[arm])
            
            # Expected payoff
            mean_est = _dot_prod(theta_hat, context_vector)
            
            # Confidence width: sqrt(x^T * A_inv * x)
            A_inv_x = _mat_vec_mul(A_inv, context_vector)
            var_term = max(0.0, _dot_prod(context_vector, A_inv_x))
            cb = self.alpha * math.sqrt(var_term)
            
            ucb_score = mean_est + cb
            if ucb_score > best_ucb:
                best_ucb = ucb_score
                best_arm = arm

        return best_arm

    def update_arm(self, arm_id: str, context_vector: List[float], reward: float):
        """
        A_a = A_a + x * x^T
        b_a = b_a + r * x
        """
        self._init_arm_if_absent(arm_id)
        
        # Update A_a with outer product x * x^T
        for i in range(self.d):
            for j in range(self.d):
                self.A[arm_id][i][j] += context_vector[i] * context_vector[j]
                
        # Update b_a with r * x
        for i in range(self.d):
            self.b[arm_id][i] += reward * context_vector[i]
