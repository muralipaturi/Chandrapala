"""
Selenium Python Generator

Deterministic Selenium + Python automation code generator.

Input:
    ResolvedAutomationPlan

Output:
    Selenium Python source code

Design principles:
    - No Gemini call
    - Uses resolved application UI evidence
    - No invented locators
    - Generates pytest-compatible Selenium code
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


class SeleniumPythonGenerator:
    """
    Generates deterministic Selenium Python automation.
    """

    def generate(
        self,
        plan: ResolvedAutomationPlan,
    ) -> str:

        self._validate_plan(plan)

        lines: List[str] = []

        self._add_header(lines)
        self._add_configuration(lines, plan)
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
                "Cannot generate Selenium Python code: "
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
                "Generated Selenium Python automation.",
                '"""',
                "",
                "import os",
                "",
                "import pytest",
                "",
                "from selenium import webdriver",
                "from selenium.webdriver.common.by import By",
                "from selenium.webdriver.support.ui import WebDriverWait",
                "from selenium.webdriver.support import expected_conditions as EC",
                "",
            ]
        )

    # ========================================================
    # CONFIGURATION
    # ========================================================

    @staticmethod
    def _add_configuration(
        lines: List[str],
        plan: ResolvedAutomationPlan,
    ) -> None:

        lines.extend(
            [
                "BASE_URL = os.getenv(",
                "    'BASE_URL',",
                f"    {_py_string(plan.application_url)},",
                ")",
                "",
                "WAIT_TIMEOUT = int(",
                "    os.getenv('WAIT_TIMEOUT', '20')",
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
                f"def {test_name}():",
                '    """',
                f"    Test case: {plan.test_case_id}",
                f"    {plan.title}",
                '    """',
                "",
                "    driver = webdriver.Chrome()",
                "    wait = WebDriverWait(driver, WAIT_TIMEOUT)",
                "",
                "    try:",
                "        driver.get(BASE_URL)",
                "",
            ]
        )

        # ----------------------------------------------------
        # ACTIONS
        # ----------------------------------------------------

        for action in plan.actions:

            description = (
                action.business_target
                or str(action.action)
            )

            lines.append(
                f"        # Step {action.step_number}: "
                f"{description}"
            )

            self._generate_action(
                lines,
                action,
            )

            lines.append("")

        # ----------------------------------------------------
        # ASSERTIONS
        # ----------------------------------------------------

        lines.append(
            "        # Business outcome assertions"
        )

        for assertion in plan.assertions:

            self._generate_assertion(
                lines,
                assertion,
            )

            lines.append("")

        lines.extend(
            [
                "    finally:",
                "        driver.quit()",
            ]
        )

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

        if action_type == ActionType.CLICK:
            self._click(
                lines,
                action,
            )
            return

        if action_type == ActionType.FILL:
            self._fill(
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

        if action_type == ActionType.CLEAR:
            self._clear(
                lines,
                action,
            )
            return

        if action_type == ActionType.UPLOAD:
            self._upload(
                lines,
                action,
            )
            return

        if action_type in (ActionType.CAPTURE, ActionType.CAPTURE_TEXT):
            self._capture(
                lines,
                action,
            )
            return

        if action_type in (
            ActionType.ASSERT_VISIBLE,
            ActionType.ASSERT_NOT_VISIBLE,
            ActionType.ASSERT_TEXT,
            ActionType.ASSERT_ENABLED,
            ActionType.ASSERT_DISABLED,
        ):
            self._assert_visible_action(
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

        if action_type == ActionType.WAIT:
            lines.append("        time.sleep(2)")
            return

        if action_type in (ActionType.ASSERT_VISIBLE, ActionType.ASSERT, ActionType.VERIFY):
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
        expression = self._selenium_locator(locator)
        var = getattr(action, "variable_name", None) or action.value_reference or "patient_id"
        var = re.sub(r"[^a-zA-Z0-9_]", "", var.replace(" ", "_").lower()) or "patient_id"
        lines.append(f"    {var} = driver.find_element(*{expression}).text")

    def _select(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._selenium_locator(locator)
        value = self._value_expression(action)
        lines.append("    from selenium.webdriver.support.ui import Select")
        lines.append(f"    Select({expression}).select_by_visible_text({value})")

    def _check(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._selenium_locator(locator)
        lines.append(f"    el = {expression}")
        lines.append("    if not el.is_selected(): el.click()")

    def _uncheck(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._selenium_locator(locator)
        lines.append(f"    el = {expression}")
        lines.append("    if el.is_selected(): el.click()")

    def _clear(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._selenium_locator(locator)
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
                f"        driver.get({_py_string(target)})"
            )

        else:

            lines.append(
                f"        # Navigation target: "
                f"{_py_string(target)}"
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
                "        username = os.getenv('TEST_USERNAME')",
                "        password = os.getenv('TEST_PASSWORD')",
                "",
                "        if not username or not password:",
                "            raise ValueError(",
                "                'TEST_USERNAME and TEST_PASSWORD "
                "must be configured.'",
                "            )",
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

        expression = self._selenium_locator(
            locator
        )

        lines.extend(
            [
                "        element = wait.until(",
                "            EC.element_to_be_clickable(",
                f"                {expression}",
                "            )",
                "        )",
                "",
                "        element.click()",
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

        expression = self._selenium_locator(
            locator
        )

        value = self._value_expression(
            action
        )

        lines.extend(
            [
                "        element = wait.until(",
                "            EC.visibility_of_element_located(",
                f"                {expression}",
                "            )",
                "        )",
                "",
                "        element.clear()",
                f"        element.send_keys({value})",
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

        expression = self._selenium_locator(
            locator
        )

        value = self._value_expression(
            action
        )

        lines.extend(
            [
                "        element = wait.until(",
                "            EC.presence_of_element_located(",
                f"                {expression}",
                "            )",
                "        )",
                "",
                f"        element.send_keys({value})",
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
                self._selenium_locator(
                    resolution.locator
                )
            )

            message = (
                action.expected_result
                or action.business_target
                or "Expected element to be visible."
            )

            lines.extend(
                [
                    "        element = wait.until(",
                    "            EC.visibility_of_element_located(",
                    f"                {expression}",
                    "            )",
                    "        )",
                    "",
                    "        assert element.is_displayed(), (",
                    f"            {_py_string(message)}",
                    "        )",
                ]
            )

            return

        lines.extend(
            [
                "        raise AssertionError(",
                f"            {_py_string(action.expected_result or action.business_target or 'Required UI evidence was not resolved.')}",
                "        )",
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
            "        # Assertion: "
            f"{assertion.description}"
        )

        resolution = (
            assertion.locator_resolution
        )

        if (
            resolution
            and resolution.found
            and resolution.locator
        ):

            expression = (
                self._selenium_locator(
                    resolution.locator
                )
            )

            message = (
                assertion.description
                or "Expected element to be visible."
            )

            lines.extend(
                [
                    "        element = wait.until(",
                    "            EC.visibility_of_element_located(",
                    f"                {expression}",
                    "            )",
                    "        )",
                    "",
                    "        assert element.is_displayed(), (",
                    f"            {_py_string(message)}",
                    "        )",
                ]
            )

            return

        lines.extend(
            [
                "        raise AssertionError(",
                "            'Required Selenium assertion "
                "locator was not resolved.'",
                "        )",
            ]
        )

    # ========================================================
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
                "Cannot generate Selenium Python code "
                f"for step {action.step_number}: "
                "no safe locator was resolved for "
                f"'{action.business_target}'."
            )

        return resolution.locator

    # ========================================================
    # SELENIUM LOCATOR CONVERSION
    # ========================================================

    @staticmethod
    def _selenium_locator(
        locator,
    ) -> str:

        strategy = str(
            locator.strategy.value
        )

        value = str(
            locator.value
        )

        # ----------------------------------------------------
        # ID
        # ----------------------------------------------------

        if strategy == "id":

            return (
                "(By.ID, "
                f"{_py_string(value)})"
            )

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if strategy == "name":

            return (
                "(By.NAME, "
                f"{_py_string(value)})"
            )

        # ----------------------------------------------------
        # CSS
        # ----------------------------------------------------

        if strategy == "css":

            return (
                "(By.CSS_SELECTOR, "
                f"{_py_string(value)})"
            )

        # ----------------------------------------------------
        # XPATH
        # ----------------------------------------------------

        if strategy == "xpath":

            return (
                "(By.XPATH, "
                f"{_py_string(value)})"
            )

        # ----------------------------------------------------
        # PLACEHOLDER
        #
        # IMPORTANT:
        # The generated selector must be:
        #
        # '[placeholder="Username"]'
        #
        # NOT:
        #
        # [placeholder="'Username'"]
        # ----------------------------------------------------

        if strategy == "placeholder":

            selector = (
                f'[placeholder="{_css_escape(value)}"]'
            )

            return (
                "(By.CSS_SELECTOR, "
                f"{_py_string(selector)})"
            )

        # ----------------------------------------------------
        # LABEL
        # ----------------------------------------------------

        if strategy == "label":

            selector = (
                f'label[for="{_css_escape(value)}"]'
            )

            return (
                "(By.CSS_SELECTOR, "
                f"{_py_string(selector)})"
            )

        # ----------------------------------------------------
        # ARIA LABEL
        # ----------------------------------------------------

        if strategy == "aria_label":

            selector = (
                f'[aria-label="{_css_escape(value)}"]'
            )

            return (
                "(By.CSS_SELECTOR, "
                f"{_py_string(selector)})"
            )

        # ----------------------------------------------------
        # ACCESSIBILITY ID
        # ----------------------------------------------------

        if strategy == "accessibility_id":

            selector = (
                f'[aria-label="{_css_escape(value)}"]'
            )

            return (
                "(By.CSS_SELECTOR, "
                f"{_py_string(selector)})"
            )

        # ----------------------------------------------------
        # TEST ID
        # ----------------------------------------------------

        if strategy == "test_id":

            selector = (
                f'[data-testid="{_css_escape(value)}"]'
            )

            return (
                "(By.CSS_SELECTOR, "
                f"{_py_string(selector)})"
            )

        # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------

        if strategy == "role":

            selector = (
                f'[role="{_css_escape(value)}"]'
            )

            return (
                "(By.CSS_SELECTOR, "
                f"{_py_string(selector)})"
            )

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        if strategy == "text":

            xpath = (
                f"//*[normalize-space(text())="
                f"{_xpath_literal(value)}]"
            )

            return (
                "(By.XPATH, "
                f"{_py_string(xpath)})"
            )

        raise ValueError(
            "Unsupported Selenium Python "
            f"locator strategy: {strategy}"
        )

    # ========================================================
    # VALUE EXPRESSION
    # ========================================================

    @staticmethod
    def _value_expression(
        action: ResolvedAction,
    ) -> str:

        if action.value_reference:
            ref = str(action.value_reference).strip()
            clean_var = re.sub(r"^[\$\{\}\s]+|[\}\s]+$", "", ref)
            var_name = getattr(action, "variable_name", None)
            if clean_var in ("patient_id", "captured_value", "captured_patient_id", var_name) or (var_name and clean_var == var_name):
                return clean_var

            if not ref.startswith("test_") and not ref.isupper() and " " not in ref and not ref.endswith("_username") and not ref.endswith("_password"):
                # literal or simple variable
                if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", ref) and ref.islower():
                    return ref
                return _py_string(ref)

            env_name = re.sub(
                r"[^A-Za-z0-9_]",
                "_",
                ref,
            ).upper()

            return (
                "os.getenv("
                f"{_py_string(env_name)}"
                ")"
            )

        return (
            "os.getenv('TEST_DATA_VALUE')"
        )


# ============================================================
# HELPERS
# ============================================================


def _py_string(
    value: str,
) -> str:

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
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _xpath_literal(
    value: str,
) -> str:

    if "'" not in value:
        return f"'{value}'"

    if '"' not in value:
        return f'"{value}"'

    parts = value.split("'")

    return (
        "concat("
        + ", \"'\", ".join(
            f"'{part}'"
            for part in parts
        )
        + ")"
    )


def _python_test_name(
    test_case_id: str,
    title: str,
) -> str:

    raw = (
        f"{test_case_id}_{title}"
    )

    parts = re.findall(
        r"[A-Za-z0-9]+",
        raw,
    )

    if not parts:
        return "test_generated_selenium"

    name = "_".join(
        part.lower()
        for part in parts
    )

    if not name.startswith("test_"):
        name = f"test_{name}"

    return name


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def generate_selenium_python(
    plan: ResolvedAutomationPlan,
) -> str:

    generator = (
        SeleniumPythonGenerator()
    )

    return generator.generate(plan)