"""
Adaptive Learning & Career Intelligence Agent Orchestrator
Coordinates BKT, IRT, Bandits, Forgetting, Question Selection, and Career Analytics.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from .knowledge.bkt import (
    BKTKnowledgeTracer,
    BKTParameters,
    load_concept_params,
    load_calibration_metadata,
    default_calibration_path,
)

# Fallback weight given to the IRT ability estimate when the calibration artifact carries
# no fitted blend weight. Derived offline in agent/analytics/train_calibration.py.
DEFAULT_IRT_BLEND_WEIGHT = 0.3
from .knowledge.irt import IRTModel
from .knowledge.forgetting import ForgettingEngine
from .bandit.epsilon_greedy import EpsilonGreedyBandit
from .bandit.contextual_bandit import LinUCBContextualBandit
from .assessment.question_selector import AdaptiveQuestionSelector
from .assessment.assignment_builder import AssignmentBuilder
from .career.role_matcher import RoleMatcher, ROLE_REGISTRY
from .career.skill_gap import SkillGapAnalyzer, CareerAnalysisReport

class AdaptiveLearningAgent:
    def __init__(
        self,
        question_bank_path: Optional[str] = None,
        role_matcher: Optional[RoleMatcher] = None,
        calibration_path: Optional[str] = None
    ):
        # Load question bank
        if question_bank_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            question_bank_path = os.path.join(base_dir, "data", "question_bank.json")

        self.question_bank = self._load_questions(question_bank_path)
        self.question_map = {q["id"]: q for q in self.question_bank}

        # Core intelligence components
        # Per-concept BKT parameters are loaded from the artifact produced by
        # agent/analytics/train_calibration.py; concepts without a calibrated entry
        # fall back to BKTParameters() defaults.
        self.calibration_path = calibration_path or default_calibration_path()
        self.calibrated_params: Dict[str, BKTParameters] = load_concept_params(self.calibration_path)
        self.bkt = BKTKnowledgeTracer(concept_params=self.calibrated_params)

        # Blend weight for combining BKT mastery with IRT ability, as fitted offline.
        metadata = load_calibration_metadata(self.calibration_path)
        try:
            fitted_weight = float(metadata.get("irt_blend_weight", DEFAULT_IRT_BLEND_WEIGHT))
        except (TypeError, ValueError):
            fitted_weight = DEFAULT_IRT_BLEND_WEIGHT
        self.irt_blend_weight = min(1.0, max(0.0, fitted_weight))
        self.irt = IRTModel()
        self.forgetting = ForgettingEngine()
        self.bandit = EpsilonGreedyBandit()
        self.linucb = LinUCBContextualBandit()
        self.selector = AdaptiveQuestionSelector(bandit=self.bandit)
        self.assignment_builder = AssignmentBuilder(self.question_bank, self.selector)
        self.role_matcher = role_matcher or RoleMatcher()
        self.skill_gap_analyzer = SkillGapAnalyzer(self.role_matcher)

    def _load_questions(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def initialize_student_profile(
        self,
        initial_theta: float = 0.0,
        prior_masteries: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Creates a fresh student state dictionary."""
        return {
            "theta": initial_theta,
            "concept_mastery": prior_masteries.copy() if prior_masteries else {},
            "skill_mastery": {},
            "attempt_history": [],
            "last_practiced": {},
            "total_attempts": 0,
            "correct_attempts": 0
        }

    def generate_assignment(
        self,
        student_profile: Dict[str, Any],
        total_questions: int = 25,
        target_role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Creates a personalized assignment adapted to the student's mastery profile.
        """
        target_skills = None
        if target_role:
            role = self.role_matcher.get_role(target_role)
            if role:
                target_skills = list(role.skill_weights.keys())

        return self.assignment_builder.build_assessment(
            student_theta=student_profile.get("theta", 0.0),
            concept_mastery=student_profile.get("concept_mastery", {}),
            attempt_history=student_profile.get("attempt_history", []),
            total_questions=total_questions,
            target_skills=target_skills
        )

    def process_answer(
        self,
        student_profile: Dict[str, Any],
        question_id: str,
        selected_option: int,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Processes a single question answer, updates BKT mastery, IRT theta, bandit rewards, and history.
        """
        q = self.question_map.get(question_id)
        if not q:
            raise ValueError(f"Question {question_id} not found in bank")

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        correct_option = q["answer"]
        is_correct = (selected_option == correct_option)
        concept = q.get("concept", "General")
        skill = q.get("skill", "General")
        diff = q.get("difficulty", 3)
        diff_bin = "easy" if diff <= 2 else ("medium" if diff == 3 else "hard")

        # 1. Update BKT mastery (cold start from the calibrated P(L0) for this concept)
        prior_mastery = self.bkt.get_params(concept).p_init
        current_mastery = student_profile["concept_mastery"].get(concept, prior_mastery)
        _, next_mastery = self.bkt.update_mastery(concept, current_mastery, is_correct)
        student_profile["concept_mastery"][concept] = round(next_mastery, 4)
        student_profile["last_practiced"][concept] = timestamp.isoformat()

        # 2. Recompute aggregated skill mastery
        skill_concepts = [
            item.get("concept") for item in self.question_bank
            if item.get("skill") == skill and item.get("concept")
        ]
        if skill_concepts:
            mastery_vals = [
                student_profile["concept_mastery"].get(c, self.bkt.get_params(c).p_init)
                for c in set(skill_concepts)
            ]
            student_profile["skill_mastery"][skill] = round(sum(mastery_vals) / len(mastery_vals), 4)
        else:
            student_profile["skill_mastery"][skill] = round(next_mastery, 4)

        # 3. Update IRT theta (online single step)
        current_theta = student_profile.get("theta", 0.0)
        a = q.get("irt_a", 1.0)
        b = q.get("irt_b", 0.0)
        new_theta = self.irt.single_step_theta_update(current_theta, a, b, is_correct)
        student_profile["theta"] = round(new_theta, 4)

        # 4. Update Bandit reward
        learning_gain = max(0.0, next_mastery - current_mastery)
        reward = 0.8 if is_correct else 0.3 + learning_gain
        self.bandit.update_reward(concept, diff_bin, reward)

        # 5. Record attempt
        attempt_record = {
            "question_id": question_id,
            "attempt_number": len(student_profile["attempt_history"]) + 1,
            "selected_option": selected_option,
            "correct_option": correct_option,
            "is_correct": is_correct,
            "concept": concept,
            "skill": skill,
            "difficulty": diff,
            "theta_after": round(new_theta, 4),
            "mastery_after": round(next_mastery, 4),
            "timestamp": timestamp.isoformat()
        }
        student_profile["attempt_history"].append(attempt_record)
        student_profile["total_attempts"] += 1
        if is_correct:
            student_profile["correct_attempts"] += 1

        return {
            "question_id": question_id,
            "is_correct": is_correct,
            "correct_option": correct_option,
            "explanation": q.get("explanation", ""),
            "concept": concept,
            "previous_mastery": round(current_mastery, 4),
            "updated_mastery": round(next_mastery, 4),
            "updated_theta": round(new_theta, 4)
        }

    def predict_response_probability(
        self,
        student_profile: Dict[str, Any],
        question_id: str,
        irt_weight: Optional[float] = None
    ) -> float:
        """
        Estimated probability that the student answers `question_id` correctly.

        Blends BKT concept mastery with an IRT ability estimate. Per-concept evidence is
        thin (a student answers only a couple of questions per concept), while theta
        aggregates every response so far, so the blend predicts better than either alone.
        The weight comes from the calibration artifact unless overridden.
        """
        q = self.question_map.get(question_id)
        if not q:
            raise ValueError(f"Question {question_id} not found in bank")

        concept = q.get("concept", "General")
        mastery = student_profile["concept_mastery"].get(
            concept, self.bkt.get_params(concept).p_init
        )
        mastery_probability = self.bkt.predict_correctness_probability(concept, mastery)

        weight = self.irt_blend_weight if irt_weight is None else max(0.0, min(1.0, irt_weight))
        if weight <= 0.0:
            return mastery_probability

        ability_probability = self.irt.probability_correct(
            student_profile.get("theta", 0.0),
            q.get("irt_a", 1.0),
            q.get("irt_b", 0.0),
        )
        return (weight * ability_probability) + ((1.0 - weight) * mastery_probability)

    def process_full_assessment(
        self,
        student_profile: Dict[str, Any],
        submissions: List[Tuple[str, int]] # (question_id, selected_option)
    ) -> Dict[str, Any]:
        """Processes an entire assessment submission batch."""
        results = []
        for q_id, opt in submissions:
            res = self.process_answer(student_profile, q_id, opt)
            results.append(res)

        total = len(submissions)
        correct_count = sum(1 for r in results if r["is_correct"])
        score_pct = round((correct_count / max(1, total)) * 100, 1)

        return {
            "total_questions": total,
            "correct_count": correct_count,
            "score_percentage": score_pct,
            "results": results,
            "student_profile": student_profile
        }

    def analyze_career_fit(
        self,
        student_profile: Dict[str, Any],
        role_id: str
    ) -> CareerAnalysisReport:
        """Analyzes career readiness & gaps for the student."""
        return self.skill_gap_analyzer.analyze_gaps(
            role_id=role_id,
            skill_masteries=student_profile.get("skill_mastery", {})
        )
