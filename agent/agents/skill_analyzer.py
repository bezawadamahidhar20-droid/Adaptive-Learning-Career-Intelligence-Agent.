"""
Skill Analyzer Agent
Translates between descriptive skill levels ('Below Average', 'Average', 'Good', 'Perfect')
and quantitative BKT parameters, categorizes skills, computes priorities, and generates actionable advice.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

DESCRIPTIVE_LEVELS = ["Below Average", "Average", "Good", "Perfect"]

LEVEL_TO_NUMERIC = {
    "Below Average": 0.25,
    "Average": 0.50,
    "Good": 0.75,
    "Perfect": 0.95
}

def numeric_to_descriptive(mastery: float) -> str:
    """Converts a continuous mastery probability in [0, 1] to a standardized descriptive tier."""
    if mastery < 0.40:
        return "Below Average"
    elif mastery < 0.68:
        return "Average"
    elif mastery < 0.88:
        return "Good"
    else:
        return "Perfect"

@dataclass
class StandardizedSkill:
    skill_name: str
    category: str
    descriptive_level: str
    numeric_mastery: float
    importance_weight: float
    target_level: str
    confidence: float
    evidence_source: str
    improvement_recommendation: str
    priority_rank: int

class SkillAnalyzerAgent:
    def __init__(self):
        self.default_categories = {
            "Python": "Technical / Programming",
            "SQL": "Database & Analytics",
            "Machine Learning": "AI / ML Engineering",
            "Statistics": "Mathematics & Analytics",
            "Deep Learning": "AI / ML Engineering",
            "Backend Architecture": "Software Engineering",
            "System Design": "Software Engineering",
            "Data Structures & Algorithms": "Core CS Fundamentals",
            "Communication": "Soft Skills",
            "Problem Solving": "Soft Skills"
        }

    def standardize_and_rank_skills(
        self,
        raw_skills: List[Dict[str, Any]],
        role_weights: Optional[Dict[str, float]] = None
    ) -> List[StandardizedSkill]:
        """
        Standardizes raw user skills, maps descriptive levels, computes priorities,
        and generates explainable improvement recommendations.
        """
        weights = role_weights or {}
        processed: List[StandardizedSkill] = []

        for item in raw_skills:
            name = item.get("skill_name", item.get("name", "Unknown"))
            category = item.get("category") or self.default_categories.get(name, "General Technical")
            
            # Level parsing
            level_input = item.get("descriptive_level", item.get("level", "Average"))
            if level_input not in DESCRIPTIVE_LEVELS:
                if isinstance(level_input, (int, float)):
                    descriptive_level = numeric_to_descriptive(float(level_input))
                else:
                    descriptive_level = "Average"
            else:
                descriptive_level = level_input

            numeric_mastery = item.get("numeric_mastery")
            if numeric_mastery is None:
                numeric_mastery = LEVEL_TO_NUMERIC.get(descriptive_level, 0.50)

            importance = weights.get(name, item.get("importance_weight", 0.20))
            target_level = item.get("target_level", "Good" if importance >= 0.20 else "Average")
            confidence = item.get("confidence", 0.75)
            evidence = item.get("evidence_source", "Onboarding Self-Assessment")

            # Generate improvement recommendation
            if descriptive_level == "Below Average":
                rec = f"Critical foundation gap: Begin with 15 focused adaptive practice questions on {name} fundamentals."
            elif descriptive_level == "Average":
                rec = f"Moderate proficiency: Advance to medium-difficulty problem solving and practical implementation tasks."
            elif descriptive_level == "Good":
                rec = f"Strong benchmark capability: Maintain knowledge with periodic spaced repetition reviews."
            else:
                rec = f"Mastery achieved: Ready for senior-level technical interview challenges in {name}."

            processed.append(StandardizedSkill(
                skill_name=name,
                category=category,
                descriptive_level=descriptive_level,
                numeric_mastery=round(numeric_mastery, 3),
                importance_weight=round(importance, 3),
                target_level=target_level,
                confidence=round(confidence, 2),
                evidence_source=evidence,
                improvement_recommendation=rec,
                priority_rank=1
            ))

        # Sort by urgency = importance * (1.0 - numeric_mastery)
        processed.sort(key=lambda s: s.importance_weight * (1.0 - s.numeric_mastery), reverse=True)
        
        # Assign 1-indexed priority ranks
        for idx, skill in enumerate(processed, 1):
            skill.priority_rank = idx

        return processed
