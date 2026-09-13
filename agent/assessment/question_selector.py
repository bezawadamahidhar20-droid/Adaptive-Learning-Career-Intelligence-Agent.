"""
Adaptive Question Selector with Multi-Objective Optimization & CAT Fisher Information
Formula: Score(q) = w1*FisherInfo(q) + w2*WeakConceptBoost(q) + w3*Novelty(q) - w4*RecencyPenalty(q)
"""
import math
import random
from typing import Dict, List, Optional, Set, Any
from ..knowledge.irt import IRTModel
from ..bandit.epsilon_greedy import EpsilonGreedyBandit

class AdaptiveQuestionSelector:
    def __init__(
        self,
        w_fisher: float = 0.40,
        w_weakness: float = 0.35,
        w_novelty: float = 0.15,
        w_recency_penalty: float = 0.30,
        bandit: Optional[EpsilonGreedyBandit] = None
    ):
        self.w_fisher = w_fisher
        self.w_weakness = w_weakness
        self.w_novelty = w_novelty
        self.w_recency_penalty = w_recency_penalty
        self.bandit = bandit or EpsilonGreedyBandit()

    def score_question(
        self,
        question: Dict[str, Any],
        student_theta: float,
        concept_mastery: Dict[str, float],
        attempt_history: List[Dict[str, Any]], # List of past attempts
        current_attempt_index: int = 1
    ) -> float:
        """
        Calculates multi-objective priority score for a candidate question.
        """
        q_id = question["id"]
        concept = question.get("concept", "")
        a = question.get("irt_a", 1.0)
        b = question.get("irt_b", 0.0)

        # 1. Fisher Information I(theta)
        fisher_info = IRTModel.fisher_information(student_theta, a, b)
        # Normalize fisher info (max for a=1.8 is ~0.81)
        normalized_fisher = min(1.0, fisher_info / 0.75)

        # 2. Weak Concept Boost
        mastery = concept_mastery.get(concept, 0.5)
        weakness_boost = 1.0 - max(0.0, min(1.0, mastery))

        # 3. Novelty Bonus
        past_attempts_for_q = [att for att in attempt_history if att.get("question_id") == q_id]
        times_seen = len(past_attempts_for_q)
        novelty_score = 1.0 if times_seen == 0 else max(0.0, 1.0 / (1.0 + times_seen))

        # 4. Recency Penalty & Spaced Repetition Cooldown
        recency_penalty = 0.0
        if past_attempts_for_q:
            last_attempt = past_attempts_for_q[-1]
            last_idx = last_attempt.get("attempt_number", 0)
            was_correct = last_attempt.get("is_correct", False)
            attempts_ago = current_attempt_index - last_idx

            if attempts_ago <= 1:
                # Immediate repetition penalty
                recency_penalty = 1.0
            elif attempts_ago <= 3:
                # Still in cooldown
                recency_penalty = 0.6 if not was_correct else 0.4
            else:
                # Spaced reinforcement window
                recency_penalty = 0.1

        total_score = (
            self.w_fisher * normalized_fisher +
            self.w_weakness * weakness_boost +
            self.w_novelty * novelty_score -
            self.w_recency_penalty * recency_penalty
        )

        return max(0.0, total_score)

    def select_best_question(
        self,
        candidate_questions: List[Dict[str, Any]],
        student_theta: float,
        concept_mastery: Dict[str, float],
        attempt_history: List[Dict[str, Any]],
        excluded_ids: Optional[Set[str]] = None,
        target_concept: Optional[str] = None,
        target_difficulty: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Filters and scores candidates, returning the top-ranked question.
        """
        excluded = excluded_ids or set()
        pool = [q for q in candidate_questions if q["id"] not in excluded]

        if target_concept:
            concept_matched = [q for q in pool if q.get("concept") == target_concept]
            if concept_matched:
                pool = concept_matched

        if target_difficulty:
            diff_matched = [q for q in pool if q.get("difficulty") == target_difficulty]
            if diff_matched:
                pool = diff_matched

        if not pool:
            return None

        # Score candidate questions
        scored_pool = []
        for q in pool:
            score = self.score_question(
                question=q,
                student_theta=student_theta,
                concept_mastery=concept_mastery,
                attempt_history=attempt_history,
                current_attempt_index=len(attempt_history) + 1
            )
            scored_pool.append((score, q))

        # Sort descending by score
        scored_pool.sort(key=lambda item: item[0], reverse=True)
        return scored_pool[0][1]
