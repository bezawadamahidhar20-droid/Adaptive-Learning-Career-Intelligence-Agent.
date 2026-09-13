"""
Career Intelligence Layer - Role Matching & Readiness Computation
Maps student skill masteries against target career profiles and computes weighted readiness scores.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class RoleProfile:
    role_id: str
    title: str
    description: str
    skill_weights: Dict[str, float]  # Skill name -> importance weight (sums to 1.0)
    target_thresholds: Dict[str, float] = field(default_factory=dict) # Skill name -> min required mastery

ROLE_REGISTRY: Dict[str, RoleProfile] = {
    "data_scientist": RoleProfile(
        role_id="data_scientist",
        title="Data Scientist",
        description="Designs predictive machine learning models, statistical experiments, and data pipelines.",
        skill_weights={
            "Python": 0.25,
            "Machine Learning": 0.27,
            "Statistics": 0.20,
            "SQL": 0.18,
            "Deep Learning": 0.10
        },
        target_thresholds={
            "Python": 0.75,
            "Machine Learning": 0.80,
            "Statistics": 0.75,
            "SQL": 0.70,
            "Deep Learning": 0.65
        }
    ),
    "backend_developer": RoleProfile(
        role_id="backend_developer",
        title="Backend Developer",
        description="Architects scalable RESTful APIs, distributed microservices, database schemas, and background queues.",
        skill_weights={
            "Python": 0.25,
            "Backend Architecture": 0.25,
            "SQL": 0.20,
            "System Design": 0.20,
            "Data Structures & Algorithms": 0.10
        },
        target_thresholds={
            "Python": 0.80,
            "Backend Architecture": 0.85,
            "SQL": 0.75,
            "System Design": 0.75,
            "Data Structures & Algorithms": 0.70
        }
    ),
    "data_analyst": RoleProfile(
        role_id="data_analyst",
        title="Data Analyst",
        description="Transforms raw business data into actionable dashboards, SQL analytics, and statistical insights.",
        skill_weights={
            "SQL": 0.35,
            "Python": 0.25,
            "Statistics": 0.25,
            "Machine Learning": 0.15
        },
        target_thresholds={
            "SQL": 0.85,
            "Python": 0.70,
            "Statistics": 0.75,
            "Machine Learning": 0.60
        }
    )
}

class RoleMatcher:
    def __init__(self, roles: Optional[Dict[str, RoleProfile]] = None):
        self.roles = roles or ROLE_REGISTRY

    def get_role(self, role_id: str) -> Optional[RoleProfile]:
        return self.roles.get(role_id)

    def list_roles(self) -> List[RoleProfile]:
        return list(self.roles.values())

    def calculate_readiness(
        self,
        role_id: str,
        skill_masteries: Dict[str, float]
    ) -> float:
        """
        Calculates career readiness percentage for a given role:
        Readiness = Sum(Mastery_i * Weight_i) / Sum(Weight_i)
        Mastery is assumed in range [0, 1]. Returns percentage 0.0 - 100.0 (or fraction 0.0 - 1.0).
        """
        role = self.get_role(role_id)
        if not role:
            raise ValueError(f"Unknown role_id: {role_id}")

        total_weight = 0.0
        weighted_sum = 0.0

        for skill, weight in role.skill_weights.items():
            mastery = skill_masteries.get(skill, 0.0)
            mastery = max(0.0, min(1.0, mastery))
            weighted_sum += mastery * weight
            total_weight += weight

        if total_weight == 0.0:
            return 0.0

        readiness_ratio = weighted_sum / total_weight
        return round(readiness_ratio * 100.0, 2)
