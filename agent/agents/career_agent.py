"""
Career Intelligence Agent
Computes role suitability and generates explainable career recommendations
comparing student skill levels against industry hiring benchmarks.
"""
from typing import Dict, List, Any
from dataclasses import dataclass
from ..career.role_matcher import ROLE_REGISTRY, RoleMatcher

@dataclass
class ExplainableCareerFit:
    role_id: str
    role_title: str
    suitability_score: float
    is_recommended: bool
    is_job_ready: bool
    explanation: str
    strengths: List[str]
    missing_skills: List[str]
    priority_skills_to_learn: List[str]

class CareerIntelligenceAgent:
    def __init__(self, role_matcher: RoleMatcher = None):
        self.role_matcher = role_matcher or RoleMatcher()

    def evaluate_career_fit(
        self,
        target_role_id: str,
        user_skills: Dict[str, float]
    ) -> ExplainableCareerFit:
        """
        Generates comprehensive, explainable career suitability analysis.
        """
        role = self.role_matcher.get_role(target_role_id) or self.role_matcher.get_role("data_scientist")
        
        suitability = self.role_matcher.calculate_readiness(role.role_id, user_skills)
        threshold = 75.0 if role.role_id == "data_analyst" else 78.0
        is_ready = suitability >= threshold

        strengths = []
        missing_skills = []
        priority_skills = []

        for skill, weight in role.skill_weights.items():
            current_m = user_skills.get(skill, 0.20)
            target_thresh = role.target_thresholds.get(skill, 0.75)

            if current_m >= target_thresh:
                strengths.append(f"{skill} ({int(current_m*100)}% mastery)")
            elif current_m >= 0.50:
                missing_skills.append(f"{skill} (at {int(current_m*100)}%, target: {int(target_thresh*100)}%)")
                priority_skills.append(skill)
            else:
                missing_skills.append(f"{skill} (low mastery: {int(current_m*100)}%, target: {int(target_thresh*100)}%)")
                priority_skills.insert(0, skill) # Highest priority

        # Generate Explainable Justification
        if strengths and missing_skills:
            explanation = (
                f"Recommended for {role.title} because you have proven strengths in {', '.join(strengths[:2])}, "
                f"but need focused development in {', '.join(priority_skills[:2])} to reach competitive hiring benchmark."
            )
        elif strengths:
            explanation = (
                f"Excellent alignment with {role.title}! You meet or exceed industry benchmark thresholds across "
                f"{', '.join(strengths)}. Ready for placement interviews and portfolio submission."
            )
        else:
            explanation = (
                f"Foundational phase for {role.title}. Begin by establishing core competency in {', '.join(priority_skills[:2])}."
            )

        return ExplainableCareerFit(
            role_id=role.role_id,
            role_title=role.title,
            suitability_score=suitability,
            is_recommended=suitability >= 45.0,
            is_job_ready=is_ready,
            explanation=explanation,
            strengths=strengths,
            missing_skills=missing_skills,
            priority_skills_to_learn=priority_skills
        )

    def evaluate_all_roles(self, user_skills: Dict[str, float]) -> List[ExplainableCareerFit]:
        """Evaluates suitability across all registered industry roles."""
        results = []
        for role_id in ROLE_REGISTRY.keys():
            results.append(self.evaluate_career_fit(role_id, user_skills))
        results.sort(key=lambda r: r.suitability_score, reverse=True)
        return results
