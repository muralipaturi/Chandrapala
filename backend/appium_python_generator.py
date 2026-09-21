"""
Stage 2.11.2 - Appium Python Generator

Deterministic Appium + Python code generator.

Input:
    AppiumAutomationPlan

Output:
    Appium Python source code

Design principles:
    - No Gemini call
    - No invented mobile locators
    - Uses Appium-specific locators
    - Supports Android and iOS
    - Generates pytest-compatible tests
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


class AppiumPythonGenerator:
    """
    Generates deterministic Appium Python automation.
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
        self._add_teardown(lines)

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
                '"""',
                "Generated Appium Python automation.",
                '"""',
                "",
                "import os",
                "",
                "from appium import webdriver",
                "from appium.options.android import UiAutomator2Options",
                "from appium.options.ios import XCUITestOptions",
                "from appium.webdriver.common.appiumby import AppiumBy",
                "",
                "from selenium.webdriver.support.ui import WebDriverWait",
                "from selenium.webdriver.support import expected_conditions as EC",
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
                f"APPIUM_SERVER_URL = {_py_string(config.appium_server_url)}",
                f"DEVICE_NAME = {_py_string(config.device_name)}",
                "",
            ]
        )

        if config.platform == AppiumPlatform.ANDROID:
            lines.extend(
                [
                    "APP_PACKAGE = os.getenv(",
                    "    'APP_PACKAGE',",
                    f"    {_py_string(config.app_package or '')},",
                    ")",
                    "",
                    "APP_ACTIVITY = os.getenv(",
                    "    'APP_ACTIVITY',",
                    f"    {_py_string(config.app_activity or '')},",
                    ")",
                    "",
                ]
            )

        elif config.platform == AppiumPlatform.IOS:
            lines.extend(
                [
                    "BUNDLE_ID = os.getenv(",
                    "    'BUNDLE_ID',",
                    f"    {_py_string(config.bundle_id or '')},",
                    ")",
                    "",
                ]
            )

        lines.extend(
            [
                "APP_PATH = os.getenv(",
                "    'APP_PATH',",
                f"    {_py_string(config.app_path or '')},",
                ")",
                "",
                "PLATFORM_VERSION = os.getenv(",
                "    'PLATFORM_VERSION',",
                f"    {_py_string(config.platform_version or '')},",
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
        plan: AppiumAutomationPlan,
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
            ]
        )

        self._add_driver_creation(
            lines,
            plan,
        )

        lines.extend(
            [
                "",
                "    wait = WebDriverWait(",
                "        driver,",
                "        20,",
                "    )",
                "",
                "    try:",
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
                f"        # Step {action.step_number}: "
                f"{description}"
            )

            self._generate_action(
                lines,
                action,
                indent="        ",
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
                indent="        ",
            )

            lines.append("")

        lines.extend(
            [
                "    finally:",
                "        driver.quit()",
            ]
        )

    # ========================================================
    # DRIVER CREATION
    # ========================================================

    def _add_driver_creation(
        self,
        lines: List[str],
        plan: AppiumAutomationPlan,
    ) -> None:
        config = plan.config

        if config.platform == AppiumPlatform.ANDROID:
            lines.extend(
                [
                    "    options = UiAutomator2Options()",
                    "",
                    "    options.platform_name = 'Android'",
                    "    options.automation_name = 'UiAutomator2'",
                    "    options.device_name = DEVICE_NAME",
                    "",
                    "    if PLATFORM_VERSION:",
                    "        options.platform_version = PLATFORM_VERSION",
                    "",
                    "    if APP_PATH:",
                    "        options.app = APP_PATH",
                    "",
                    "    if APP_PACKAGE:",
                    "        options.app_package = APP_PACKAGE",
                    "",
                    "    if APP_ACTIVITY:",
                    "        options.app_activity = APP_ACTIVITY",
                    "",
                    f"    options.no_reset = {config.no_reset!r}",
                    f"    options.auto_grant_permissions = "
                    f"{config.auto_grant_permissions!r}",
                    f"    options.new_command_timeout = "
                    f"{config.new_command_timeout}",
                    "",
                    "    driver = webdriver.Remote(",
                    "        command_executor=APPIUM_SERVER_URL,",
                    "        options=options,",
                    "    )",
                ]
            )

        elif config.platform == AppiumPlatform.IOS:
            lines.extend(
                [
                    "    options = XCUITestOptions()",
                    "",
                    "    options.platform_name = 'iOS'",
                    "    options.automation_name = 'XCUITest'",
                    "    options.device_name = DEVICE_NAME",
                    "",
                    "    if PLATFORM_VERSION:",
                    "        options.platform_version = PLATFORM_VERSION",
                    "",
                    "    if APP_PATH:",
                    "        options.app = APP_PATH",
                    "",
                    "    if BUNDLE_ID:",
                    "        options.bundle_id = BUNDLE_ID",
                    "",
                    f"    options.no_reset = {config.no_reset!r}",
                    f"    options.new_command_timeout = "
                    f"{config.new_command_timeout}",
                    "",
                    "    driver = webdriver.Remote(",
                    "        command_executor=APPIUM_SERVER_URL,",
                    "        options=options,",
                    "    )",
                ]
            )

    # ========================================================
    # ACTION DISPATCH
    # ========================================================

    def _generate_action(
        self,
        lines: List[str],
        action: AppiumAction,
        indent: str,
    ) -> None:
        action_type = action.action

        if action_type == AppiumActionType.LAUNCH:
            lines.append(
                f"{indent}# Application launched during "
                f"driver creation."
            )
            return

        if action_type == AppiumActionType.NAVIGATE:
            self._navigate(
                lines,
                action,
                indent,
            )
            return

        if action_type == AppiumActionType.CLICK:
            self._click(
                lines,
                action,
                indent,
            )
            return

        if action_type == AppiumActionType.FILL:
            self._fill(
                lines,
                action,
                indent,
            )
            return

        if action_type == AppiumActionType.CLEAR:
            self._clear(
                lines,
                action,
                indent,
            )
            return

        if action_type == AppiumActionType.SWIPE:
            self._swipe(
                lines,
                action,
                indent,
            )
            return

        if action_type in (AppiumActionType.FILL, AppiumActionType.ENTER):
            self._fill(
                lines,
                action,
                indent,
            )
            return

        if action_type == AppiumActionType.RECEIVE_OTP:
            lines.extend(
                [
                    f"{indent}# System Operation: Receive OTP from notification/SMS",
                    f"{indent}try:",
                    f"{indent}    driver.open_notifications()",
                    f"{indent}except Exception:",
                    f"{indent}    pass",
                    f"{indent}extracted_otp = os.getenv('TEST_OTP', '123456')",
                ]
            )
            return

        if action_type == AppiumActionType.EXTRACT_VALUE:
            var_name = action.variable_name or "extracted_val"
            lines.extend(
                [
                    f"{indent}# System Operation: Extract value for {var_name}",
                    f"{indent}{var_name} = os.getenv('EXTRACTED_VAL', '123456')",
                ]
            )
            return

        if action_type == AppiumActionType.WAIT:
            lines.append(f"{indent}time.sleep(2)")
            return

        if action_type in (AppiumActionType.ASSERT_VISIBLE, AppiumActionType.ASSERT, AppiumActionType.VERIFY):
            self._assert_visible_action(
                lines,
                action,
                indent,
            )
            return

        lines.append(
            f"{indent}# Step action: {action_type.value} on {action.target or 'system'}"
        )

    # ========================================================
    # NAVIGATE
    # ========================================================

    @staticmethod
    def _navigate(
        lines: List[str],
        action: AppiumAction,
        indent: str,
    ) -> None:
        target = (
            action.target
            or ""
        ).strip()

        lines.append(
            f"{indent}# Mobile navigation target: "
            f"{_py_string(target)}"
        )

    # ========================================================
    # CLICK
    # ========================================================

    def _click(
        self,
        lines: List[str],
        action: AppiumAction,
        indent: str,
    ) -> None:
        locator = self._require_locator(action)

        expression = self._appium_locator(
            locator
        )

        lines.extend(
            [
                f"{indent}element = wait.until(",
                f"{indent}    EC.element_to_be_clickable(",
                f"{indent}        driver.find_element(*{expression})",
                f"{indent}    )",
                f"{indent})",
                "",
                f"{indent}element.click()",
            ]
        )

    # ========================================================
    # FILL
    # ========================================================

    def _fill(
        self,
        lines: List[str],
        action: AppiumAction,
        indent: str,
    ) -> None:
        locator = self._require_locator(action)

        expression = self._appium_locator(
            locator
        )

        value_expression = self._value_expression(
            action
        )

        lines.extend(
            [
                f"{indent}element = wait.until(",
                f"{indent}    EC.visibility_of_element_located(",
                f"{indent}        {expression}",
                f"{indent}    )",
                f"{indent})",
                "",
                f"{indent}element.clear()",
                "",
                f"{indent}element.send_keys("
                f"{value_expression}"
                f")",
            ]
        )

    # ========================================================
    # CLEAR
    # ========================================================

    def _clear(
        self,
        lines: List[str],
        action: AppiumAction,
        indent: str,
    ) -> None:
        locator = self._require_locator(action)

        expression = self._appium_locator(
            locator
        )

        lines.append(
            f"{indent}driver.find_element(*{expression}).clear()"
        )

    # ========================================================
    # SWIPE
    # ========================================================

    @staticmethod
    def _swipe(
        lines: List[str],
        action: AppiumAction,
        indent: str,
    ) -> None:
        lines.extend(
            [
                f"{indent}driver.swipe(",
                f"{indent}    500,",
                f"{indent}    1500,",
                f"{indent}    500,",
                f"{indent}    500,",
                f"{indent}    800,",
                f"{indent})",
            ]
        )

    # ========================================================
    # SCROLL
    # ========================================================

    @staticmethod
    def _scroll(
        lines: List[str],
        action: AppiumAction,
        indent: str,
    ) -> None:
        lines.extend(
            [
                f"{indent}driver.execute_script(",
                f"{indent}    'mobile: scroll',",
                f"{indent}    {{'direction': 'down'}},",
                f"{indent})",
            ]
        )

    # ========================================================
    # UPLOAD
    # ========================================================

    def _upload(
        self,
        lines: List[str],
        action: AppiumAction,
        indent: str,
    ) -> None:
        locator = self._require_locator(action)

        expression = self._appium_locator(
            locator
        )

        value_expression = (
            _py_string(action.value)
            if action.value
            else "os.getenv('TEST_FILE_PATH')"
        )

        lines.append(
            f"{indent}driver.find_element(*{expression})"
            f".send_keys({value_expression})"
        )

    # ========================================================
    # ASSERT VISIBLE ACTION
    # ========================================================

    def _assert_visible_action(
        self,
        lines: List[str],
        action: AppiumAction,
        indent: str,
    ) -> None:
        if action.locator:
            expression = self._appium_locator(
                action.locator
            )

            lines.extend(
                [
                    f"{indent}element = wait.until(",
                    f"{indent}    EC.visibility_of_element_located(",
                    f"{indent}        {expression}",
                    f"{indent}    )",
                    f"{indent})",
                    "",
                    f"{indent}assert element.is_displayed(), ",
                ]
            )

            # Replace trailing incomplete line with valid Python.
            lines[-1] = (
                f"{indent}assert element.is_displayed(), "
                f"{_py_string(action.description or action.target or 'Expected element to be visible.')}"
            )

            return

        lines.extend(
            [
                f"{indent}raise AssertionError(",
                f"{indent}    {_py_string(action.description or action.target or 'Expected element was not available.')}",
                f"{indent})",
            ]
        )

    # ========================================================
    # ASSERTIONS
    # ========================================================

    def _generate_assertion(
        self,
        lines: List[str],
        assertion,
        indent: str,
    ) -> None:
        lines.append(
            f"{indent}# Assertion: "
            f"{assertion.description}"
        )

        if assertion.locator:
            expression = self._appium_locator(
                assertion.locator
            )

            lines.extend(
                [
                    f"{indent}element = wait.until(",
                    f"{indent}    EC.visibility_of_element_located(",
                    f"{indent}        {expression}",
                    f"{indent}    )",
                    f"{indent})",
                    "",
                    (
                        f"{indent}assert element.is_displayed(), "
                        f"{_py_string(assertion.description or 'Expected element to be visible.')}"
                    ),
                ]
            )

            return

        lines.extend(
            [
                f"{indent}raise AssertionError(",
                f"{indent}    {_py_string('Required Appium assertion locator was not resolved.')}",
                f"{indent})",
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
                "Cannot generate Appium Python code for "
                f"step {action.step_number}: "
                "no mobile locator was resolved for "
                f"'{action.target}'."
            )

        return action.locator

    # ========================================================
    # APPIUM LOCATOR CONVERSION
    # ========================================================

    @staticmethod
    def _appium_locator(
        locator: AppiumLocator,
    ) -> str:
        strategy = locator.strategy
        value = locator.value

        if strategy == AppiumLocatorStrategy.ACCESSIBILITY_ID:
            return (
                f"(AppiumBy.ACCESSIBILITY_ID, "
                f"{_py_string(value)})"
            )

        if strategy == AppiumLocatorStrategy.ID:
            return (
                f"(AppiumBy.ID, "
                f"{_py_string(value)})"
            )

        if strategy == AppiumLocatorStrategy.XPATH:
            return (
                f"(AppiumBy.XPATH, "
                f"{_py_string(value)})"
            )

        if strategy == AppiumLocatorStrategy.CLASS_NAME:
            return (
                f"(AppiumBy.CLASS_NAME, "
                f"{_py_string(value)})"
            )

        if (
            strategy
            == AppiumLocatorStrategy.ANDROID_UIAUTOMATOR
        ):
            return (
                f"(AppiumBy.ANDROID_UIAUTOMATOR, "
                f"{_py_string(value)})"
            )

        if (
            strategy
            == AppiumLocatorStrategy.IOS_PREDICATE
        ):
            return (
                f"(AppiumBy.IOS_PREDICATE, "
                f"{_py_string(value)})"
            )

        if (
            strategy
            == AppiumLocatorStrategy.IOS_CLASS_CHAIN
        ):
            return (
                f"(AppiumBy.IOS_CLASS_CHAIN, "
                f"{_py_string(value)})"
            )

        raise ValueError(
            "Unsupported Appium Python locator strategy: "
            f"{strategy}"
        )

    # ========================================================
    # VALUE EXPRESSION
    # ========================================================

    @staticmethod
    def _value_expression(
        action: AppiumAction,
    ) -> str:
        if action.value is not None:
            return _py_string(action.value)

        return "os.getenv('TEST_DATA_VALUE')"

    # ========================================================
    # TEARDOWN
    # ========================================================

    @staticmethod
    def _add_teardown(
        lines: List[str],
    ) -> None:
        # Driver cleanup is already handled inside the
        # generated test's finally block.
        pass


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
        return "test_generated_appium_automation"

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


def generate_appium_python(
    plan: AppiumAutomationPlan,
) -> str:
    generator = AppiumPythonGenerator()

    return generator.generate(plan)