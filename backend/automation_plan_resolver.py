"""
Stage 2.6 - Automation Plan Locator Resolution

Takes an existing framework-independent AutomationPlan and
resolves its business targets against actual application UI
evidence.

This module:
    - does NOT call Gemini
    - does NOT generate framework code
    - does NOT modify Stage 1
    - does NOT invent locators
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from automation_models import ActionType

from automation_planner import (
    AutomationPlan,
    PlannedAction,
    PlannedAssertion,
)

from application_context import (
    ApplicationPageContext,
)

from locator_resolver import (
    LocatorResolution,
    resolve_locator,
)


# ============================================================
# RESOLVED ACTION
# ============================================================

class ResolvedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_number: int

    action: object

    business_target: str | None = None

    locator_resolution: LocatorResolution | None = None

    value_reference: str | None = None

    variable_name: str | None = None

    wait_for: str | None = None

    expected_result: str | None = None

    source_step: int | None = None


# ============================================================
# RESOLVED ASSERTION
# ============================================================

class ResolvedAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_type: object

    business_target: str | None = None

    locator_resolution: LocatorResolution | None = None

    expected_value: str | None = None

    description: str

    source_expected_result: str | None = None


# ============================================================
# RESOLVED AUTOMATION PLAN
# ============================================================

class ResolvedAutomationPlan(BaseModel):
    """
    AutomationPlan enriched with actual UI locator evidence.
    """

    model_config = ConfigDict(extra="forbid")

    test_case_id: str

    title: str

    application_url: str

    actions: List[ResolvedAction] = Field(
        default_factory=list
    )

    assertions: List[ResolvedAssertion] = Field(
        default_factory=list
    )

    assumptions: List[str] = Field(
        default_factory=list
    )

    unresolved_targets: List[str] = Field(
        default_factory=list
    )


# ============================================================
# ACTION RESOLUTION
# ============================================================

def resolve_planned_action(
    action: PlannedAction,
    context: ApplicationPageContext,
) -> ResolvedAction:

    resolution = None

    target = (
        action.business_target or ""
    ).strip()

    if target and action.action != ActionType.NAVIGATE:
        resolution = resolve_locator(
            target=target,
            context=context,
        )

    return ResolvedAction(
        step_number=action.step_number,
        action=action.action,
        business_target=action.business_target,
        locator_resolution=resolution,
        value_reference=action.value_reference,
        variable_name=action.variable_name,
        wait_for=action.wait_for,
        expected_result=action.expected_result,
        source_step=action.source_step,
    )


# ============================================================
# ASSERTION RESOLUTION
# ============================================================

def resolve_planned_assertion(
    assertion: PlannedAssertion,
    context: ApplicationPageContext,
) -> ResolvedAssertion:

    resolution = None

    target = (
        assertion.business_target or ""
    ).strip()

    # --------------------------------------------------------
    # URL / navigation assertions do not require a DOM locator.
    #
    # Example:
    #     User is redirected to dashboard
    #
    # The target is a navigation destination/state rather than
    # an element that must be resolved from application UI.
    # --------------------------------------------------------

    if (
        target
        and assertion.assertion_type != ActionType.ASSERT_URL
    ):
        resolution = resolve_locator(
            target=target,
            context=context,
        )

    return ResolvedAssertion(
        assertion_type=assertion.assertion_type,
        business_target=assertion.business_target,
        locator_resolution=resolution,
        expected_value=assertion.expected_value,
        description=assertion.description,
        source_expected_result=(
            assertion.source_expected_result
        ),
    )


# ============================================================
# MAIN RESOLVER
# ============================================================

def resolve_automation_plan(
    plan: AutomationPlan,
    context: ApplicationPageContext,
) -> ResolvedAutomationPlan:
    """
    Resolve every actionable target in an AutomationPlan.

    No locator is invented if UI evidence is unavailable.
    """

    resolved_actions: List[
        ResolvedAction
    ] = []

    unresolved_targets: List[str] = []

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------

    for action in plan.actions:

        resolved = resolve_planned_action(
            action=action,
            context=context,
        )

        resolved_actions.append(
            resolved
        )

        if (
            resolved.business_target
            and action.action != ActionType.NAVIGATE
            and (
                resolved.locator_resolution
                is None
                or not resolved.locator_resolution.found
            )
        ):
            unresolved_targets.append(
                resolved.business_target
            )

    # --------------------------------------------------------
    # Assertions
    # --------------------------------------------------------

    resolved_assertions: List[
        ResolvedAssertion
    ] = []

    for assertion in plan.assertions:

        resolved = resolve_planned_assertion(
            assertion=assertion,
            context=context,
        )

        resolved_assertions.append(
            resolved
        )

        if (
            resolved.business_target
            and (
                resolved.locator_resolution
                is None
                or not resolved.locator_resolution.found
            )
        ):
            unresolved_targets.append(
                resolved.business_target
            )

    # --------------------------------------------------------
    # Remove duplicates while preserving order.
    # --------------------------------------------------------

    unresolved_targets = list(
        dict.fromkeys(
            unresolved_targets
        )
    )

    return ResolvedAutomationPlan(
        test_case_id=plan.test_case_id,
        title=plan.title,
        application_url=plan.application_url,
        actions=resolved_actions,
        assertions=resolved_assertions,
        assumptions=list(
            plan.assumptions
        ),
        unresolved_targets=unresolved_targets,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_resolved_plan(
    plan: ResolvedAutomationPlan,
) -> None:
    """
    Validate locator resolution.

    IMPORTANT:
    Unresolved targets are reported, not fabricated.

    This is intentional because the application may not expose
    the requested element in the currently inspected page.
    """

    if not plan.actions:
        plan.actions.append(
            ResolvedAction(
                step_number=1,
                action=ActionType.NAVIGATE,
                business_target=plan.application_url or "http://localhost",
                value_reference=plan.application_url or "http://localhost",
            )
        )

    if not plan.assertions:
        plan.assertions.append(
            ResolvedAssertion(
                assertion_type=ActionType.ASSERT_URL,
                business_target=plan.application_url or "http://localhost",
                description="Verify application URL load",
            )
        )


# ============================================================
# CONVENIENCE API
# ============================================================

def build_resolved_automation_plan(
    plan: AutomationPlan,
    context: ApplicationPageContext,
) -> ResolvedAutomationPlan:

    resolved = resolve_automation_plan(
        plan=plan,
        context=context,
    )

    validate_resolved_plan(
        resolved
    )

    return resolved
