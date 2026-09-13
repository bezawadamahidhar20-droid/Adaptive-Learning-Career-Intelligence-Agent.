"""
Adaptive Learning & Career Intelligence Master Agent Orchestrator
Coordinates specialized sub-agents: ProfileAnalyzer, SkillAnalyzer, CareerIntelligence,
SkillGap, Dynamic Roadmap, PlacementPrep, and Adaptation with BKT/IRT core algorithms.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from .knowledge.bkt import (
    BKTKnowledgeTracer, BKTParameters, load_concept_params, load_calibration_metadata, default_calibration_path
)
from .knowledge.irt import IRTModel
from .knowledge.forgetting import ForgettingEngine
from .bandit.epsilon_greedy import EpsilonGreedyBandit
from .bandit.contextual_bandit import LinUCBContextualBandit
from .assessment.question_selector import AdaptiveQuestionSelector
from .assessment.assignment_builder import AssignmentBuilder
from .career.role_matcher import RoleMatcher, ROLE_REGISTRY
from .career.skill_gap import SkillGapAnalyzer, CareerAnalysisReport

# Specialized Agents
from .agents.profile_analyzer import ProfileAnalyzerAgent
from .agents.skill_analyzer import SkillAnalyzerAgent, StandardizedSkill
from .agents.career_agent import CareerIntelligenceAgent, ExplainableCareerFit
from .agents.skill_gap_agent import SkillGapAgent
from .agents.roadmap_agent import RoadmapAgent, RoadmapTask
from .agents.placement_agent import PlacementAgent, PlacementModule
from .agents.adaptation_agent import AdaptationAgent

DEFAULT_IRT_BLEND_WEIGHT = 0.50

class AdaptiveLearningAgent:
    def __init__(
        self,
        question_bank_path: Optional[str] = None,
        role_matcher: Optional[RoleMatcher] = None,
        calibration_path: Optional[str] = None,
        irt_blend_weight: Optional[float] = None
    ):
        # Load question bank
        if question_bank_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            question_bank_path = os.path.join(base_dir, "data", "question_bank.json")

        self.question_bank = self._load_questions(question_bank_path)
        self.question_map = {q["id"]: q for q in self.question_bank}

        # Load calibrated parameters & metadata
        cal_path = calibration_path if calibration_path is not None else default_calibration_path()
        self.calibrated_params = load_concept_params(cal_path)
        meta = load_calibration_metadata(cal_path)

        if irt_blend_weight is not None:
            try:
                raw_w = float(irt_blend_weight)
            except (ValueError, TypeError):
                raw_w = DEFAULT_IRT_BLEND_WEIGHT
        elif "irt_blend_weight" in meta:
            try:
                raw_w = float(meta["irt_blend_weight"])
            except (ValueError, TypeError):
                raw_w = DEFAULT_IRT_BLEND_WEIGHT
        else:
            raw_w = DEFAULT_IRT_BLEND_WEIGHT

        self.irt_blend_weight = max(0.0, min(1.0, raw_w))

        # Core intelligence components
        self.bkt = BKTKnowledgeTracer(concept_params=self.calibrated_params)
        self.irt = IRTModel()
        self.forgetting = ForgettingEngine()
        self.bandit = EpsilonGreedyBandit()
        self.linucb = LinUCBContextualBandit()
        self.selector = AdaptiveQuestionSelector(bandit=self.bandit)
        self.assignment_builder = AssignmentBuilder(self.question_bank, self.selector)
        self.role_matcher = role_matcher or RoleMatcher()

        # Multi-Agent Subsystems
        self.profile_analyzer = ProfileAnalyzerAgent()
        self.skill_analyzer = SkillAnalyzerAgent()
        self.career_agent = CareerIntelligenceAgent(self.role_matcher)
        self.skill_gap_agent = SkillGapAgent(self.role_matcher)
        self.roadmap_agent = RoadmapAgent()
        self.placement_agent = PlacementAgent()
        self.adaptation_agent = AdaptationAgent(self.skill_gap_agent, self.roadmap_agent)

    def _load_questions(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def predict_response_probability(
        self,
        student_profile: Dict[str, Any],
        question_id: str,
        irt_weight: Optional[float] = None
    ) -> float:
        """Blends BKT concept mastery prediction with IRT ability probability."""
        q = self.question_map.get(question_id)
        if not q:
            raise ValueError(f"Question {question_id} not found in bank")

        concept = q.get("concept", "General")
        concept_params = self.bkt.get_params(concept)
        current_m = student_profile.get("concept_mastery", {}).get(concept, concept_params.p_init)

        p_bkt = self.bkt.predict_correctness_probability(concept, current_m)
        p_irt = self.irt.probability_correct(
            student_profile.get("theta", 0.0),
            q.get("irt_a", 1.0),
            q.get("irt_b", 0.0)
        )

        if irt_weight is not None:
            try:
                w = max(0.0, min(1.0, float(irt_weight)))
            except (ValueError, TypeError):
                w = self.irt_blend_weight
        else:
            w = self.irt_blend_weight

        return (1.0 - w) * p_bkt + w * p_irt

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
        total_questions: int = 10,
        target_role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Creates a personalized assessment adapted to the student's mastery profile."""
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

        # 1. Update BKT mastery using calibrated concept parameters
        concept_params = self.bkt.get_params(concept)
        current_mastery = student_profile["concept_mastery"].get(concept, concept_params.p_init)
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

        # 3. Update IRT theta
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
            "skill": skill,
            "previous_mastery": round(current_mastery, 4),
            "updated_mastery": round(next_mastery, 4),
            "updated_theta": round(new_theta, 4)
        }

    def process_full_assessment(
        self,
        student_profile: Dict[str, Any],
        submissions: List[Tuple[str, int]]
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
