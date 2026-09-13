"""
Profile Analyzer Agent
Evaluates student educational background, graduation timeline, experience tier, and target career track.
"""
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ProfileAnalysisResult:
    user_id: str
    target_role: str
    academic_status: str
    urgency_tier: str  # 'high', 'moderate', 'planning'
    velocity_recommendation: str
    summary: str

class ProfileAnalyzerAgent:
    def analyze_profile(self, user_id: str, profile_data: Dict[str, Any]) -> ProfileAnalysisResult:
        """
        Analyzes profile features to establish a tailored learning pacing strategy.
        """
        grad_year = profile_data.get("graduation_year", 2026)
        exp_level = profile_data.get("experience_level", "Beginner / Student")
        target_role = profile_data.get("target_role", "data_scientist")
        education = profile_data.get("education_level", "Undergraduate")

        # Determine urgency based on graduation timeline
        current_year = 2026
        years_to_grad = max(0, grad_year - current_year)
        
        if years_to_grad <= 0:
            urgency = "high"
            velocity = "Intensive placement sprint (5-7 adaptive sessions/week + daily interview prep)"
        elif years_to_grad == 1:
            urgency = "moderate"
            velocity = "Steady career readiness track (3-4 adaptive sessions/week + monthly project milestone)"
        else:
            urgency = "planning"
            velocity = "Foundational pacing (2-3 sessions/week focusing on core fundamentals & DSA)"

        summary = (
            f"Candidate targeting {target_role.replace('_', ' ').title()} with {exp_level} background. "
            f"Education: {education} (Grad: {grad_year}). Pacing set to {urgency} urgency."
        )

        return ProfileAnalysisResult(
            user_id=user_id,
            target_role=target_role,
            academic_status=f"{education} (Graduating {grad_year})",
            urgency_tier=urgency,
            velocity_recommendation=velocity,
            summary=summary
        )
