from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# 1. Data Ingestion
class IngestRequest(BaseModel):
    student_id: str
    file_type: str
    content_base64: str

class ExtractedCourse(BaseModel):
    course_id: str
    name: str
    credits: int
    grade: str
    is_passed: bool

class IngestResponse(BaseModel):
    status: str
    extracted_courses: List[ExtractedCourse]

# 2. Student Persona
class CreditsSummary(BaseModel):
    earned: int
    total_required: int
    debt: int

class CategorizedLists(BaseModel):
    passed: List[str]
    failed: List[str]
    can_improve: List[str]

class Persona(BaseModel):
    gpa: float
    standing: str
    credits_summary: CreditsSummary
    categorized_lists: CategorizedLists

class StatusResponse(BaseModel):
    persona: Persona

# 3. Goal & Limits
class LifeConstraintSlot(BaseModel):
    day: str
    start: str
    end: str

class LifeConstraints(BaseModel):
    work_hours_per_week: int
    blackout_slots: List[LifeConstraintSlot]

class SetGoalsRequest(BaseModel):
    student_id: str
    user_intent: str
    life_constraints: LifeConstraints

class Limits(BaseModel):
    min_credits: int
    max_credits: int
    difficulty_cap: float

class SetGoalsResponse(BaseModel):
    extracted_goals: List[str]
    limits: Limits

# 4. Smart Planning
class RecommendRequest(BaseModel):
    student_id: str
    semester: str

class SuggestedCourse(BaseModel):
    course_id: str
    priority: str
    reason: str
    difficulty_score: float

class RecommendResponse(BaseModel):
    suggested_cart: List[SuggestedCourse]
    total_credits: int
    balance_status: str

# 5. Adaptive Roadmap
class RoadmapCourse(BaseModel):
    id: str
    name: str
    type: str
    difficulty: float
    reasoning: str

class RoadmapTerm(BaseModel):
    term: str
    is_summer: bool
    credits: int
    term_difficulty: float
    courses: List[RoadmapCourse]

class OverallPlan(BaseModel):
    graduation_date: str
    semesters_remaining: int

class RoadmapResponse(BaseModel):
    overall_plan: OverallPlan
    optimized_roadmap: List[RoadmapTerm]
    insights: List[str]

# 6. Incident Handling
class ReOptimizeRequest(BaseModel):
    student_id: str
    incident_type: str
    course_id: str
    keep_original_grad_date: bool

class ReoptimizationReport(BaseModel):
    status: str
    incident_resolved: str
    action_taken: str
    impact_severity: str

class ReoptimizedSemesterCourse(BaseModel):
    id: str
    name: str
    type: str
    priority: str
    reasoning: str

class ReoptimizedSemester(BaseModel):
    term: str
    is_summer: bool
    total_credits: int
    courses: List[ReoptimizedSemesterCourse]

class NewOptimizedRoadmap(BaseModel):
    overall_stats: Dict[str, Any]
    semesters: List[ReoptimizedSemester]
    bottlenecks_resolved: List[str]
    warnings: List[str]

class ReOptimizeResponse(BaseModel):
    reoptimization_report: ReoptimizationReport
    new_optimized_roadmap: NewOptimizedRoadmap
