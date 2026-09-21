from typing import Literal, Any
from pydantic import BaseModel, Field


# ============================================================
# PROJECT & APPLICATION MODELS
# ============================================================

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(default="")

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: str

class ApplicationCreate(BaseModel):
    project_id: str
    name: str = Field(..., min_length=2, max_length=100)
    base_url: str = Field(default="https://example.com")
    environment: str = Field(default="QA")

class ApplicationResponse(BaseModel):
    id: str
    project_id: str
    name: str
    base_url: str
    environment: str
    created_at: str


# ============================================================
# REQUIREMENT REQUEST & MODELS
# ============================================================

class RequirementCreate(BaseModel):
    project_id: str
    application_id: str | None = None
    title: str
    content: str

class RequirementRequest(BaseModel):
    requirement: str = Field(
        ...,
        min_length=10,
        max_length=5000
    )
    base_url: str = Field(
        default="https://example.com"
    )
    project_id: str = Field(
        default="proj-default-001"
    )
    screenshot_context: str = Field(
        default=""
    )


# ============================================================
# TEST CASE MODELS
# ============================================================

class TestCase(BaseModel):
    id: str
    tc_code: str | None = None
    priority: str = "Medium"
    type: str = "functional"
    test_scenario: str | None = None
    title: str
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected_result: str = ""
    test_data: list[str] = Field(default_factory=list)
    requirement_id: str | None = "REQ-001"
    status: str = "Ready for Automation"
    remarks: str = ""
    automation_candidate: bool = True
    project_id: str | None = "proj-default-001"

class TestCaseResponse(BaseModel):
    test_cases: list[TestCase]

class TestCaseSaveRequest(BaseModel):
    test_case: TestCase
    project_id: str = "proj-default-001"


# ============================================================
# AUTOMATION REQUEST
# ============================================================

class AutomationRequest(BaseModel):
    test_case: TestCase
    framework: Literal[
        "playwright",
        "selenium",
        "appium",
        "cypress"
    ] = "playwright"

    language: Literal[
        "python",
        "java",
        "javascript"
    ] = "python"

    base_url: str = "https://example.com"
    project_id: str = "proj-default-001"


# ============================================================
# EXECUTION REQUEST & RESPONSE
# ============================================================

class ExecutionRequest(BaseModel):
    code: str
    filename: str = "test_generated.py"
    framework: Literal[
        "playwright",
        "selenium",
        "appium",
        "cypress"
    ] = "playwright"

    language: Literal[
        "python",
        "java",
        "javascript"
    ] = "python"

    base_url: str = "https://example.com"
    test_case_id: str = ""
    script_id: str = ""
    project_id: str = "proj-default-001"
    steps: int = 0
    assertions: int = 0
    browser: str = ""


# ============================================================
# DASHBOARD STATS MODEL
# ============================================================

class DashboardStatsResponse(BaseModel):
    test_cases: int
    automations: int
    executions: int
    passed: int
    failed: int
    pass_rate: str
    application: str
    base_url: str
    environment: str
    recent_executions: list[dict[str, Any]] = Field(default_factory=list)
