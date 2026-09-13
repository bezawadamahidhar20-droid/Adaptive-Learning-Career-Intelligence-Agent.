"""
Production Pydantic Schemas for API Requests & Responses
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, List, Optional, Any

# ==================== AUTH & USER SCHEMAS ====================
class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    target_role: Optional[str] = "data_scientist"

class UserLoginRequest(BaseModel):
    email: str
    password: str

class OAuthLoginRequest(BaseModel):
    provider: str = "google" # 'google' or 'github'
    code: str
    redirect_uri: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    target_role: str
    onboarding_completed: bool

# ==================== ONBOARDING SCHEMAS ====================
class RawSkillInput(BaseModel):
    name: str
    category: Optional[str] = None
    level: str = "Average" # 'Below Average', 'Average', 'Good', 'Perfect'

class OnboardingSubmitRequest(BaseModel):
    education_level: str = "Undergraduate (B.Tech / B.S.)"
    major: str = "Computer Science"
    graduation_year: int = 2026
    experience_level: str = "Beginner / Student"
    placement_goal: str = "Tech / AI Campus Placements 2026"
    target_role: str = "data_scientist"
    technical_skills: List[RawSkillInput]
    soft_skills: List[str] = ["Problem Solving", "Communication"]
    preferred_technologies: List[str] = ["Python", "SQL", "FastAPI"]

class OnboardingStatusResponse(BaseModel):
    onboarding_completed: bool
    user_id: str
    profile: Optional[Dict[str, Any]] = None

# ==================== SKILL SCHEMAS ====================
class SkillItemResponse(BaseModel):
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

# ==================== CAREER SCHEMAS ====================
class RoleInfo(BaseModel):
    role_id: str
    title: str
    description: str
    skill_weights: Dict[str, float]
    target_thresholds: Dict[str, float]

class ExplainableCareerFitResponse(BaseModel):
    role_id: str
    role_title: str
    suitability_score: float
    is_recommended: bool
    is_job_ready: bool
    explanation: str
    strengths: List[str]
    missing_skills: List[str]
    priority_skills_to_learn: List[str]


# ==================== ROADMAP SCHEMAS ====================
class RoadmapTaskResponse(BaseModel):
    id: str
    target_role: str
    stage_name: str
    title: str
    description: str
    category: str
    associated_skill: str
    priority_rank: int
    is_completed: bool

class TaskToggleRequest(BaseModel):
    task_id: str
    is_completed: bool

class RoadmapSummaryResponse(BaseModel):
    target_role: str
    total_tasks: int
    completed_tasks: int
    completion_percentage: float
    stages: Dict[str, List[RoadmapTaskResponse]]

# ==================== PLACEMENT SCHEMAS ====================
class PlacementModuleResponse(BaseModel):
    module_type: str
    title: str
    description: str
    items: List[Dict[str, Any]]

class PlacementProgressToggleRequest(BaseModel):
    module_type: str
    item_id: str
    status: str # 'pending', 'completed'

# ==================== ASSESSMENT SCHEMAS ====================
class AssessmentQuestionResponse(BaseModel):
    id: str
    skill: str
    concept: str
    subtopic: str
    difficulty: int
    question: str
    options: List[str]

class AnswerSubmissionItem(BaseModel):
    question_id: str
    selected_option: int

class AssessmentSubmitRequest(BaseModel):
    target_role: str
    submissions: List[AnswerSubmissionItem]

class AnswerResult(BaseModel):
    question_id: str
    is_correct: bool
    correct_option: int
    explanation: str
    concept: str
    skill: str
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

# ==================== DASHBOARD SCHEMAS ====================
class DashboardSummaryResponse(BaseModel):
    user_id: str
    name: str
    target_role: str
    role_title: str
    onboarding_completed: bool
    theta: float
    total_attempts: int
    correct_attempts: int
    accuracy_percentage: float
    career_readiness: float
    is_job_ready: bool
    top_priority_skill: Optional[str]
    skills: List[SkillItemResponse]
    career_fit: ExplainableCareerFitResponse
    roadmap_preview: List[RoadmapTaskResponse]
    next_recommended_assignment: List[AssessmentQuestionResponse]
    has_sufficient_data: bool
