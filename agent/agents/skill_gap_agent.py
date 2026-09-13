"""
Skill Gap Agent
Computes precise numeric gap magnitudes between current BKT mastery and role benchmarks,
calculates learning time estimates, and prioritizes action items.
"""
from typing import Dict, List, Any
from dataclasses import dataclass
from ..career.skill_gap import SkillGapAnalyzer, SkillGapItem, CareerAnalysisReport
from ..career.role_matcher import RoleMatcher

class SkillGapAgent:
    def __init__(self, role_matcher: RoleMatcher = None):
        self.analyzer = SkillGapAnalyzer(role_matcher=role_matcher)

    def analyze(self, role_id: str, skill_masteries: Dict[str, float]) -> CareerAnalysisReport:
        """Runs comprehensive skill gap analysis."""
        return self.analyzer.analyze_gaps(role_id=role_id, skill_masteries=skill_masteries)
