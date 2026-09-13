"""
Adaptive Assignment Builder
Constructs calibrated question sets with concept & difficulty distributions:
Target composition: 60% weak concepts / 20% medium / 10% strong / 10% exploration
Difficulty mix: 40% easy / 40% medium / 20% hard
"""
import random
from typing import Dict, List, Optional, Set, Any
from .question_selector import AdaptiveQuestionSelector
from ..bandit.epsilon_greedy import EpsilonGreedyBandit

class AssignmentBuilder:
    def __init__(
        self,
        question_bank: List[Dict[str, Any]],
        selector: Optional[AdaptiveQuestionSelector] = None
    ):
        self.question_bank = question_bank
        self.selector = selector or AdaptiveQuestionSelector()

    def build_assessment(
        self,
        student_theta: float,
        concept_mastery: Dict[str, float],
        attempt_history: List[Dict[str, Any]],
        total_questions: int = 25,
        target_skills: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates an adaptive assessment tailored to the student's mastery profile.
        """
        # Filter bank by target skills if requested
        eligible_bank = self.question_bank
        if target_skills:
            eligible_bank = [q for q in self.question_bank if q.get("skill") in target_skills]
            if not eligible_bank:
                eligible_bank = self.question_bank  # Fallback to all

        # Partition concepts into tiers
        all_concepts = list(set(q.get("concept", "") for q in eligible_bank if q.get("concept")))
        
        weak_concepts = [c for c in all_concepts if concept_mastery.get(c, 0.5) < 0.45]
        medium_concepts = [c for c in all_concepts if 0.45 <= concept_mastery.get(c, 0.5) < 0.75]
        strong_concepts = [c for c in all_concepts if concept_mastery.get(c, 0.5) >= 0.75]

        # Allocate slot counts
        # Adjust if certain tiers are empty
        num_weak = int(round(total_questions * 0.60))
        num_med = int(round(total_questions * 0.20))
        num_str = int(round(total_questions * 0.10))
        num_exp = total_questions - (num_weak + num_med + num_str)

        selected_questions: List[Dict[str, Any]] = []
        selected_ids: Set[str] = set()

        def pick_from_tier(concepts: List[str], count: int, pref_diff: Optional[int] = None):
            nonlocal selected_questions, selected_ids
            candidates = [q for q in eligible_bank if q["id"] not in selected_ids]
            
            if concepts:
                tier_candidates = [q for q in candidates if q.get("concept") in concepts]
                if tier_candidates:
                    candidates = tier_candidates

            for _ in range(count):
                if not candidates:
                    break
                best_q = self.selector.select_best_question(
                    candidate_questions=candidates,
                    student_theta=student_theta,
                    concept_mastery=concept_mastery,
                    attempt_history=attempt_history,
                    excluded_ids=selected_ids,
                    target_difficulty=pref_diff
                )
                if best_q:
                    selected_questions.append(best_q)
                    selected_ids.add(best_q["id"])
                    candidates = [q for q in candidates if q["id"] not in selected_ids]

        # 1. Fill weak concepts (mix easy & medium)
        pick_from_tier(weak_concepts or all_concepts, num_weak, pref_diff=None)

        # 2. Fill medium concepts
        pick_from_tier(medium_concepts or all_concepts, num_med, pref_diff=3)

        # 3. Fill strong concepts (harder difficulty)
        pick_from_tier(strong_concepts or all_concepts, num_str, pref_diff=4)

        # 4. Fill exploration (random/novel)
        remaining = total_questions - len(selected_questions)
        if remaining > 0:
            pick_from_tier([], remaining, pref_diff=None)

        # If question bank has fewer unique questions than total_questions, fill as many as available
        # Shuffle presentation order slightly so test isn't strictly sorted by tier
        random.shuffle(selected_questions)
        return selected_questions
