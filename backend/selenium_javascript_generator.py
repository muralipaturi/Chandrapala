"""
Stage 2.7.3 - Selenium JavaScript Generator

Deterministic Selenium + JavaScript code generator.

Input:
    ResolvedAutomationPlan

Output:
    Selenium JavaScript source code

Design:
    - No Gemini call
    - No invented locators
    - Uses actual resolved UI evidence
    - Framework-independent planning remains unchanged
    - Uses selenium-webdriver
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
# GENERATOR
# ============================================================


class SeleniumJavaScriptGenerator:
    """
    Generates Selenium JavaScript automation code.
    """

    def generate(
        self,
        plan: ResolvedAutomationPlan,
    ) -> str:

        self._validate_plan(plan)

        lines: List[str] = []

        self._add_header(lines)
        self._add_setup(lines, plan)
        self._add_test(lines, plan)
        self._add_teardown(lines)

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
                "Cannot generate Selenium JavaScript code: "
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
                "const {",
                "    Builder,",
                "    By,",
                "    until",
                "} = require('selenium-webdriver');",
                "",
                "const assert = require('assert');",
                "",
            ]
        )

    # ========================================================
    # SETUP
    # ========================================================

    @staticmethod
    def _add_setup(
        lines: List[str],
        plan: ResolvedAutomationPlan,
    ) -> None:

        url = _js_string(
            plan.application_url
        )

        lines.extend(
            [
                "describe('Generated Selenium Test', function () {",
                "",
                "    let driver;",
                "",
                "    beforeEach(async function () {",
                "        driver = await new Builder()",
                "            .forBrowser('chrome')",
                "            .build();",
                "",
                "        await driver.manage()",
                "            .window()",
                "            .maximize();",
                "",
                f"        await driver.get({url});",
                "    });",
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

        lines.extend(
            [
                "    it(",
                f"        {_js_string(plan.title)},",
                "        async function () {",
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
                f"            // Step "
                f"{action.step_number}: "
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
            "            // Business outcome assertions"
        )

        for assertion in plan.assertions:

            self._generate_assertion(
                lines,
                assertion,
            )

            lines.append("")

        lines.extend(
            [
                "        }",
                "    );",
                "",
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

        if action_type == ActionType.UPLOAD:
            self._upload(
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
                    "            // System Operation: Receive OTP from notification/SMS source",
                    "            const extractedOtp = process.env.TEST_OTP || '123456';",
                ]
            )
            return

        if action_type == ActionType.EXTRACT_VALUE:
            var_name = getattr(action, "variable_name", None) or "extractedVal"
            lines.extend(
                [
                    f"            // System Operation: Extract value for {var_name}",
                    f"            const {var_name} = process.env.EXTRACTED_VAL || '123456';",
                ]
            )
            return

        if action_type == ActionType.WAIT:
            lines.append("            await new Promise(r => setTimeout(r, 2000));")
            return

        if action_type in (ActionType.ASSERT_VISIBLE, ActionType.ASSERT, ActionType.VERIFY):
            self._assert_visible_action(
                lines,
                action,
            )
            return

        lines.append(
            f"            // Step action: {action_type.value} on {action.business_target or 'system'}"
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
                "            await driver.get("
                f"{_js_string(target)}"
                ");"
            )

        else:

            lines.append(
                "            // Navigate to: "
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
                "            const username = "
                "process.env.TEST_USERNAME;",
                "",
                "            const password = "
                "process.env.TEST_PASSWORD;",
                "",
                "            if (!username || !password) {",
                "                throw new Error(",
                "                    'TEST_USERNAME and "
                "TEST_PASSWORD must be configured.'",
                "                );",
                "            }",
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
                "            const element = "
                "await driver.wait(",
                f"                until.elementLocated("
                f"{expression}),",
                "                15000",
                "            );",
                "",
                "            await driver.wait(",
                "                until.elementIsVisible(element),",
                "                15000",
                "            );",
                "",
                "            await element.click();",
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
                "            const element = "
                "await driver.wait(",
                f"                until.elementLocated("
                f"{expression}),",
                "                15000",
                "            );",
                "",
                "            await driver.wait(",
                "                until.elementIsVisible(element),",
                "                15000",
                "            );",
                "",
                "            await element.clear();",
                "",
                f"            await element.sendKeys({value});",
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
                "            const fileInput = "
                "await driver.wait(",
                f"                until.elementLocated("
                f"{expression}),",
                "                15000",
                "            );",
                "",
                f"            await fileInput.sendKeys({value});",
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

            lines.extend(
                [
                    "            const element = "
                    "await driver.wait(",
                    f"                until.elementLocated("
                    f"{expression}),",
                    "                15000",
                    "            );",
                    "",
                    "            assert.strictEqual(",
                    "                await element.isDisplayed(),",
                    "                true",
                    "            );",
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
                "            throw new Error(",
                f"                {_js_string(message)}",
                "            );",
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
            "            // Assertion: "
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

            lines.extend(
                [
                    "            const assertionElement = "
                    "await driver.wait(",
                    f"                until.elementLocated("
                    f"{expression}),",
                    "                15000",
                    "            );",
                    "",
                    "            assert.strictEqual(",
                    "                await assertionElement.isDisplayed(),",
                    "                true",
                    "            );",
                ]
            )

            return

        lines.extend(
            [
                "            throw new Error(",
                "                'Required assertion locator "
                "was not resolved from application evidence.'",
                "            );",
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
                "Cannot generate Selenium JavaScript "
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

        strategy = (
            locator.strategy.value
        )

        value = locator.value

        # ----------------------------------------------------
        # ID
        # ----------------------------------------------------

        if strategy == "id":

            return (
                "By.id("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if strategy == "name":

            return (
                "By.name("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # CSS
        # ----------------------------------------------------

        if strategy == "css":

            return (
                "By.css("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # XPATH
        # ----------------------------------------------------

        if strategy == "xpath":

            return (
                "By.xpath("
                f"{_js_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # PLACEHOLDER
        # ----------------------------------------------------

        if strategy == "placeholder":

            selector = _css_attribute_selector(
                "placeholder",
                value,
            )

            return (
                "By.css("
                f"{_js_string(selector)}"
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

            selector = _css_attribute_selector(
                "aria-label",
                value,
            )

            return (
                "By.css("
                f"{_js_string(selector)}"
                ")"
            )

        # ----------------------------------------------------
        # TEST ID
        # ----------------------------------------------------

        if strategy == "test_id":

            selector = _css_attribute_selector(
                "data-testid",
                value,
            )

            return (
                "By.css("
                f"{_js_string(selector)}"
                ")"
            )

        # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------

        if strategy == "role":

            selector = _css_attribute_selector(
                "role",
                value,
            )

            return (
                "By.css("
                f"{_js_string(selector)}"
                ")"
            )

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        if strategy == "text":

            xpath = (
                "//*[normalize-space()="
                f"{_js_string(value)}]"
            )

            return (
                "By.xpath("
                f"{_js_string(xpath)}"
                ")"
            )

        raise ValueError(
            "Unsupported Selenium JavaScript "
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
                f"process.env."
                f"{env_name}"
            )

        return (
            "process.env.TEST_DATA_VALUE"
        )

    # ========================================================
    # TEARDOWN
    # ========================================================

    @staticmethod
    def _add_teardown(
        lines: List[str],
    ) -> None:

        lines.extend(
            [
                "    afterEach(async function () {",
                "        if (driver) {",
                "            await driver.quit();",
                "        }",
                "    });",
                "",
                "});",
            ]
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
        .replace("`", "\\`")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )

    return f"`{escaped}`"


def _css_attribute_selector(
    attribute: str,
    value: str,
) -> str:

    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace("\"", "\\\"")
    )

    return (
        f"[{attribute}=\"{escaped}\"]"
    )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def generate_selenium_javascript(
    plan: ResolvedAutomationPlan,
) -> str:
    """
    Generate Selenium JavaScript source code.
    """

    generator = (
        SeleniumJavaScriptGenerator()
    )

    return generator.generate(
        plan
    )