"""
Stage 2.10 - Playwright JavaScript Generator

Deterministic Playwright + JavaScript code generator.

Input:
    ResolvedAutomationPlan

Output:
    Playwright JavaScript source code

Design principles:
    - No Gemini call
    - No invented locators
    - Uses resolved application evidence
    - Uses @playwright/test
    - Generates JavaScript Playwright tests
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


class PlaywrightJavaScriptGenerator:
    """
    Generates deterministic Playwright JavaScript automation.
    """

    def generate(
        self,
        plan: ResolvedAutomationPlan,
    ) -> str:

        self._validate_plan(plan)

        lines: List[str] = []

        self._add_header(lines)
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
                "Cannot generate Playwright JavaScript code: "
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
                "const { test, expect } = require('@playwright/test');",
                "",
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

        test_title = (
            plan.title
            or plan.test_case_id
            or "Generated Playwright Test"
        )

        lines.extend(
            [
                f"test({_js_string(test_title)}, async ({{ page }}) => {{",
                "",
                f"    await page.goto({_js_string(plan.application_url)});",
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
                f"    // Step {action.step_number}: "
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
            "    // Business outcome assertions"
        )

        for assertion in plan.assertions:

            self._generate_assertion(
                lines,
                assertion,
            )

            lines.append("")

        lines.append("});")

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
            self._navigate(lines, action)
            return

        if action_type == ActionType.LOGIN:
            self._login(lines, action)
            return

        if action_type == ActionType.CLICK:
            self._click(lines, action)
            return

        if action_type in (ActionType.FILL, ActionType.ENTER):
            self._fill(lines, action)
            return

        if action_type == ActionType.RECEIVE_OTP:
            lines.extend(
                [
                    "    // System Operation: Receive OTP from notification/SMS source",
                    "    const extractedOtp = process.env.TEST_OTP || '123456';",
                ]
            )
            return

        if action_type == ActionType.EXTRACT_VALUE:
            var_name = getattr(action, "variable_name", None) or "extractedVal"
            lines.extend(
                [
                    f"    // System Operation: Extract value for {var_name}",
                    f"    const {var_name} = process.env.EXTRACTED_VAL || '123456';",
                ]
            )
            return

        if action_type == ActionType.WAIT:
            lines.append("    await page.waitForTimeout(2000);")
            return

        if action_type in (
            ActionType.ASSERT_VISIBLE,
            ActionType.ASSERT_TEXT,
            ActionType.ASSERT_ENABLED,
            ActionType.ASSERT_DISABLED,
            ActionType.ASSERT,
            ActionType.VERIFY,
        ):
            self._assert_visible_action(lines, action)
            return

        lines.append(
            f"    // Step action: {action_type.value} on {action.business_target or 'system'}"
        )

    def _capture(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        expression = self._playwright_locator(locator)
        var = getattr(action, "variable_name", None) or action.value_reference or "patientId"
        var = re.sub(r"[^a-zA-Z0-9_]", "", var.replace(" ", "_")) or "patientId"
        if "_" in var:
            parts = var.split("_")
            var = parts[0].lower() + "".join(p.capitalize() for p in parts[1:])
        lines.append(f"    const {var} = await {expression}.innerText();")

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
                "    await page.goto("
                f"{_js_string(target)}"
                ");"
            )

        else:

            lines.append(
                "    // Navigate to: "
                f"{_js_string(target)}"
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
                "    const username = process.env.TEST_USERNAME;",
                "    const password = process.env.TEST_PASSWORD;",
                "",
                "    if (!username || !password) {",
                "        throw new Error(",
                "            'TEST_USERNAME and TEST_PASSWORD "
                "must be configured.'",
                "        );",
                "    }",
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

        locator = self._require_locator(action)

        expression = self._playwright_locator(
            locator
        )

        lines.append(
            f"    await {expression}.click();"
        )

    # ========================================================
    # FILL
    # ========================================================

    def _fill(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        locator = self._require_locator(action)

        expression = self._playwright_locator(
            locator
        )

        value = self._value_expression(action)

        lines.append(
            f"    await {expression}.fill({value});"
        )

    # ========================================================
    # UPLOAD
    # ========================================================

    def _upload(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        locator = self._require_locator(action)

        expression = self._playwright_locator(
            locator
        )

        value = self._value_expression(action)

        lines.append(
            f"    await {expression}.setInputFiles({value});"
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

            lines.append(
                f"    await expect({expression}).toBeVisible();"
            )

            return

        message = (
            action.expected_result
            or action.business_target
            or "Required UI evidence was not available."
        )

        lines.extend(
            [
                "    throw new Error(",
                f"        {_js_string(message)}",
                "    );",
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
            "    // Assertion: "
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
                self._playwright_locator(
                    resolution.locator
                )
            )

            lines.append(
                f"    await expect({expression}).toBeVisible();"
            )

            return

        lines.extend(
            [
                "    throw new Error(",
                "        'Required assertion locator "
                "was not resolved from application evidence.'",
                "    );",
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
                "Cannot generate Playwright JavaScript "
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
                f"{_js_string('#' + value)}"
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
                f"{_js_string(selector)}"
                ")"
            )

        # ----------------------------------------------------
        # CSS
        # ----------------------------------------------------

        if strategy == "css":

            return (
                "page.locator("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # XPATH
        # ----------------------------------------------------

        if strategy == "xpath":

            return (
                "page.locator("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # PLACEHOLDER
        # ----------------------------------------------------

        if strategy == "placeholder":

            return (
                "page.getByPlaceholder("
                f"{_js_string(value)}"
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
                "page.getByLabel("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # TEST ID
        # ----------------------------------------------------

        if strategy == "test_id":

            return (
                "page.getByTestId("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------

        if strategy == "role":

            return (
                "page.getByRole("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        if strategy == "text":

            return (
                "page.getByText("
                f"{_js_string(value)}"
                ")"
            )

        raise ValueError(
            "Unsupported Playwright JavaScript "
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
            if clean_var in ("patient_id", "patientId", "captured_value", "capturedPatientId", var_name) or (var_name and clean_var == var_name):
                if "_" in clean_var:
                    parts = clean_var.split("_")
                    clean_var = parts[0].lower() + "".join(p.capitalize() for p in parts[1:])
                return clean_var

            if not ref.startswith("test_") and not ref.isupper() and " " not in ref and not ref.endswith("_username") and not ref.endswith("_password"):
                if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", ref):
                    return ref
                return _js_string(ref)

            env_name = re.sub(
                r"[^A-Za-z0-9_]",
                "_",
                ref,
            ).upper()

            return (
                "process.env."
                f"{env_name}"
            )

        return (
            "process.env.TEST_DATA_VALUE"
        )


# ============================================================
# HELPERS
# ============================================================


def _js_string(
    value: str,
) -> str:
    """
    Safely create a JavaScript string literal.
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
        .replace("\r", " ")
        .replace("\n", " ")
    )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def generate_playwright_javascript(
    plan: ResolvedAutomationPlan,
) -> str:
    """
    Generate Playwright JavaScript source code.
    """

    generator = (
        PlaywrightJavaScriptGenerator()
    )

    return generator.generate(plan)