from application_context import inspect_application
from automation_models import (
    ActionType,
    AutomationFramework,
    AutomationLanguage,
)
from automation_planner import (
    AutomationPlan,
    PlannedAction,
    PlannedAssertion,
)
from automation_plan_resolver import (
    resolve_automation_plan,
)
from automation_service import (
    ensure_plan_resolved,
)
from automation_generator_dispatcher import (
    generate_automation,
)


URL = (
    "https://opensource-demo.orangehrmlive.com/"
    "web/index.php/auth/login"
)


def build_resolved_plan():
    context = inspect_application(URL)

    plan = AutomationPlan(
        test_case_id="TC-DISPATCH-ALL-001",
        title="Verify login fields",
        application_url=URL,
        actions=[
            PlannedAction(
                step_number=1,
                action=ActionType.FILL,
                business_target="Username",
                value_reference="test_username",
                source_step=1,
            ),
            PlannedAction(
                step_number=2,
                action=ActionType.FILL,
                business_target="Password",
                value_reference="test_password",
                source_step=2,
            ),
        ],
        assertions=[
            PlannedAssertion(
                assertion_type=ActionType.ASSERT_VISIBLE,
                business_target="Password",
                description="Password field is visible",
                source_expected_result=(
                    "Password field is visible"
                ),
            )
        ],
    )

    resolved = resolve_automation_plan(
        plan,
        context,
    )
    resolved = ensure_plan_resolved(resolved)

    if resolved.unresolved_targets:
        raise AssertionError(
            "Unresolved targets: "
            f"{resolved.unresolved_targets}"
        )

    return resolved


def main():
    resolved = build_resolved_plan()

    routes = [
        (
            AutomationFramework.SELENIUM,
            AutomationLanguage.PYTHON,
        ),
        (
            AutomationFramework.SELENIUM,
            AutomationLanguage.JAVA,
        ),
        (
            AutomationFramework.SELENIUM,
            AutomationLanguage.JAVASCRIPT,
        ),
        (
            AutomationFramework.PLAYWRIGHT,
            AutomationLanguage.PYTHON,
        ),
        (
            AutomationFramework.PLAYWRIGHT,
            AutomationLanguage.JAVA,
        ),
        (
            AutomationFramework.PLAYWRIGHT,
            AutomationLanguage.JAVASCRIPT,
        ),
        (
            AutomationFramework.APPIUM,
            AutomationLanguage.PYTHON,
        ),
        (
            AutomationFramework.APPIUM,
            AutomationLanguage.JAVA,
        ),
        (
            AutomationFramework.APPIUM,
            AutomationLanguage.JAVASCRIPT,
        ),
        (
            AutomationFramework.CYPRESS,
            AutomationLanguage.JAVASCRIPT,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 70)
    print("GENERATOR DISPATCHER INTEGRATION TEST")
    print("=" * 70)

    for framework, language in routes:
        route = (
            f"{framework.value} + "
            f"{language.value}"
        )

        try:
            result = generate_automation(
                framework,
                language,
                resolved,
            )

            if not result.code.strip():
                raise AssertionError(
                    "Generated code is empty."
                )

            print(
                f"{route:<40} "
                f"PASS -> {result.generator_name}"
            )

            passed += 1

        except Exception as exc:
            print(
                f"{route:<40} "
                f"FAIL -> {exc}"
            )

            failed += 1

    print("=" * 70)
    print(f"PASSED = {passed}")
    print(f"FAILED = {failed}")
    print("=" * 70)

    if failed:
        raise SystemExit(1)

    print(
        "GENERATOR_DISPATCHER_INTEGRATION_OK"
    )


if __name__ == "__main__":
    main()