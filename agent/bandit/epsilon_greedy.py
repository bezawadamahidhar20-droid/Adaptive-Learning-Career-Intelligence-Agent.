"""
Epsilon-Greedy Multi-Armed Bandit for Adaptive Question Selection
Balances exploration of unpracticed/novel difficulty levels and concepts
with exploitation of known weak areas where learning gains are highest.
"""
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

@dataclass
class ArmStats:
    pull_count: int = 0
    total_reward: float = 0.0

    @property
    def average_reward(self) -> float:
        if self.pull_count == 0:
            return 0.5  # Neutral optimistic prior
        return self.total_reward / self.pull_count

class EpsilonGreedyBandit:
    def __init__(self, epsilon: float = 0.15, decay_rate: float = 0.995, min_epsilon: float = 0.05):
        """
        epsilon: exploration probability
        decay_rate: decays epsilon over interactions
        min_epsilon: exploration floor
        """
        self.epsilon = epsilon
        self.decay_rate = decay_rate
        self.min_epsilon = min_epsilon
        # Arm key: (concept, difficulty_bin) e.g. ("Pandas DataFrames", "medium")
        self.arms: Dict[str, ArmStats] = {}

    def _get_arm_key(self, concept: str, difficulty_bin: str) -> str:
        return f"{concept}::{difficulty_bin}"

    def select_action(
        self,
        candidate_actions: List[Tuple[str, str]], # List of (concept, difficulty_bin)
        concept_weakness: Optional[Dict[str, float]] = None # concept -> weakness score (1 - mastery)
    ) -> Tuple[str, str]:
        """
        Selects (concept, difficulty_bin) action via epsilon-greedy.
        Weakness scores are used to bias exploitation towards high-leverage areas.
        """
        if not candidate_actions:
            raise ValueError("No candidate actions provided to bandit")

        # Exploration branch
        if random.random() < self.epsilon:
            return random.choice(candidate_actions)

        # Exploitation branch: score each candidate arm
        best_score = -float("inf")
        best_action = candidate_actions[0]

        for concept, diff in candidate_actions:
            key = self._get_arm_key(concept, diff)
            arm_stat = self.arms.get(key, ArmStats())
            
            # Base Q-value from arm statistics
            q_val = arm_stat.average_reward
            
            # Incorporate weak concept bonus if available
            weakness_bonus = 0.0
            if concept_weakness and concept in concept_weakness:
                weakness_bonus = concept_weakness[concept] * 0.4
                
            score = q_val + weakness_bonus
            if score > best_score:
                best_score = score
                best_action = (concept, diff)

        return best_action

    def update_reward(self, concept: str, difficulty_bin: str, reward: float):
        """
        Updates arm statistics given observed reward (e.g. learning gain, response quality).
        Reward should be normalized in [0, 1].
        """
        key = self._get_arm_key(concept, difficulty_bin)
        if key not in self.arms:
            self.arms[key] = ArmStats()

        self.arms[key].pull_count += 1
        self.arms[key].total_reward += reward

        # Decay exploration rate
        self.epsilon = max(self.min_epsilon, self.epsilon * self.decay_rate)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes bandit parameters and arm statistics."""
        return {
            "epsilon": self.epsilon,
            "decay_rate": self.decay_rate,
            "min_epsilon": self.min_epsilon,
            "arms": {
                k: {"pull_count": v.pull_count, "total_reward": v.total_reward}
                for k, v in self.arms.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpsilonGreedyBandit":
        """Deserializes bandit from dictionary state."""
        inst = cls(
            epsilon=float(data.get("epsilon", 0.15)),
            decay_rate=float(data.get("decay_rate", 0.995)),
            min_epsilon=float(data.get("min_epsilon", 0.05))
        )
        arms_raw = data.get("arms", {})
        for k, v in arms_raw.items():
            inst.arms[k] = ArmStats(
                pull_count=int(v.get("pull_count", 0)),
                total_reward=float(v.get("total_reward", 0.0))
            )
        return inst
