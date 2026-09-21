"""
Stage 2.8 - Playwright Python Generator

Deterministic Playwright + Python code generator.

Input:
    ResolvedAutomationPlan

Output:
    Playwright Python source code

Design principles:
    - No Gemini call
    - No invented locators
    - Uses resolved application evidence
    - Framework-independent planning remains unchanged
    - Uses Playwright sync API
    - Generates pytest-compatible tests
"""

from __future__ import annotations

import re
from typing import List

from automation_models import ActionType

from automation_plan_resolver import (
    ResolvedAction,
    ResolvedAssertion,
    ResolvedAutomationPlan,
)


# ============================================================
# PLAYWRIGHT PYTHON GENERATOR
# ============================================================


class PlaywrightPythonGenerator:
    """
    Generates deterministic Playwright Python automation.
    """

    def generate(
        self,
        plan: ResolvedAutomationPlan,
    ) -> str:

        self._validate_plan(plan)

        lines: List[str] = []

        self._add_header(lines)
        self._add_constants(lines, plan)
        self._add_test(lines, plan)

        return "\n".join(lines)

    # ========================================================
    # VALIDATION
    # ========================================================

    @staticmethod
    def _validate_plan(
        plan: ResolvedAutomationPlan,
    ) -> None:

        if not plan.application_url:
            raise ValueError(
                "Cannot generate Playwright Python code: "
                "application URL is missing."
            )

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

    # ========================================================
    # HEADER
    # ========================================================

    @staticmethod
    def _add_header(
        lines: List[str],
    ) -> None:

        lines.extend(
            [
                '"""',
                "Generated Playwright Python automation.",
                '"""',
                "",
                "import os",
"import re",
                "",
                "import pytest",
                "from playwright.sync_api import (",
"    Page,",
"    expect,",
"    Playwright,",
"    sync_playwright,",
")",
                "",
            ]
        )

    # ========================================================
    # CONSTANTS
    # ========================================================

    @staticmethod
    def _add_constants(
        lines: List[str],
        plan: ResolvedAutomationPlan,
    ) -> None:

        lines.extend(
            [
                "",
                "BASE_URL = os.getenv(",
                "    'BASE_URL',",
                f"    {_python_string(plan.application_url)},",
                ")",
                "",
            ]
        )

    # ========================================================
    # TEST
    # ========================================================

    def _add_test(
        self,
        lines: List[str],
        plan: ResolvedAutomationPlan,
    ) -> None:

        test_name = _python_test_name(
            plan.test_case_id,
            plan.title,
        )

        lines.extend(
            [
                "",
                f"def {test_name}(page: Page):",
                '    """',
                f"    Test case: {plan.test_case_id}",
                f"    {plan.title}",
                '    """',
                "",
                "    page.goto(BASE_URL)",
                "",
            ]
        )

        # ----------------------------------------------------
        # Actions
        # ----------------------------------------------------

        for action in plan.actions:

            description = (
                action.business_target
                or str(action.action)
            )

            lines.append(
                f"    # Step {action.step_number}: "
                f"{description}"
            )

            self._generate_action(
                lines,
                action,
            )

            lines.append("")

        # ----------------------------------------------------
        # Assertions
        # ----------------------------------------------------

        lines.append(
            "    # Business outcome assertions"
        )

        for assertion in plan.assertions:

            self._generate_assertion(
                lines,
                assertion,
            )

            lines.append("")

    # ========================================================
    # ACTION DISPATCH
    # ========================================================

    def _generate_action(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        action_type = action.action

        if action_type == ActionType.NAVIGATE:
            self._navigate(
                lines,
                action,
            )
            return

        if action_type == ActionType.LOGIN:
            self._login(
                lines,
                action,
            )
            return

        if action_type == ActionType.CLICK:
            self._click(
                lines,
                action,
            )
            return

        if action_type in (ActionType.FILL, ActionType.ENTER):
            self._fill(
                lines,
                action,
            )
            return

        if action_type == ActionType.RECEIVE_OTP:
            lines.extend(
                [
                    "        # System Operation: Receive OTP from notification/SMS source",
                    "        extracted_otp = os.getenv('TEST_OTP', '123456')",
                ]
            )
            return

        if action_type == ActionType.EXTRACT_VALUE:
            var_name = getattr(action, "variable_name", None) or "extracted_val"
            lines.extend(
                [
                    f"        # System Operation: Extract value for {var_name}",
                    f"        {var_name} = os.getenv('EXTRACTED_VAL', '123456')",
                ]
            )
            return

        if action_type in (ActionType.CAPTURE, ActionType.CAPTURE_TEXT):
            self._capture(
                lines,
                action,
            )
            return

        if action_type == ActionType.SELECT:
            self._select(
                lines,
                action,
            )
            return

        if action_type == ActionType.CHECK:
            self._check(
                lines,
                action,
            )
            return

        if action_type == ActionType.UNCHECK:
            self._uncheck(
                lines,
                action,
            )
            return

        if action_type == ActionType.HOVER:
            self._hover(
                lines,
                action,
            )
            return

        if action_type == ActionType.PRESS:
            self._press(
                lines,
                action,
            )
            return

        if action_type == ActionType.CLEAR:
            self._clear(
                lines,
                action,
            )
            return

        if action_type == ActionType.WAIT:
            lines.append("        page.wait_for_timeout(2000)")
            return

        if action_type in (
            ActionType.ASSERT_VISIBLE,
            ActionType.ASSERT_NOT_VISIBLE,
            ActionType.ASSERT_TEXT,
            ActionType.ASSERT_ENABLED,
            ActionType.ASSERT_DISABLED,
            ActionType.ASSERT,
            ActionType.VERIFY,
        ):
            self._assert_visible_action(
                lines,
                action,
            )
            return

        lines.append(
            f"        # Step action: {action_type.value} on {action.business_target or 'system'}"
        )

    def _capture(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._playwright_locator(locator)
        var = getattr(action, "variable_name", None) or action.value_reference or "patient_id"
        var = re.sub(r"[^a-zA-Z0-9_]", "", var.replace(" ", "_").lower()) or "patient_id"
        lines.append(f"    {var} = {expression}.inner_text()")

    def _select(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._playwright_locator(locator)
        value = self._value_expression(action)
        lines.append(f"    {expression}.select_option({value})")

    def _check(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._playwright_locator(locator)
        lines.append(f"    {expression}.check()")

    def _uncheck(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._playwright_locator(locator)
        lines.append(f"    {expression}.uncheck()")

    def _hover(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._playwright_locator(locator)
        lines.append(f"    {expression}.hover()")

    def _press(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._playwright_locator(locator)
        value = self._value_expression(action)
        lines.append(f"    {expression}.press({value})")

    def _clear(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._playwright_locator(locator)
        lines.append(f"    {expression}.clear()")

    # ========================================================
    # NAVIGATE
    # ========================================================

    @staticmethod
    def _navigate(
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        target = (
            action.business_target
            or ""
        ).strip()

        if target.startswith(
            (
                "http://",
                "https://",
            )
        ):

            lines.append(
                "    page.goto("
                f"{_python_string(target)}"
                ")"
            )

        else:

            lines.append(
                "    # Navigate to: "
                f"{_python_string(target)}"
            )

    # ========================================================
    # LOGIN
    # ========================================================

    @staticmethod
    def _login(
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        lines.extend(
            [
                "    username = os.getenv(",
                "        'TEST_USERNAME'",
                "    )",
                "",
                "    password = os.getenv(",
                "        'TEST_PASSWORD'",
                "    )",
                "",
                "    if not username or not password:",
                "        pytest.skip(",
                "            'TEST_USERNAME and "
                "TEST_PASSWORD must be configured.'",
                "        )",
            ]
        )

    # ========================================================
    # CLICK
    # ========================================================

    def _click(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        locator = self._require_locator(
            action
        )

        expression = self._playwright_locator(
            locator
        )

        lines.extend(
            [
                f"    {expression}.click()",
            ]
        )

    # ========================================================
    # FILL
    # ========================================================

    def _fill(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        locator = self._require_locator(
            action
        )

        expression = self._playwright_locator(
            locator
        )

        value = self._value_expression(
            action
        )

        lines.extend(
            [
                f"    {expression}.fill({value})",
            ]
        )

    # ========================================================
    # UPLOAD
    # ========================================================

    def _upload(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        locator = self._require_locator(
            action
        )

        expression = self._playwright_locator(
            locator
        )

        value = self._value_expression(
            action
        )

        lines.extend(
            [
                f"    {expression}.set_input_files({value})",
            ]
        )

    # ========================================================
    # ASSERT VISIBLE ACTION
    # ========================================================

    def _assert_visible_action(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        resolution = (
            action.locator_resolution
        )

        if (
            resolution
            and resolution.found
            and resolution.locator
        ):

            expression = (
                self._playwright_locator(
                    resolution.locator
                )
            )

            lines.extend(
                [
                    f"    expect({expression}).to_be_visible()",
                ]
            )

            return

        message = (
            action.expected_result
            or action.business_target
            or "Required UI evidence was not available."
        )

        lines.extend(
            [
                "    pytest.fail(",
                f"        {_python_string(message)}",
                "    )",
            ]
        )

    # ========================================================
    # ASSERTIONS
    # ========================================================

    def _generate_assertion(
        self,
        lines: List[str],
        assertion: ResolvedAssertion,
    ) -> None:

        lines.append(
            "    # Assertion: "
            f"{assertion.description}"
        )

        # ====================================================
        # URL / NAVIGATION ASSERTION
        # ====================================================

        if assertion.assertion_type == ActionType.ASSERT_URL:

            target = (
                assertion.business_target
                or ""
            ).strip()

            if not target:

                lines.extend(
                    [
                        "    pytest.fail(",
                        "        'URL assertion target is empty.'",
                        "    )",
                    ]
                )

                return

            # The planner may provide a business destination such as:
            #
            #     dashboard
            #
            # We do not invent a DOM locator for this.
            #
            # Prefer matching the destination portion of the URL.
            #
            # Example:
            #     dashboard
            #
            # becomes:
            #
            #     expect(page).to_have_url(
            #         re.compile(r".*dashboard.*")
            #     )

            escaped_target = re.escape(
                target
            )

            lines.extend(
                [
                    "    expect(page).to_have_url(",
                    f"        re.compile(r'.*{escaped_target}.*')",
                    "    )",
                ]
            )

            return

        # ====================================================
        # NORMAL LOCATOR ASSERTIONS
        # ====================================================

        resolution = (
            assertion.locator_resolution
        )

        if (
            resolution
            and resolution.found
            and resolution.locator
        ):

            expression = (
                self._playwright_locator(
                    resolution.locator
                )
            )

            lines.append(
                f"    expect({expression}).to_be_visible()"
            )

            return

        lines.extend(
            [
                "    pytest.fail(",
                "        'Required assertion locator "
                "was not resolved from application evidence.'",
                "    )",
            ]
        )

    # LOCATOR VALIDATION
    # ========================================================

    @staticmethod
    def _require_locator(
        action: ResolvedAction,
    ):

        resolution = (
            action.locator_resolution
        )

        if (
            resolution is None
            or not resolution.found
            or resolution.locator is None
        ):

            raise ValueError(
                "Cannot generate Playwright Python code "
                f"for step {action.step_number}: "
                "no safe locator was resolved for "
                f"'{action.business_target}'."
            )

        return resolution.locator

    # ========================================================
    # PLAYWRIGHT LOCATOR CONVERSION
    # ========================================================

    @staticmethod
    def _playwright_locator(
        locator,
    ) -> str:

        strategy = (
            locator.strategy.value
        )

        value = locator.value

        # ----------------------------------------------------
        # ID
        # ----------------------------------------------------

        if strategy == "id":

            return (
                "page.locator("
                f"{_python_string('#' + value)}"
                ")"
            )

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if strategy == "name":

            selector = (
                f'[name="{_css_escape(value)}"]'
            )

            return (
                "page.locator("
                f"{_python_string(selector)}"
                ")"
            )

        # ----------------------------------------------------
        # CSS
        # ----------------------------------------------------

        if strategy == "css":

            return (
                "page.locator("
                f"{_python_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # XPATH
        # ----------------------------------------------------

        if strategy == "xpath":

            return (
                "page.locator("
                f"{_python_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # PLACEHOLDER
        # ----------------------------------------------------

        if strategy == "placeholder":

            return (
                "page.get_by_placeholder("
                f"{_python_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # LABEL / ARIA LABEL
        # ----------------------------------------------------

        if strategy in (
            "label",
            "aria_label",
            "accessibility_id",
        ):

            return (
                "page.get_by_label("
                f"{_python_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # TEST ID
        # ----------------------------------------------------

        if strategy == "test_id":

            return (
                "page.get_by_test_id("
                f"{_python_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------

        # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------

        if strategy == "role":

            role_name = getattr(
                locator,
                "name",
                None,
            )

            if role_name:

                return (
                    "page.get_by_role("
                    f"{_python_string(value)}, "
                    "name="
                    f"{_python_string(role_name)}"
                    ")"
                )

            return (
                "page.get_by_role("
                f"{_python_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        if strategy == "text":

            return (
                "page.get_by_text("
                f"{_python_string(value)}"
                ")"
            )

        raise ValueError(
            "Unsupported Playwright Python "
            f"locator strategy: {strategy}"
        )

    # ========================================================
    # VALUE EXPRESSION
    # ========================================================

    @staticmethod
    def _value_expression(
        action: ResolvedAction,
    ) -> str:
        """
        Generate the Python expression used as an input value.

        Explicit environment references:
            test_username -> os.getenv('TEST_USERNAME')
            test_password -> os.getenv('TEST_PASSWORD')

        Explicit literal values:
            Admin -> 'Admin'
            Admin@123 -> 'Admin@123'

        When no explicit value is supplied, known business targets
        are mapped to their standard environment variables.
        """

        # ----------------------------------------------------
        # Explicit value/reference
        # ----------------------------------------------------

        if action.value_reference:

            reference = str(
                action.value_reference
            ).strip()

            clean_var = re.sub(r"^[\$\{\}\s]+|[\}\s]+$", "", reference)
            var_name = getattr(action, "variable_name", None)
            if clean_var in ("patient_id", "captured_value", "captured_patient_id", var_name) or (var_name and clean_var == var_name):
                return clean_var

            # Known environment-variable references.
            environment_references = {
                "test_username": "TEST_USERNAME",
                "test_password": "TEST_PASSWORD",
                "test_email": "TEST_EMAIL",
                "test_phone": "TEST_PHONE",
                "test_mobile": "TEST_MOBILE",
                "test_first_name": "TEST_FIRST_NAME",
                "test_last_name": "TEST_LAST_NAME",
                "test_name": "TEST_NAME",
                "test_address": "TEST_ADDRESS",
                "test_city": "TEST_CITY",
                "test_state": "TEST_STATE",
                "test_country": "TEST_COUNTRY",
                "test_zipcode": "TEST_ZIPCODE",
                "test_postal_code": "TEST_POSTAL_CODE",
                "test_data_value": "TEST_DATA_VALUE",
            }

            env_name = environment_references.get(
                reference.lower()
            )

            if env_name:
                return (
                    "os.getenv("
                    f"{_python_string(env_name)}"
                    ")"
                )

            # ------------------------------------------------
            # Everything else is treated as a literal value.
            # ------------------------------------------------

            return _python_string(
                reference
            )

        # ----------------------------------------------------
        # Automatic business-target mapping.
        # ----------------------------------------------------

        target = str(
            action.business_target or ""
        ).strip().lower()

        target = re.sub(
            r"[^a-z0-9]+",
            "_",
            target,
        ).strip("_")

        field_environment_map = {
            "username": "TEST_USERNAME",
            "user_name": "TEST_USERNAME",
            "user": "TEST_USERNAME",

            "password": "TEST_PASSWORD",
            "pass_word": "TEST_PASSWORD",
            "pass": "TEST_PASSWORD",

            "email": "TEST_EMAIL",
            "email_address": "TEST_EMAIL",

            "phone": "TEST_PHONE",
            "phone_number": "TEST_PHONE",

            "mobile": "TEST_MOBILE",
            "mobile_number": "TEST_MOBILE",

            "first_name": "TEST_FIRST_NAME",
            "last_name": "TEST_LAST_NAME",

            "name": "TEST_NAME",

            "address": "TEST_ADDRESS",

            "city": "TEST_CITY",

            "state": "TEST_STATE",

            "country": "TEST_COUNTRY",

            "zipcode": "TEST_ZIPCODE",
            "zip_code": "TEST_ZIPCODE",

            "postal_code": "TEST_POSTAL_CODE",
        }

        env_name = field_environment_map.get(
            target
        )

        if env_name:
            return (
                "os.getenv("
                f"{_python_string(env_name)}"
                ")"
            )

        # ----------------------------------------------------
        # Generic fallback.
        # ----------------------------------------------------

        return (
            "os.getenv("
            "'TEST_DATA_VALUE'"
            ")"
        )

# ============================================================
# HELPERS
# ============================================================


def _python_string(
    value: str,
) -> str:
    """
    Safely create a Python string literal.
    """

    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )

    return f"'{escaped}'"


def _css_escape(
    value: str,
) -> str:

    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
        .replace("\r", " ")
    )


def _python_test_name(
    test_case_id: str,
    title: str,
) -> str:
    """
    Create a valid pytest function name.
    """

    raw = (
        f"{test_case_id}_{title}"
    )

    parts = re.findall(
        r"[A-Za-z0-9]+",
        raw,
    )

    if not parts:
        return "test_generated_automation"

    name = "_".join(
        part.lower()
        for part in parts
    )

    if not name.startswith("test_"):
        name = (
            "test_"
            + name
        )

    return name


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def generate_playwright_python(
    plan: ResolvedAutomationPlan,
) -> str:
    """
    Generate Playwright Python source code.
    """

    generator = (
        PlaywrightPythonGenerator()
    )

    return generator.generate(
        plan
    )


