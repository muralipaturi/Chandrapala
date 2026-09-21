"""
Stage 2.12.1 - Cypress JavaScript Generator

Deterministic Cypress + JavaScript code generator.

Input:
    ResolvedAutomationPlan

Output:
    Cypress JavaScript source code

Design principles:
    - Cypress supports JavaScript only in this generator
    - No Gemini call
    - No invented locators
    - Uses resolved application UI evidence
    - Generates Cypress-compatible test code
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


class CypressJavaScriptGenerator:
    """
    Generates deterministic Cypress JavaScript automation.
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
                "Cannot generate Cypress JavaScript code: "
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
                "describe('Generated Test Cases', () => {",
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

        title = (
            plan.title
            or plan.test_case_id
            or "Generated Cypress Test"
        )

        lines.extend(
            [
                f"    it({_js_string(title)}, () => {{",
                "",
                f"        cy.visit({_js_string(plan.application_url)});",
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
                f"        // Step {action.step_number}: "
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
            "        // Business outcome assertions"
        )

        for assertion in plan.assertions:

            self._generate_assertion(
                lines,
                assertion,
            )

            lines.append("")

        lines.extend(
            [
                "    });",
                "",
                "});",
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
            self._navigate(lines, action)
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
                    "        // System Operation: Receive OTP from notification/SMS source",
                    "        const extractedOtp = Cypress.env('TEST_OTP') || '123456';",
                ]
            )
            return

        if action_type == ActionType.EXTRACT_VALUE:
            var_name = getattr(action, "variable_name", None) or "extractedVal"
            lines.extend(
                [
                    f"        // System Operation: Extract value for {var_name}",
                    f"        const {var_name} = Cypress.env('EXTRACTED_VAL') || '123456';",
                ]
            )
            return

        if action_type == ActionType.WAIT:
            lines.append("        cy.wait(2000);")
            return

        if action_type in (ActionType.ASSERT_VISIBLE, ActionType.ASSERT, ActionType.VERIFY):
            self._assert_visible_action(lines, action)
            return

        lines.append(
            f"        // Step action: {action_type.value} on {action.business_target or 'system'}"
        )

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
                f"        cy.visit({_js_string(target)});"
            )

        else:

            lines.append(
                f"        // Navigation target: "
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
                "        const username = "
                "Cypress.env('TEST_USERNAME');",
                "        const password = "
                "Cypress.env('TEST_PASSWORD');",
                "",
                "        if (!username || !password) {",
                "            throw new Error(",
                "                'TEST_USERNAME and "
                "TEST_PASSWORD must be configured.'",
                "            );",
                "        }",
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

        expression = self._cypress_locator(
            locator
        )

        lines.append(
            f"        {expression}.click();"
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

        expression = self._cypress_locator(
            locator
        )

        value = self._value_expression(
            action
        )

        lines.append(
            f"        {expression}.clear().type({value});"
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

        expression = self._cypress_locator(
            locator
        )

        value = self._value_expression(
            action
        )

        lines.append(
            f"        {expression}.selectFile({value});"
        )

    # ========================================================
    # ASSERT VISIBLE
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
                self._cypress_locator(
                    resolution.locator
                )
            )

            lines.append(
                f"        {expression}.should('be.visible');"
            )

            return

        lines.extend(
            [
                "        throw new Error(",
                f"            {_js_string(action.expected_result or action.business_target or 'Required UI evidence was not resolved.')}",
                "        );",
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
            "        // Assertion: "
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
                self._cypress_locator(
                    resolution.locator
                )
            )

            lines.append(
                f"        {expression}.should('be.visible');"
            )

            return

        lines.extend(
            [
                "        throw new Error(",
                "            'Required Cypress assertion "
                "locator was not resolved.'",
                "        );",
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
                "Cannot generate Cypress JavaScript "
                f"for step {action.step_number}: "
                "no safe locator was resolved for "
                f"'{action.business_target}'."
            )

        return resolution.locator

    # ========================================================
    # CYPRESS LOCATOR CONVERSION
    # ========================================================

    @staticmethod
    def _cypress_locator(
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
                "cy.get("
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
                "cy.get("
                f"{_js_string(selector)}"
                ")"
            )

        # ----------------------------------------------------
        # CSS
        # ----------------------------------------------------

        if strategy == "css":

            return (
                "cy.get("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # XPATH
        # ----------------------------------------------------

        if strategy == "xpath":

            return (
                "cy.xpath("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # PLACEHOLDER
        # ----------------------------------------------------

        if strategy == "placeholder":

            selector = (
                f'[placeholder="{_css_escape(value)}"]'
            )

            return (
                "cy.get("
                f"{_js_string(selector)}"
                ")"
            )

        # ----------------------------------------------------
        # LABEL
        # ----------------------------------------------------

        if strategy in (
            "label",
            "aria_label",
            "accessibility_id",
        ):

            return (
                "cy.contains("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # TEST ID
        # ----------------------------------------------------

        if strategy == "test_id":

            return (
                "cy.get("
                f"{_js_string('[data-testid="' + _css_escape(value) + '"]')}"
                ")"
            )

        # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------

        if strategy == "role":

            # Cypress does not provide getByRole natively
            # unless Cypress Testing Library is installed.
            #
            # Use an ARIA role selector so the generated
            # code remains dependency-light.

            selector = (
                f'[role="{_css_escape(value)}"]'
            )

            return (
                "cy.get("
                f"{_js_string(selector)}"
                ")"
            )

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        if strategy == "text":

            return (
                "cy.contains("
                f"{_js_string(value)}"
                ")"
            )

        raise ValueError(
            "Unsupported Cypress JavaScript "
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

            env_name = re.sub(
                r"[^A-Za-z0-9_]",
                "_",
                action.value_reference,
            ).upper()

            return (
                "Cypress.env("
                f"{_js_string(env_name)}"
                ")"
            )

        return (
            "Cypress.env('TEST_DATA_VALUE')"
        )


# ============================================================
# HELPERS
# ============================================================


def _js_string(
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


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def generate_cypress_javascript(
    plan: ResolvedAutomationPlan,
) -> str:

    generator = (
        CypressJavaScriptGenerator()
    )

    return generator.generate(plan)