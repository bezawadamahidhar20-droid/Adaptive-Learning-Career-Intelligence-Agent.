"""
Career Intelligence - Skill Gap Analysis & Learning Recommendations
Identifies weakest career-critical skills, calculates gap magnitudes,
and generates prioritized recommendations with time-to-readiness estimates.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from .role_matcher import RoleMatcher, ROLE_REGISTRY

@dataclass
class SkillGapItem:
    skill: str
    current_mastery: float
    target_threshold: float
    importance_weight: float
    gap_magnitude: float     # weight * max(0, target - current)
    priority_rank: int
    estimated_questions_to_mastery: int
    recommendation_text: str

@dataclass
class CareerAnalysisReport:
    role_id: str
    role_title: str
    readiness_score: float
    is_job_ready: bool
    top_priority_skill: Optional[str]
    gaps: List[SkillGapItem]
    estimated_study_hours: float

class SkillGapAnalyzer:
    def __init__(self, role_matcher: Optional[RoleMatcher] = None):
        self.role_matcher = role_matcher or RoleMatcher()

    def analyze_gaps(
        self,
        role_id: str,
        skill_masteries: Dict[str, float]
    ) -> CareerAnalysisReport:
        """
        Analyzes student skill profile against role requirements.
        Rank gaps by urgency = weight * max(0, target_threshold - current_mastery)
        """
        role = self.role_matcher.get_role(role_id)
        if not role:
            raise ValueError(f"Role '{role_id}' not found in registry")

        readiness = self.role_matcher.calculate_readiness(role_id, skill_masteries)
        
        raw_gaps = []
        total_questions_needed = 0

        for skill, weight in role.skill_weights.items():
            current = skill_masteries.get(skill, 0.0)
            target = role.target_thresholds.get(skill, 0.75)
            
            delta = max(0.0, target - current)
            gap_magnitude = weight * delta
            
            # Heuristic estimate: ~25 adaptive questions per 0.3 mastery gain
            questions_needed = int(round(delta * 40))
            total_questions_needed += questions_needed

            raw_gaps.append({
                "skill": skill,
                "current": current,
                "target": target,
                "weight": weight,
                "gap": gap_magnitude,
                "questions_needed": questions_needed
            })

        # Sort descending by gap magnitude
        raw_gaps.sort(key=lambda item: item["gap"], reverse=True)

        gap_items: List[SkillGapItem] = []
        for rank, item in enumerate(raw_gaps, 1):
            curr_pct = int(round(item["current"] * 100))
            tgt_pct = int(round(item["target"] * 100))
            
            if item["gap"] > 0.05:
                rec = f"Critical priority: {item['skill']} is at {curr_pct}% vs required {tgt_pct}%. Dedicate next 2 adaptive practice sessions here."
            elif item["gap"] > 0.0:
                rec = f"Moderate gap: {item['skill']} is at {curr_pct}% (Target: {tgt_pct}%). Targeted practice recommended."
            else:
                rec = f"Role benchmark met: {item['skill']} is at {curr_pct}% (Benchmark: {tgt_pct}%). Maintain with periodic spaced reviews."

            gap_items.append(SkillGapItem(
                skill=item["skill"],
                current_mastery=round(item["current"], 3),
                target_threshold=item["target"],
                importance_weight=item["weight"],
                gap_magnitude=round(item["gap"], 4),
                priority_rank=rank,
                estimated_questions_to_mastery=item["questions_needed"],
                recommendation_text=rec
            ))

        top_priority = gap_items[0].skill if gap_items and gap_items[0].gap_magnitude > 0 else None
        # ~2.5 minutes per adaptive question
        est_study_hours = round((total_questions_needed * 2.5) / 60.0, 1)
        is_ready = readiness >= 78.0

        return CareerAnalysisReport(
            role_id=role.role_id,
            role_title=role.title,
            readiness_score=readiness,
            is_job_ready=is_ready,
            top_priority_skill=top_priority,
            gaps=gap_items,
            estimated_study_hours=est_study_hours
        )
