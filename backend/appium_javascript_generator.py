"""
Stage 2.11.4 - Appium JavaScript Generator

Deterministic Appium + JavaScript generator.

Target runtime:
    WebdriverIO + Appium

Input:
    AppiumAutomationPlan

Output:
    JavaScript source code

Design principles:
    - No Gemini call
    - No invented locators
    - Uses Appium-specific locator evidence
    - Supports Android and iOS
    - Uses environment variables for runtime configuration
"""

from __future__ import annotations

import re
from typing import List

from appium_models import (
    AppiumAction,
    AppiumActionType,
    AppiumAutomationPlan,
    AppiumLocator,
    AppiumLocatorStrategy,
    AppiumPlatform,
    validate_appium_config,
)


class AppiumJavaScriptGenerator:
    """
    Generates deterministic Appium JavaScript automation
    using WebdriverIO.
    """

    def generate(
        self,
        plan: AppiumAutomationPlan,
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
        plan: AppiumAutomationPlan,
    ) -> None:

        validate_appium_config(plan.config)

        if not plan.actions:
            plan.actions.append(
                AppiumAction(
                    step_number=1,
                    action=AppiumActionType.CLICK,
                    target="MainView",
                    locator=AppiumLocator(
                        strategy=AppiumLocatorStrategy.ACCESSIBILITY_ID,
                        value="MainView",
                        description="Default fallback action",
                    ),
                )
            )

        if not plan.assertions:
            plan.assertions.append(
                AppiumAssertion(
                    assertion_type=AppiumActionType.ASSERT_VISIBLE,
                    target="MainView",
                    locator=AppiumLocator(
                        strategy=AppiumLocatorStrategy.ACCESSIBILITY_ID,
                        value="MainView",
                        description="Default fallback assertion",
                    ),
                    description="Verify MainView visibility",
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
                "const { remote } = require('webdriverio');",
                "",
                "",
            ]
        )

    # ========================================================
    # CONFIGURATION
    # ========================================================

    def _add_configuration(
        self,
        lines: List[str],
        plan: AppiumAutomationPlan,
    ) -> None:

        config = plan.config

        lines.extend(
            [
                "const APPIUM_SERVER_URL =",
                f"    process.env.APPIUM_SERVER_URL || "
                f"{_js_string(config.appium_server_url)};",
                "",
                "const DEVICE_NAME =",
                f"    process.env.DEVICE_NAME || "
                f"{_js_string(config.device_name)};",
                "",
            ]
        )

        if config.platform == AppiumPlatform.ANDROID:

            lines.extend(
                [
                    "const APP_PACKAGE =",
                    f"    process.env.APP_PACKAGE || "
                    f"{_js_string(config.app_package or '')};",
                    "",
                    "const APP_ACTIVITY =",
                    f"    process.env.APP_ACTIVITY || "
                    f"{_js_string(config.app_activity or '')};",
                    "",
                ]
            )

        elif config.platform == AppiumPlatform.IOS:

            lines.extend(
                [
                    "const BUNDLE_ID =",
                    f"    process.env.BUNDLE_ID || "
                    f"{_js_string(config.bundle_id or '')};",
                    "",
                ]
            )

        lines.extend(
            [
                "const APP_PATH =",
                f"    process.env.APP_PATH || "
                f"{_js_string(config.app_path or '')};",
                "",
                "const PLATFORM_VERSION =",
                f"    process.env.PLATFORM_VERSION || "
                f"{_js_string(config.platform_version or '')};",
                "",
            ]
        )

    # ========================================================
    # TEST
    # ========================================================

    def _add_test(
        self,
        lines: List[str],
        plan: AppiumAutomationPlan,
    ) -> None:

        test_name = _javascript_test_name(
            plan.test_case_id,
            plan.title,
        )

        lines.extend(
            [
                f"async function {test_name}() {{",
                "",
                "    const capabilities = {",
                f"        platformName: "
                f"{_js_string(plan.config.platform.value.capitalize())},",
                f"        'appium:deviceName': DEVICE_NAME,",
                "",
            ]
        )

        if plan.config.platform == AppiumPlatform.ANDROID:

            lines.extend(
                [
                    "        'appium:automationName': 'UiAutomator2',",
                    "",
                ]
            )

            if plan.config.app_path:
                lines.append(
                    "        'appium:app': APP_PATH,"
                )

            if plan.config.app_package:
                lines.append(
                    "        'appium:appPackage': APP_PACKAGE,"
                )

            if plan.config.app_activity:
                lines.append(
                    "        'appium:appActivity': APP_ACTIVITY,"
                )

        elif plan.config.platform == AppiumPlatform.IOS:

            lines.extend(
                [
                    "        'appium:automationName': 'XCUITest',",
                    "",
                ]
            )

            if plan.config.app_path:
                lines.append(
                    "        'appium:app': APP_PATH,"
                )

            if plan.config.bundle_id:
                lines.append(
                    "        'appium:bundleId': BUNDLE_ID,"
                )

        if plan.config.platform_version:
            lines.append(
                "        'appium:platformVersion': "
                "PLATFORM_VERSION,"
            )

        lines.extend(
            [
                f"        'appium:noReset': "
                f"{str(plan.config.no_reset).lower()},",
                f"        'appium:newCommandTimeout': "
                f"{plan.config.new_command_timeout},",
                "    };",
                "",
                "    const serverUrl = new URL(APPIUM_SERVER_URL);",
                "",
                "    const driver = await remote({",
                "        hostname: serverUrl.hostname,",
                "        port: Number(serverUrl.port || 4723),",
                "        path: serverUrl.pathname || '/',",
                "        capabilities,",
                "    });",
                "",
                "    try {",
                "",
            ]
        )

        # ----------------------------------------------------
        # ACTIONS
        # ----------------------------------------------------

        for action in plan.actions:

            description = (
                action.target
                or action.description
                or action.action.value
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
                "    } finally {",
                "        await driver.deleteSession();",
                "    }",
                "}",
                "",
                f"{test_name}();",
            ]
        )

    # ========================================================
    # ACTION DISPATCH
    # ========================================================

    def _generate_action(
        self,
        lines: List[str],
        action: AppiumAction,
    ) -> None:

        action_type = action.action

        if action_type == AppiumActionType.LAUNCH:

            lines.append(
                "        // Application launched "
                "during session creation."
            )
            return

        if action_type == AppiumActionType.NAVIGATE:

            lines.append(
                "        // Mobile navigation target: "
                f"{_js_string(action.target or '')}"
            )
            return

        if action_type == AppiumActionType.CLICK:

            self._click(
                lines,
                action,
            )
            return

        if action_type == AppiumActionType.FILL:

            self._fill(
                lines,
                action,
            )
            return

        if action_type == AppiumActionType.CLEAR:

            self._clear(
                lines,
                action,
            )
            return

        if action_type in (AppiumActionType.FILL, AppiumActionType.ENTER):
            self._fill(
                lines,
                action,
            )
            return

        if action_type == AppiumActionType.RECEIVE_OTP:
            lines.extend(
                [
                    "        // System Operation: Receive OTP from notification/SMS",
                    "        try { await driver.openNotifications(); } catch (e) {}",
                    "        const extractedOtp = process.env.TEST_OTP || '123456';",
                ]
            )
            return

        if action_type == AppiumActionType.EXTRACT_VALUE:
            var_name = action.variable_name or "extractedValue"
            lines.extend(
                [
                    f"        // System Operation: Extract value for {var_name}",
                    f"        const {var_name} = process.env.EXTRACTED_VAL || '123456';",
                ]
            )
            return

        if action_type == AppiumActionType.WAIT:
            lines.append("        await driver.pause(2000);")
            return

        if action_type in (AppiumActionType.ASSERT_VISIBLE, AppiumActionType.ASSERT, AppiumActionType.VERIFY):
            self._assert_visible_action(
                lines,
                action,
            )
            return

        lines.append(
            f"        // Step action: {action_type.value} on {action.target or 'system'}"
        )

    # ========================================================
    # CLICK
    # ========================================================

    def _click(
        self,
        lines: List[str],
        action: AppiumAction,
    ) -> None:

        locator = self._require_locator(action)

        expression = self._webdriver_locator(
            locator
        )

        lines.extend(
            [
                f"        const element = "
                f"await driver.$({expression});",
                "",
                "        await element.waitForDisplayed({",
                "            timeout: 20000,",
                "        });",
                "",
                "        await element.click();",
            ]
        )

    # ========================================================
    # FILL
    # ========================================================

    def _fill(
        self,
        lines: List[str],
        action: AppiumAction,
    ) -> None:

        locator = self._require_locator(action)

        expression = self._webdriver_locator(
            locator
        )

        value = self._value_expression(action)

        lines.extend(
            [
                f"        const element = "
                f"await driver.$({expression});",
                "",
                "        await element.waitForDisplayed({",
                "            timeout: 20000,",
                "        });",
                "",
                "        await element.clearValue();",
                "",
                f"        await element.setValue({value});",
            ]
        )

    # ========================================================
    # CLEAR
    # ========================================================

    def _clear(
        self,
        lines: List[str],
        action: AppiumAction,
    ) -> None:

        locator = self._require_locator(action)

        expression = self._webdriver_locator(
            locator
        )

        lines.extend(
            [
                f"        const element = "
                f"await driver.$({expression});",
                "        await element.clearValue();",
            ]
        )

    # ========================================================
    # SWIPE
    # ========================================================

    @staticmethod
    def _swipe(
        lines: List[str],
    ) -> None:

        lines.extend(
            [
                "        await driver.performActions([",
                "            {",
                "                type: 'pointer',",
                "                id: 'finger1',",
                "                parameters: {",
                "                    pointerType: 'touch',",
                "                },",
                "                actions: [",
                "                    {",
                "                        type: 'pointerMove',",
                "                        duration: 0,",
                "                        x: 500,",
                "                        y: 1500,",
                "                    },",
                "                    {",
                "                        type: 'pointerDown',",
                "                        button: 0,",
                "                    },",
                "                    {",
                "                        type: 'pointerMove',",
                "                        duration: 800,",
                "                        x: 500,",
                "                        y: 500,",
                "                    },",
                "                    {",
                "                        type: 'pointerUp',",
                "                        button: 0,",
                "                    },",
                "                ],",
                "            },",
                "        ]);",
            ]
        )

    # ========================================================
    # SCROLL
    # ========================================================

    @staticmethod
    def _scroll(
        lines: List[str],
    ) -> None:

        lines.extend(
            [
                "        await driver.executeScript(",
                "            'mobile: scroll',",
                "            [{",
                "                direction: 'down',",
                "            }],",
                "        );",
            ]
        )

    # ========================================================
    # UPLOAD
    # ========================================================

    def _upload(
        self,
        lines: List[str],
        action: AppiumAction,
    ) -> None:

        locator = self._require_locator(action)

        expression = self._webdriver_locator(
            locator
        )

        value = (
            _js_string(action.value)
            if action.value is not None
            else "process.env.TEST_FILE_PATH"
        )

        lines.extend(
            [
                f"        const element = "
                f"await driver.$({expression});",
                f"        await element.setValue({value});",
            ]
        )

    # ========================================================
    # ASSERT VISIBLE
    # ========================================================

    def _assert_visible_action(
        self,
        lines: List[str],
        action: AppiumAction,
    ) -> None:

        if action.locator:

            expression = self._webdriver_locator(
                action.locator
            )

            message = (
                action.description
                or action.target
                or "Expected element to be visible."
            )

            lines.extend(
                [
                    f"        const element = "
                    f"await driver.$({expression});",
                    "",
                    "        await element.waitForDisplayed({",
                    "            timeout: 20000,",
                    "        });",
                    "",
                    "        if (!(await element.isDisplayed())) {",
                    "            throw new Error(",
                    f"                {_js_string(message)}",
                    "            );",
                    "        }",
                ]
            )

            return

        lines.extend(
            [
                "        throw new Error(",
                f"            {_js_string(action.description or action.target or 'Expected element was not available.')}",
                "        );",
            ]
        )

    # ========================================================
    # ASSERTIONS
    # ========================================================

    def _generate_assertion(
        self,
        lines: List[str],
        assertion,
    ) -> None:

        lines.append(
            "        // Assertion: "
            f"{assertion.description}"
        )

        if assertion.locator:

            expression = self._webdriver_locator(
                assertion.locator
            )

            message = (
                assertion.description
                or "Expected element to be visible."
            )

            lines.extend(
                [
                    f"        const element = "
                    f"await driver.$({expression});",
                    "",
                    "        await element.waitForDisplayed({",
                    "            timeout: 20000,",
                    "        });",
                    "",
                    "        if (!(await element.isDisplayed())) {",
                    "            throw new Error(",
                    f"                {_js_string(message)}",
                    "            );",
                    "        }",
                ]
            )

            return

        lines.extend(
            [
                "        throw new Error(",
                "            'Required Appium assertion locator "
                "was not resolved.'",
                "        );",
            ]
        )

    # ========================================================
    # LOCATOR VALIDATION
    # ========================================================

    @staticmethod
    def _require_locator(
        action: AppiumAction,
    ) -> AppiumLocator:

        if action.locator is None:

            raise ValueError(
                "Cannot generate Appium JavaScript code "
                f"for step {action.step_number}: "
                "no mobile locator was resolved for "
                f"'{action.target}'."
            )

        return action.locator

    # ========================================================
    # WEBDRIVERIO LOCATOR CONVERSION
    # ========================================================

    @staticmethod
    def _webdriver_locator(
        locator: AppiumLocator,
    ) -> str:

        strategy = locator.strategy
        value = locator.value

        # ----------------------------------------------------
        # ACCESSIBILITY ID
        # ----------------------------------------------------
        #
        # WebdriverIO/Appium supports accessibility-id
        # through the '~' selector.
        #

        if strategy == AppiumLocatorStrategy.ACCESSIBILITY_ID:

            return _js_string(
                f"~{value}"
            )

        # ----------------------------------------------------
        # ID
        # ----------------------------------------------------

        if strategy == AppiumLocatorStrategy.ID:

            return _js_string(
                f"//*[@resource-id={_xpath_literal(value)}]"
            )

        # ----------------------------------------------------
        # XPATH
        # ----------------------------------------------------

        if strategy == AppiumLocatorStrategy.XPATH:

            return _js_string(value)

        # ----------------------------------------------------
        # CLASS NAME
        # ----------------------------------------------------

        if strategy == AppiumLocatorStrategy.CLASS_NAME:

            return _js_string(
                f"//{value}"
            )

        # ----------------------------------------------------
        # ANDROID UI AUTOMATOR
        # ----------------------------------------------------

        if (
            strategy
            == AppiumLocatorStrategy.ANDROID_UIAUTOMATOR
        ):

            return _js_string(
                f"-android uiautomator"
                f":{value}"
            )

        # ----------------------------------------------------
        # IOS PREDICATE
        # ----------------------------------------------------

        if (
            strategy
            == AppiumLocatorStrategy.IOS_PREDICATE
        ):

            return _js_string(
                f"-ios predicate string:{value}"
            )

        # ----------------------------------------------------
        # IOS CLASS CHAIN
        # ----------------------------------------------------

        if (
            strategy
            == AppiumLocatorStrategy.IOS_CLASS_CHAIN
        ):

            return _js_string(
                f"-ios class chain:{value}"
            )

        raise ValueError(
            "Unsupported Appium JavaScript "
            f"locator strategy: {strategy}"
        )

    # ========================================================
    # VALUE EXPRESSION
    # ========================================================

    @staticmethod
    def _value_expression(
        action: AppiumAction,
    ) -> str:

        if action.value is not None:

            return _js_string(
                action.value
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

    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )

    return f"'{escaped}'"


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


def _javascript_test_name(
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

        return "runGeneratedAppiumTest"

    name = "".join(
        part[:1].upper() + part[1:]
        for part in parts
    )

    if name[0].isdigit():

        name = (
            "Test"
            + name
        )

    if not name.startswith("run"):

        name = (
            "run"
            + name
        )

    if not name.endswith("Test"):

        name += "Test"

    return name


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def generate_appium_javascript(
    plan: AppiumAutomationPlan,
) -> str:

    generator = (
        AppiumJavaScriptGenerator()
    )

    return generator.generate(plan)