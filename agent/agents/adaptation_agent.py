"""
Adaptation Agent
Coordinates online feedback loops:
Assesses student performance changes → Recalculates skill mastery & theta →
Updates gap priorities → Dynamically adapts learning roadmap & placement tasks.
"""
from typing import Dict, List, Any
from dataclasses import dataclass
from .roadmap_agent import RoadmapAgent, RoadmapTask
from .skill_gap_agent import SkillGapAgent
from ..career.skill_gap import CareerAnalysisReport

@dataclass
class AdaptationReport:
    previous_readiness: float
    updated_readiness: float
    readiness_delta: float
    recalculated_gaps: CareerAnalysisReport
    adapted_roadmap: List[RoadmapTask]
    adaptation_summary: str

class AdaptationAgent:
    def __init__(
        self,
        skill_gap_agent: SkillGapAgent = None,
        roadmap_agent: RoadmapAgent = None
    ):
        self.gap_agent = skill_gap_agent or SkillGapAgent()
        self.roadmap_agent = roadmap_agent or RoadmapAgent()

    def process_adaptation(
        self,
        user_id: str,
        target_role: str,
        previous_readiness: float,
        current_skill_masteries: Dict[str, float],
        completed_task_ids: Optional[List[str]] = None
    ) -> AdaptationReport:
        """
        Recalculates gaps, updates readiness, and adapts the roadmap.
        """
        # 1. Recalculate skill gaps
        gap_report = self.gap_agent.analyze(target_role, current_skill_masteries)
        updated_readiness = gap_report.readiness_score
        readiness_delta = round(updated_readiness - previous_readiness, 2)

        # 2. Adapt the roadmap based on new skill masteries
        adapted_tasks = self.roadmap_agent.generate_adaptive_roadmap(
            target_role=target_role,
            user_skills=current_skill_masteries,
            completed_task_ids=completed_task_ids
        )

        # 3. Generate Adaptation Summary
        if readiness_delta > 0:
            summary = f"Positive adaptation: Career readiness advanced by +{readiness_delta}%! Gaps decreased."
        elif readiness_delta < 0:
            summary = f"Readiness adjusted by {readiness_delta}%. Scaffolding reinforcement added to roadmap."
        else:
            summary = "Knowledge model verified. Roadmap optimized for remaining priority gaps."

        return AdaptationReport(
            previous_readiness=previous_readiness,
            updated_readiness=updated_readiness,
            readiness_delta=readiness_delta,
            recalculated_gaps=gap_report,
            adapted_roadmap=adapted_tasks,
            adaptation_summary=summary
        )
