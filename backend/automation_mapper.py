"""
Stage 2.2
Convert Stage 1 TestCase -> Framework-independent AutomationSpec
"""

from typing import List

from automation_models import (
    ActionType,
    ApplicationType,
    AutomationAssertion,
    AutomationConfig,
    AutomationFramework,
    AutomationLanguage,
    AutomationSpec,
    AutomationStep,
    TestData,
    get_default_test_runner,
)

# Import your Stage 1 models
from ai_service import TestCase


# ============================================================
# ACTION INFERENCE
# ============================================================

def infer_action(step: str) -> ActionType:
    text = step.lower()

    if "login" in text or "sign in" in text:
        return ActionType.LOGIN

    if "open" in text or "navigate" in text:
        return ActionType.NAVIGATE

    if "click" in text or "select" in text:
        return ActionType.CLICK

    if "enter" in text or "fill" in text:
        return ActionType.FILL

    if "upload" in text:
        return ActionType.UPLOAD

    if "verify" in text or "confirm" in text:
        return ActionType.ASSERT_VISIBLE

    return ActionType.CLICK


# ============================================================
# TARGET EXTRACTION
# ============================================================

def extract_target(step: str) -> str | None:
    s = step.strip()

    prefixes = [
        "Navigate to ",
        "Open ",
        "Click ",
        "Select ",
        "Enter ",
        "Verify ",
        "Upload ",
        "Search for ",
        "Search ",
        "Login as ",
    ]

    for p in prefixes:
        if s.lower().startswith(p.lower()):
            return s[len(p):].strip()

    return s


# ============================================================
# TEST DATA EXTRACTION
# ============================================================

def extract_test_data(test_case: TestCase) -> List[TestData]:
    data: List[TestData] = []

    all_text = " ".join(test_case.steps).lower()

    if "username" in all_text:
        data.append(
            TestData(
                name="valid_username",
                value=None,
                generated=False,
            )
        )

    if "password" in all_text:
        data.append(
            TestData(
                name="valid_password",
                value=None,
                generated=False,
            )
        )

    if "employee id" in all_text:
        data.append(
            TestData(
                name="existing_employee_id",
                value=None,
                generated=False,
            )
        )

    return data


# ============================================================
# ASSERTION GENERATION
# ============================================================

def build_assertions(test_case: TestCase) -> List[AutomationAssertion]:
    return [
        AutomationAssertion(
            assertion_type=ActionType.ASSERT_VISIBLE,
            description=test_case.expected_result,
            source_expected_result=test_case.expected_result,
        )
    ]


# ============================================================
# MAIN CONVERTER
# ============================================================

def test_case_to_spec(
    test_case: TestCase,
    requirement: str,
    application_url: str,
    framework: AutomationFramework,
    language: AutomationLanguage,
) -> AutomationSpec:

    steps: List[AutomationStep] = []

    for i, step in enumerate(test_case.steps, start=1):
        steps.append(
            AutomationStep(
                step_number=i,
                action=infer_action(step),
                target=extract_target(step),
                expected_result=(
                    test_case.expected_result
                    if i == len(test_case.steps)
                    else None
                ),
                source_step=i,
            )
        )

    return AutomationSpec(
        test_case_id=test_case.id,
        title=test_case.title,
        test_type=test_case.type,
        priority=test_case.priority,
        requirement=requirement,
        application_url=application_url,
        framework=framework,
        language=language,
        application_type=ApplicationType.WEB,
        test_runner=get_default_test_runner(framework, language),
        preconditions=[],
        test_data=extract_test_data(test_case),
        steps=steps,
        assertions=build_assertions(test_case),
        configuration=AutomationConfig(
            browser="chrome",
            base_url=application_url,
            headless=True,
        ),
    )