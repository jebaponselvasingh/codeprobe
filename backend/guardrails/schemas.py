"""
Pydantic output schemas for all LLM responses across CodeProbe agents.
Every schema is intentionally permissive (all fields optional with safe defaults)
so that partial/malformed LLM output degrades gracefully rather than crashing.
"""
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


def clamp_score(value: float) -> float:
    """Clamp a score to the valid 0.0–10.0 range."""
    try:
        return max(0.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Shared finding types (reused across multiple agents)
# ---------------------------------------------------------------------------

class GenericFinding(BaseModel):
    type: str = "suggestion"
    area: str = ""
    detail: str = ""
    file: str = ""
    line: int = 0
    fix_hint: str = ""


# ---------------------------------------------------------------------------
# Agent 03 – React Evaluator
# ---------------------------------------------------------------------------

class ReactLLMOutput(BaseModel):
    findings: List[GenericFinding] = []
    sub_scores: Dict[str, float] = Field(default_factory=dict)
    strengths: List[str] = []
    score: float = Field(default=5.0, ge=0.0, le=10.0)


# ---------------------------------------------------------------------------
# Agent 04 – FastAPI Evaluator
# ---------------------------------------------------------------------------

class FastAPILLMOutput(BaseModel):
    findings: List[GenericFinding] = []
    sub_scores: Dict[str, float] = Field(default_factory=dict)
    strengths: List[str] = []
    score: float = Field(default=5.0, ge=0.0, le=10.0)


# ---------------------------------------------------------------------------
# Agent 05 – Security Scanner
# ---------------------------------------------------------------------------

class SecurityFinding(BaseModel):
    type: str = "negative"
    area: str = "security"
    detail: str = ""
    file: str = ""
    line: int = 0
    fix_hint: str = ""
    severity: Literal["critical", "high", "medium", "low"] = "low"
    owasp: str = ""


class SecurityLLMOutput(BaseModel):
    findings: List[SecurityFinding] = []
    additional_owasp_coverage: Dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent 06 – Performance Profiler
# ---------------------------------------------------------------------------

class PerformanceLLMOutput(BaseModel):
    findings: List[GenericFinding] = []
    frontend_score: float = Field(default=5.0, ge=0.0, le=10.0)
    backend_score: float = Field(default=5.0, ge=0.0, le=10.0)


# ---------------------------------------------------------------------------
# Agent 07 – Code Smell Detector
# ---------------------------------------------------------------------------

class RefactoringSuggestion(BaseModel):
    title: str = ""
    before: str = ""
    after: str = ""


class CodeSmellLLMOutput(BaseModel):
    findings: List[GenericFinding] = []
    refactoring_suggestions: List[RefactoringSuggestion] = []


# ---------------------------------------------------------------------------
# Agent 08 – Test Coverage Analyzer
# ---------------------------------------------------------------------------

class MissingTest(BaseModel):
    file: str = ""
    test_type: str = "unit"
    scenario: str = ""


class TestCoverageLLMOutput(BaseModel):
    quality_assessment: str = ""
    missing_tests: List[MissingTest] = []
    test_quality_score: float = Field(default=5.0, ge=0.0, le=10.0)


# ---------------------------------------------------------------------------
# Agent 09 – Dependency Auditor
# ---------------------------------------------------------------------------

class DependencyConcern(BaseModel):
    package: str = ""
    concern_type: str = ""
    severity: Literal["high", "medium", "low"] = "low"
    suggestion: str = ""


class DependencyLLMOutput(BaseModel):
    concerns: List[DependencyConcern] = []
    overall_health: Literal["good", "fair", "poor"] = "fair"
    dependency_score: float = Field(default=5.0, ge=0.0, le=10.0)


# ---------------------------------------------------------------------------
# Agent 10 – Accessibility Checker
# ---------------------------------------------------------------------------

class AccessibilityViolation(BaseModel):
    rule: str = ""
    impact: Literal["critical", "serious", "moderate", "minor"] = "moderate"
    element: str = ""
    file: str = ""
    fix: str = ""


class AccessibilityWCAG(BaseModel):
    A: Literal["pass", "partial", "fail"] = "partial"
    AA: Literal["pass", "partial", "fail"] = "partial"


class AccessibilityLLMOutput(BaseModel):
    violations: List[AccessibilityViolation] = []
    wcag_summary: AccessibilityWCAG = Field(default_factory=AccessibilityWCAG)
    accessibility_score: float = Field(default=5.0, ge=0.0, le=10.0)


# ---------------------------------------------------------------------------
# Agent 11 – Documentation Reviewer
# ---------------------------------------------------------------------------

class DocumentationLLMOutput(BaseModel):
    can_onboard: bool = False
    missing_sections: List[str] = []
    improvement_suggestions: List[str] = []
    documentation_score: float = Field(default=5.0, ge=0.0, le=10.0)


# ---------------------------------------------------------------------------
# Agent 12 – Integration Analyzer
# ---------------------------------------------------------------------------

class IntegrationLLMOutput(BaseModel):
    findings: List[GenericFinding] = []
    strengths: List[str] = []
    contract_issues: List[str] = []
    score: float = Field(default=5.0, ge=0.0, le=10.0)


# ---------------------------------------------------------------------------
# Agent 13 – Requirements Validator (one schema per LLM pass)
# ---------------------------------------------------------------------------

class ExplicitRequirement(BaseModel):
    id: str = ""
    category: str = "functional"
    description: str = ""
    priority: Literal["must", "should", "nice-to-have"] = "must"
    acceptance_criteria: List[str] = []


class ImplicitRequirement(BaseModel):
    id: str = ""
    description: str = ""
    category: str = "ux"


class RequirementsParseOutput(BaseModel):
    explicit_requirements: List[ExplicitRequirement] = []
    implicit_requirements: List[ImplicitRequirement] = []


class RequirementValidation(BaseModel):
    id: str = ""
    status: Literal["implemented", "partial", "missing"] = "missing"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_notes: str = ""
    gaps: List[str] = []


class ValidationOutput(BaseModel):
    validations: List[RequirementValidation] = []


class FlowStep(BaseModel):
    step: int = 0
    description: str = ""
    frontend_component: str = ""
    backend_endpoint: str = ""
    implemented: bool = True


class UserFlow(BaseModel):
    name: str = ""
    steps: List[FlowStep] = []
    complete: bool = True
    missing_steps: List[str] = []


class FlowTracingOutput(BaseModel):
    flows: List[UserFlow] = []


class TestScenario(BaseModel):
    id: str = ""
    requirement_id: str = ""
    title: str = ""
    type: Literal["unit", "integration", "e2e"] = "unit"
    steps: List[str] = []
    expected_result: str = ""
    priority: Literal["critical", "high", "medium", "low"] = "medium"


class TestScenariosOutput(BaseModel):
    test_scenarios: List[TestScenario] = []


# ---------------------------------------------------------------------------
# Agent 14 – Plagiarism Detector
# ---------------------------------------------------------------------------

class PlagiarismLLMOutput(BaseModel):
    originality_estimate: int = Field(default=50, ge=0, le=100)
    assessment: str = ""
    tutorial_signals: List[str] = []
    original_elements: List[str] = []


# ---------------------------------------------------------------------------
# Agent 15 – Complexity Analyzer
# ---------------------------------------------------------------------------

class ComplexitySuggestion(BaseModel):
    function_name: str = ""
    file: str = ""
    current_complexity: int = 0
    approach: str = ""
    pseudocode: str = ""


class ComplexityLLMOutput(BaseModel):
    suggestions: List[ComplexitySuggestion] = []


# ---------------------------------------------------------------------------
# Agent 16 – Report Generator (one schema per LLM call)
# ---------------------------------------------------------------------------

class CriticItem(BaseModel):
    i: int = 0
    false_positive: bool = False


class PriorityAction(BaseModel):
    rank: int = 1
    severity: Literal["critical", "high", "medium", "low"] = "high"
    title: str = ""
    detail: str = ""
    file: str = ""
    estimated_hours: float = Field(default=1.0, ge=0.0)
    category: str = ""


class PriorityActionsOutput(BaseModel):
    actions: List[PriorityAction] = []


class LearningItem(BaseModel):
    day: str = ""
    topic: str = ""
    why: str = ""
    exercise: str = ""
    estimated_hours: int = Field(default=2, ge=1, le=8)


class LearningWeek(BaseModel):
    week: int = 1
    focus: str = ""
    items: List[LearningItem] = []


class LearningPathOutput(BaseModel):
    weeks: List[LearningWeek] = []
    skill_gaps: Dict[str, float] = Field(default_factory=dict)
