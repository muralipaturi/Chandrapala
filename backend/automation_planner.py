"""
Stage 2.3
Gemini-powered framework-independent automation planner.

IMPORTANT:
This module generates an AutomationPlan only.
It does NOT generate Selenium, Playwright, Appium, or Cypress code.
"""

from __future__ import annotations

import json
import os
import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from automation_models import (
    ActionType,
    AutomationSpec,
    Locator,
    LocatorStrategy,
)


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


# ============================================================
# PLANNER MODELS
# ============================================================

class PlannerLocator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: LocatorStrategy
    value: str = Field(min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: Optional[str] = None


class PlannedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_number: int = Field(ge=1)

    action: ActionType

    business_target: Optional[str] = None

    locator_candidates: List[PlannerLocator] = Field(
        default_factory=list
    )

    value_reference: Optional[str] = None

    variable_name: Optional[str] = None

    wait_for: Optional[str] = None

    expected_result: Optional[str] = None

    source_step: Optional[int] = None


class PlannedAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_type: ActionType

    business_target: Optional[str] = None

    locator_candidates: List[PlannerLocator] = Field(
        default_factory=list
    )

    expected_value: Optional[str] = None

    description: str

    source_expected_result: Optional[str] = None


class AutomationPlan(BaseModel):
    """
    Framework-independent automation plan.

    This is the contract consumed by framework-specific
    code generators.
    """

    model_config = ConfigDict(extra="forbid")

    test_case_id: str

    title: str

    application_url: str

    actions: List[PlannedAction] = Field(
        default_factory=list
    )

    assertions: List[PlannedAssertion] = Field(
        default_factory=list
    )

    assumptions: List[str] = Field(
        default_factory=list
    )


# ============================================================
# PROMPT
# ============================================================

PLANNER_SYSTEM_PROMPT = r"""
You are an expert QA automation architect.

Your task is to convert a framework-independent AutomationSpec
into a framework-independent AutomationPlan.

IMPORTANT:

You are NOT generating code.

Do not generate:
- Python code
- Java code
- JavaScript code
- Selenium code
- Playwright code
- Appium code
- Cypress code

You are generating structured automation intent only.

============================================================
CORE RULE & 1 STEP -> 1 ACTION SEMANTIC MANDATE
============================================================

CRITICAL SEMANTIC MANDATE:

Each step in the requirement/test case MUST map 1-to-1 to exactly ONE correctly interpreted automation action, unless the step text explicitly specifies multiple actions (e.g. "Enter username and click submit").

- DO NOT skip or omit requirement steps.
- DO NOT combine multiple separate requirement steps into one action.
- DO NOT invent extra actions that are not described in the step.
- DO NOT set action type to CLICK when the step verb is FILL, TYPE, ENTER, SELECT, CHOOSE, CHECK, or UNCHECK.

STEP VERB INTERPRETATION MATRIX:
- "fill" / "enter" / "type" / "input" -> action: "FILL"
- "select" / "choose" / "pick" -> action: "SELECT"
- "click" / "tap" / "press" -> action: "CLICK"
- "navigate" / "open" / "go to" -> action: "NAVIGATE" (or CLICK if UI menu)
- "check" -> action: "CHECK"
- "uncheck" -> action: "UNCHECK"
- "hover" -> action: "HOVER"
- "upload" / "attach" -> action: "UPLOAD"
- "verify" / "assert" / "check that" -> PlannedAssertion with ASSERT_VISIBLE / ASSERT_TEXT / ASSERT_URL

Every expected business outcome must have at least one assertion.

Do not invent business behavior.

Do not add unrelated test scenarios.

Do not add generic QA scenarios merely because they are common.

============================================================
PRECONDITION & USER CONTEXT RULE
============================================================

CRITICAL MANDATE FOR PRECONDITIONS:

1. Technical/Environment Preconditions (e.g. "Deployed With Recent Code Build", "Server running on port 8000", "Browser supports Chrome"):
   - MUST NOT generate UI actions or click targets.
   - Do NOT create UI targets like "Deployed With Recent Code Build" or click buttons for environment setup.

2. User/Role Session Preconditions (e.g. "as Registration Staff", "Logged in as Admin"):
   - Represent as proper authentication / session login steps (e.g. login with role credentials or navigate to login page).
   - NEVER create a clickable UI target for "as Registration Staff" or "as Admin".

============================================================
TEST DATA RULE
============================================================

NEVER invent concrete test data.

Do not invent:
- usernames
- passwords
- employee names
- employee IDs
- dates
- leave types
- file names
- file contents
- product names
- prices
- quantities
- percentages
- account numbers
- error messages

If Stage 1 provides only semantic data, preserve it as a
semantic reference.

Example:

"valid username"

must remain:

"valid username"

NOT:

"admin@example.com"

============================================================
TARGET VS TEST DATA VALUE SEPARATION RULE
============================================================

CRITICAL: Never put test data, input values, or descriptive sentences into business_target.

- business_target MUST BE the actual UI element / field / button name only (e.g. "Patient Name", "Date of Birth", "Gender", "Save", "Search", "username", "password").
- value_reference MUST BE the test data value to enter or select (e.g. "Admin", "Admin@123", "Confirmed", "valid required patient information").
- Descriptive workflow text like "workflow with valid required patient information" or "and query readiness" MUST NOT become a UI element name! Extract underlying UI controls (e.g., Patient Name, DOB, Gender, Save) and keep data references in value_reference.

EXAMPLES:
1. Step: "Enter username with Admin"
   action: "FILL", business_target: "username", value_reference: "Admin"

2. Step: "Enter password with Admin@123"
   action: "FILL", business_target: "password", value_reference: "Admin@123"

3. Step: "Update appointment status to Confirmed"
   action: "SELECT", business_target: "appointment status", value_reference: "Confirmed"

4. Step: "Click Login button"
   action: "CLICK", business_target: "Login", value_reference: null

============================================================
EVIDENCE-BASED ASSERTION RULE
============================================================

Assertions MUST verify actual business outcomes through UI/API evidence:
- DO NOT assert text visibility of the raw expected result description (e.g. DO NOT assert that text "unique patient identity creation and query readiness" is visible on screen).
- DO assert actual evidence: created Patient ID field/label, success notification/banner, patient record row in table, or URL transition.

============================================================
LOCATOR RULE
============================================================

Provide locator candidates only when they are supported by the
available application/UI context.

Preferred strategy order:

1. test_id
2. accessibility_id / aria_label
3. label
4. placeholder
5. name
6. id
7. role
8. text
9. css
10. xpath

Do NOT invent CSS selectors or XPath expressions.

If the actual locator is not known, provide the business target
and leave locator_candidates empty.

Do not claim that an element exists merely because it is common
in similar applications.

============================================================
UI ASSUMPTION RULE
============================================================

Do not assume:

- an error is below a field
- a menu item is hidden
- a button is disabled
- a toast is displayed
- a modal is displayed
- an exact error message
- a particular navigation structure

unless supported by the AutomationSpec or application context.

============================================================
WAIT RULE
============================================================

Waits must describe a business/UI condition.

Good:

"wait until employee list is visible"

"wait until save operation completes"

Bad:

"sleep for 5 seconds"

Do not use arbitrary fixed delays.

============================================================
OUTPUT RULE
============================================================

Return ONLY valid JSON matching the AutomationPlan schema.

No markdown.

No explanations.
"""


# ============================================================
# CLIENT
# ============================================================

def get_gemini_client():
    """
    Reuse the Google GenAI SDK already used by Stage 1.
    """

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is not installed."
        ) from exc

    return genai.Client(api_key=api_key)


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text: str) -> dict:
    """
    Safely extract JSON from Gemini response.

    Gemini should return JSON directly, but this protects against
    accidental markdown fences.
    """

    if not text:
        raise ValueError(
            "Gemini returned an empty automation plan."
        )

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start >= 0 and end > start:
            return json.loads(
                cleaned[start:end + 1]
            )

        raise ValueError(
            "Gemini returned invalid JSON for automation plan."
        )


# ============================================================
# SPEC SERIALIZATION
# ============================================================

def build_planner_input(
    spec: AutomationSpec,
    application_context: str = "",
) -> str:

    payload = {
        "automation_spec": spec.model_dump(
            mode="json"
        ),
        "application_context": application_context,
    }

    return json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    )


# ============================================================
# GEMINI PLANNER
# ============================================================

def generate_automation_plan(
    spec: AutomationSpec,
    application_context: str = "",
) -> AutomationPlan:

    client = get_gemini_client()

    prompt = build_planner_input(
        spec=spec,
        application_context=application_context,
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                PLANNER_SYSTEM_PROMPT,
                prompt,
            ],
            config={
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        )
    except Exception as exc:
        message = str(exc)

        # Do not retry quota exhaustion here.
        if (
            "429" in message
            or "RESOURCE_EXHAUSTED" in message
            or "quota" in message.lower()
        ):
            raise RuntimeError(
                "Gemini API quota exceeded while creating "
                "the automation plan."
            ) from exc

        raise RuntimeError(
            f"Gemini automation planning failed: {exc}"
        ) from exc

    data = extract_json(
        getattr(response, "text", "") or ""
    )

    plan = AutomationPlan.model_validate(data)

    validate_automation_plan(
        spec=spec,
        plan=plan,
    )

    return plan


# ============================================================
# PLAN VALIDATION
# ============================================================

GENERIC_ACTION_PHRASES = (
    "perform the requested action",
    "perform the requested workflow",
    "execute the requested action",
    "complete the requested action",
    "perform the business action",
    "verify the resulting state",
)


def _normalise(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.lower().strip(),
    )


def _contains_generic_phrase(value: str) -> bool:
    text = _normalise(value)

    return any(
        phrase in text
        for phrase in GENERIC_ACTION_PHRASES
    )


def validate_automation_plan(
    spec: AutomationSpec,
    plan: AutomationPlan,
) -> None:

    errors: List[str] = []

    # --------------------------------------------------------
    # Basic identity
    # --------------------------------------------------------

    if plan.test_case_id != spec.test_case_id:
        errors.append(
            "Automation plan test_case_id does not match "
            "the Stage 1 test case."
        )

    if not plan.actions:
        errors.append(
            "Automation plan contains no actions."
        )

    # --------------------------------------------------------
    # Action traceability
    # --------------------------------------------------------

    stage1_steps = {
        step.step_number
        for step in spec.steps
    }

    planned_sources = {
        action.source_step
        for action in plan.actions
        if action.source_step is not None
    }

    missing_steps = (
        stage1_steps - planned_sources
    )

    if missing_steps:
        errors.append(
            "Stage 1 steps not represented in automation plan: "
            + ", ".join(
                str(x)
                for x in sorted(missing_steps)
            )
        )

    # --------------------------------------------------------
    # Generic action rejection
    # --------------------------------------------------------

    for action in plan.actions:

        target = action.business_target or ""

        if _contains_generic_phrase(target):
            errors.append(
                f"Generic automation target in step "
                f"{action.step_number}: {target}"
            )

    # --------------------------------------------------------
    # Assertion validation
    # --------------------------------------------------------

    if not plan.assertions:
        errors.append(
            "Automation plan contains no assertions."
        )

    # --------------------------------------------------------
    # Locator safety
    # --------------------------------------------------------

    for action in plan.actions:
        for candidate in action.locator_candidates:

            if candidate.strategy in {
                LocatorStrategy.CSS,
                LocatorStrategy.XPATH,
            }:
                value = candidate.value.strip()

                # Reject clearly fabricated/generated
                # placeholder selectors.
                if (
                    "generated" in value.lower()
                    or "example" in value.lower()
                    or "placeholder" in value.lower()
                ):
                    errors.append(
                        f"Unsupported locator candidate in "
                        f"step {action.step_number}: {value}"
                    )

    if errors:
        raise ValueError(
            "Automation plan failed validation:\n- "
            + "\n- ".join(errors)
        )
    