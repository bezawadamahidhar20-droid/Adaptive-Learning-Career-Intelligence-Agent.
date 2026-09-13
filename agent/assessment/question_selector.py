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
        w_bandit: float = 0.15,
        w_recency_penalty: float = 0.30,
        bandit: Optional[EpsilonGreedyBandit] = None
    ):
        self.w_fisher = w_fisher
        self.w_weakness = w_weakness
        self.w_novelty = w_novelty
        self.w_bandit = w_bandit
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
        Score(q) = w1*Fisher(q) + w2*Weakness(q) + w3*Novelty(q) + w4*Bandit(q) - w5*RecencyPenalty(q)
        """
        q_id = question["id"]
        concept = question.get("concept", "")
        a = question.get("irt_a", 1.0)
        b = question.get("irt_b", 0.0)
        diff = question.get("difficulty", 3)
        diff_bin = "easy" if diff <= 2 else ("medium" if diff == 3 else "hard")

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

        # 4. Bandit Policy Q-Value
        arm_key = self.bandit._get_arm_key(concept, diff_bin)
        arm_stat = self.bandit.arms.get(arm_key)
        bandit_val = arm_stat.average_reward if arm_stat else 0.5

        # 5. Recency Penalty & Spaced Repetition Cooldown
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
            self.w_novelty * novelty_score +
            self.w_bandit * bandit_val -
            self.w_recency_penalty * recency_penalty
        )

        return max(0.0, total_score)

    def explain_selection(
        self,
        question: Dict[str, Any],
        student_theta: float,
        concept_mastery: Dict[str, float],
        attempt_history: List[Dict[str, Any]],
        score: float
    ) -> str:
        """
        Generates a transparent, human-readable reason for selecting this question.
        """
        concept = question.get("concept", "General")
        skill = question.get("skill", "General")
        mastery = concept_mastery.get(concept, 0.5)
        a = question.get("irt_a", 1.0)
        b = question.get("irt_b", 0.0)
        fisher_info = IRTModel.fisher_information(student_theta, a, b)
        diff = question.get("difficulty", 3)
        diff_name = "foundational" if diff <= 2 else ("intermediate" if diff == 3 else "advanced")

        past_attempts = [att for att in attempt_history if att.get("question_id") == question["id"]]
        if past_attempts:
            return f"Selected for spaced repetition to reinforce '{concept}' (current mastery: {int(mastery * 100)}%) after previous practice."
        elif mastery < 0.45:
            return f"Selected because '{concept}' mastery is {int(mastery * 100)}% (low) and this {diff_name} question provides high diagnostic information (I={fisher_info:.2f}) at ability θ={student_theta:.2f}."
        elif mastery >= 0.75:
            return f"Selected as an {diff_name} milestone for '{concept}' (mastery: {int(mastery * 100)}%) to calibrate higher ability boundaries (difficulty b={b:.1f})."
        else:
            return f"Selected to benchmark skill '{skill}' on '{concept}' with high item discrimination (a={a:.1f}) matching ability θ={student_theta:.2f}."

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
        Filters and scores candidates, returning the top-ranked question with explainable reason.
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
        best_score, best_q = scored_pool[0]
        
        # Return a copy with selection explanation
        res = dict(best_q)
        res["selection_score"] = round(best_score, 4)
        res["selection_reason"] = self.explain_selection(
            best_q, student_theta, concept_mastery, attempt_history, best_score
        )
        return res

