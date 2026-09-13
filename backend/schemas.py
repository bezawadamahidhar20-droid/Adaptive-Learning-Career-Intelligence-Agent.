"""
Pydantic Data Schemas for FastAPI Endpoints
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class UserCreate(BaseModel):
    name: str = "Alex Student"
    email: str = "alex@university.edu"
    target_role: str = "data_scientist"

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    target_role: str

class RoleInfo(BaseModel):
    role_id: str
    title: str
    description: str
    skill_weights: Dict[str, float]
    target_thresholds: Dict[str, float]

class QuestionOption(BaseModel):
    index: int
    text: str

class AssessmentQuestionResponse(BaseModel):
    id: str
    skill: str
    concept: str
    subtopic: str
    difficulty: int
    question: str
    options: List[str]

class AssessmentStartRequest(BaseModel):
    user_id: str
    total_questions: int = 10
    target_role: Optional[str] = None

class AnswerSubmissionItem(BaseModel):
    question_id: str
    selected_option: int

class AssessmentSubmitRequest(BaseModel):
    user_id: str
    target_role: str
    submissions: List[AnswerSubmissionItem]

class AnswerResult(BaseModel):
    question_id: str
    is_correct: bool
    correct_option: int
    explanation: str
    concept: str
    previous_mastery: float
    updated_mastery: float
    updated_theta: float

class AssessmentSubmitResponse(BaseModel):
    assessment_id: str
    total_questions: int
    correct_count: int
    score_percentage: float
    results: List[AnswerResult]
    updated_theta: float

class SkillGapItemResponse(BaseModel):
    skill: str
    current_mastery: float
    target_threshold: float
    importance_weight: float
    gap_magnitude: float
    priority_rank: int
    estimated_questions_to_mastery: int
    recommendation_text: str

class CareerAnalysisResponse(BaseModel):
    role_id: str
    role_title: str
    readiness_score: float
    is_job_ready: bool
    top_priority_skill: Optional[str]
    gaps: List[SkillGapItemResponse]
    estimated_study_hours: float

class DashboardSummaryResponse(BaseModel):
    user_id: str
    name: str
    target_role: str
    role_title: str
    theta: float
    total_attempts: int
    correct_attempts: int
    accuracy_percentage: float
    career_readiness: float
    is_job_ready: bool
    top_priority_skill: Optional[str]
    skill_masteries: Dict[str, float]
    concept_masteries: Dict[str, float]
    gaps: List[SkillGapItemResponse]
    next_recommended_assignment: List[AssessmentQuestionResponse]
