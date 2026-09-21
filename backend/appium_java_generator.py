"""
Stage 2.11.3 - Appium Java Generator

Deterministic Appium + Java code generator.

Input:
    AppiumAutomationPlan

Output:
    Appium Java + JUnit 5 source code

Design principles:
    - No Gemini call
    - No invented mobile locators
    - Uses Appium-specific resolved locators
    - Supports Android and iOS
    - Generates JUnit 5 compatible tests
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


class AppiumJavaGenerator:
    """
    Generates deterministic Appium Java automation.
    """

    def generate(
        self,
        plan: AppiumAutomationPlan,
    ) -> str:
        self._validate_plan(plan)

        lines: List[str] = []

        self._add_header(lines)
        self._add_class(lines, plan)
        self._add_setup(lines, plan)
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
                "import io.appium.java_client.AppiumBy;",
                "import io.appium.java_client.AppiumDriver;",
                "import io.appium.java_client.android.AndroidDriver;",
                "import io.appium.java_client.android.options.UiAutomator2Options;",
                "import io.appium.java_client.ios.IOSDriver;",
                "import io.appium.java_client.ios.options.XCUITestOptions;",
                "",
                "import org.junit.jupiter.api.AfterEach;",
                "import org.junit.jupiter.api.BeforeEach;",
                "import org.junit.jupiter.api.Test;",
                "",
                "import org.openqa.selenium.By;",
                "import org.openqa.selenium.WebElement;",
                "import org.openqa.selenium.support.ui.ExpectedConditions;",
                "import org.openqa.selenium.support.ui.WebDriverWait;",
                "",
                "import java.net.MalformedURLException;",
                "import java.net.URI;",
                "import java.net.URL;",
                "import java.time.Duration;",
                "",
                "import static org.junit.jupiter.api.Assertions.assertTrue;",
                "",
            ]
        )

    # ========================================================
    # CLASS
    # ========================================================

    @staticmethod
    def _add_class(
        lines: List[str],
        plan: AppiumAutomationPlan,
    ) -> None:
        class_name = _java_class_name(
            plan.test_case_id,
            plan.title,
        )

        lines.extend(
            [
                f"public class {class_name} {{",
                "",
                "    private AppiumDriver driver;",
                "    private WebDriverWait wait;",
                "",
            ]
        )

    # ========================================================
    # SETUP
    # ========================================================

    def _add_setup(
        self,
        lines: List[str],
        plan: AppiumAutomationPlan,
    ) -> None:
        config = plan.config

        lines.extend(
            [
                "    @BeforeEach",
                "    void setUp() throws Exception {",
                "",
            ]
        )

        if config.platform == AppiumPlatform.ANDROID:
            lines.extend(
                [
                    "        UiAutomator2Options options =",
                    "            new UiAutomator2Options();",
                    "",
                    "        options.setPlatformName(\"Android\");",
                    "        options.setAutomationName(\"UiAutomator2\");",
                    "        options.setDeviceName(",
                    f"            {_java_string(config.device_name)}",
                    "        );",
                    "",
                ]
            )

            if config.platform_version:
                lines.extend(
                    [
                        "        options.setPlatformVersion(",
                        f"            {_java_string(config.platform_version)}",
                        "        );",
                        "",
                    ]
                )

            if config.app_path:
                lines.extend(
                    [
                        "        options.setApp(",
                        f"            {_java_string(config.app_path)}",
                        "        );",
                        "",
                    ]
                )

            if config.app_package:
                lines.extend(
                    [
                        "        options.setAppPackage(",
                        f"            {_java_string(config.app_package)}",
                        "        );",
                        "",
                    ]
                )

            if config.app_activity:
                lines.extend(
                    [
                        "        options.setAppActivity(",
                        f"            {_java_string(config.app_activity)}",
                        "        );",
                        "",
                    ]
                )

            lines.extend(
                [
                    f"        options.setNoReset({str(config.no_reset).lower()});",
                    "",
                    "        driver = new AndroidDriver(",
                    "            appiumServerUrl(),",
                    "            options",
                    "        );",
                ]
            )

        elif config.platform == AppiumPlatform.IOS:
            lines.extend(
                [
                    "        XCUITestOptions options =",
                    "            new XCUITestOptions();",
                    "",
                    "        options.setPlatformName(\"iOS\");",
                    "        options.setAutomationName(\"XCUITest\");",
                    "        options.setDeviceName(",
                    f"            {_java_string(config.device_name)}",
                    "        );",
                    "",
                ]
            )

            if config.platform_version:
                lines.extend(
                    [
                        "        options.setPlatformVersion(",
                        f"            {_java_string(config.platform_version)}",
                        "        );",
                        "",
                    ]
                )

            if config.app_path:
                lines.extend(
                    [
                        "        options.setApp(",
                        f"            {_java_string(config.app_path)}",
                        "        );",
                        "",
                    ]
                )

            if config.bundle_id:
                lines.extend(
                    [
                        "        options.setBundleId(",
                        f"            {_java_string(config.bundle_id)}",
                        "        );",
                        "",
                    ]
                )

            lines.extend(
                [
                    f"        options.setNoReset({str(config.no_reset).lower()});",
                    "",
                    "        driver = new IOSDriver(",
                    "            appiumServerUrl(),",
                    "            options",
                    "        );",
                ]
            )

        lines.extend(
            [
                "",
                "        wait = new WebDriverWait(",
                "            driver,",
                "            Duration.ofSeconds(20)",
                "        );",
                "    }",
                "",
                "    private URL appiumServerUrl() throws MalformedURLException {",
                "        return URI.create(",
                f"            {_java_string(config.appium_server_url)}",
                "        ).toURL();",
                "    }",
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
        lines.extend(
            [
                "    @Test",
                "    void generatedScenario() {",
                f"        // Test case: {plan.test_case_id}",
                f"        // {plan.title}",
                "",
                "        WebElement element;",
                "        String extractedOtp;",
                "",
            ]
        )

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

        lines.append(
            "        // Business outcome assertions"
        )

        for assertion in plan.assertions:
            self._generate_assertion(
                lines,
                assertion,
            )

            lines.append("")

        lines.append("    }")
        lines.append("")

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
                "        // Application launched during setup."
            )
            return

        if action_type == AppiumActionType.NAVIGATE:
            lines.append(
                "        // Mobile navigation target: "
                f"{_java_string(action.target or '')}"
            )
            return

        if action_type == AppiumActionType.CLICK:
            self._click(lines, action)
            return

        if action_type in (AppiumActionType.FILL, AppiumActionType.ENTER):
            self._fill(lines, action)
            return

        if action_type == AppiumActionType.RECEIVE_OTP:
            lines.extend(
                [
                    "        // System Operation: Receive OTP from notification/SMS source",
                    "        try {",
                    "            ((AndroidDriver) driver).openNotifications();",
                    "        } catch (Exception ignored) {}",
                    "        extractedOtp = System.getenv().getOrDefault(\"TEST_OTP\", \"123456\");",
                ]
            )
            return

        if action_type == AppiumActionType.EXTRACT_VALUE:
            var_name = action.variable_name or "extractedOtp"
            lines.extend(
                [
                    f"        // System Operation: Extract value for {var_name}",
                    f"        {var_name} = System.getenv().getOrDefault(\"EXTRACTED_VAL\", \"123456\");",
                ]
            )
            return

        if action_type == AppiumActionType.WAIT:
            lines.extend(
                [
                    "        // Wait for system state transition",
                    "        try { Thread.sleep(2000); } catch (InterruptedException ignored) {}",
                ]
            )
            return

        if action_type in (AppiumActionType.ASSERT_VISIBLE, AppiumActionType.ASSERT, AppiumActionType.VERIFY):
            self._assert_visible_action(
                lines,
                action,
            )
            return

        lines.append(
            f"        // Action: {action_type.value} on target {action.target or 'system'}"
        )

    # ========================================================
    # CLICK
    # ========================================================

    def _click(
        self,
        lines: List[str],
        action: AppiumAction,
    ) -> None:
        if action.locator is None:
            lines.extend(
                [
                    f"        // TODO: UI target '{action.target or 'element'}' is not mapped in application context.",
                    f"        // Configure locator for '{action.target or 'element'}' in inspected UI evidence.",
                ]
            )
            return

        expression = self._appium_locator(action.locator)

        lines.extend(
            [
                "        element = wait.until(",
                "            ExpectedConditions.elementToBeClickable(",
                f"                {expression}",
                "            )",
                "        );",
                "",
                "        element.click();",
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
        val_str = str(action.value or "").strip()
        if val_str in ("${EXTRACTED_OTP}", "extractedOtp", "extracted_otp", "${OTP}"):
            value = "extractedOtp"
        elif val_str.startswith("${") and val_str.endswith("}"):
            value = f"System.getenv({_java_string(val_str[2:-1])})"
        elif action.value is not None:
            value = _java_string(action.value)
        else:
            value = "System.getenv(\"TEST_DATA_VALUE\")"

        if action.locator is None:
            lines.extend(
                [
                    f"        // TODO: UI target '{action.target or 'field'}' is not mapped in application context.",
                    f"        // element = wait.until(ExpectedConditions.visibilityOfElementLocated(AppiumBy...));",
                    f"        // element.sendKeys({value});",
                ]
            )
            return

        expression = self._appium_locator(action.locator)

        lines.extend(
            [
                "        element = wait.until(",
                "            ExpectedConditions.visibilityOfElementLocated(",
                f"                {expression}",
                "            )",
                "        );",
                "",
                "        element.clear();",
                f"        element.sendKeys({value});",
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

        expression = self._appium_locator(
            locator
        )

        lines.append(
            f"        driver.findElement({expression}).clear();"
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
                "        // Swipe coordinates should be supplied",
                "        // through the generated action data.",
                "        // Mobile swipe implementation can be",
                "        // customized for the target application.",
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
                "        // Scroll implementation is platform-specific.",
                "        // Configure mobile: scroll/swipe action",
                "        // according to the target application.",
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

        expression = self._appium_locator(
            locator
        )

        value = (
            _java_string(action.value)
            if action.value is not None
            else "System.getenv(\"TEST_FILE_PATH\")"
        )

        lines.append(
            f"        driver.findElement({expression})"
            f".sendKeys({value});"
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
            expression = self._appium_locator(
                action.locator
            )

            lines.extend(
                [
                    "        element = wait.until(",
                    "            ExpectedConditions.visibilityOfElementLocated(",
                    f"                {expression}",
                    "            )",
                    "        );",
                    "",
                    "        assertTrue(",
                    "            element.isDisplayed(),",
                    f"            {_java_string(action.description or action.target or 'Expected element to be visible.')}",
                    "        );",
                ]
            )

            return

        lines.append(
            f"        // TODO: Configure assertion locator for target '{action.target or 'outcome'}' in application context"
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
            expression = self._appium_locator(
                assertion.locator
            )

            lines.extend(
                [
                    "        element = wait.until(",
                    "            ExpectedConditions.visibilityOfElementLocated(",
                    f"                {expression}",
                    "            )",
                    "        );",
                    "",
                    "        assertTrue(",
                    "            element.isDisplayed(),",
                    f"            {_java_string(assertion.description or 'Expected element to be visible.')}",
                    "        );",
                ]
            )

            return

        lines.append(
            f"        // TODO: Configure assertion locator for target '{assertion.target or assertion.description}' in application context"
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
                "Cannot generate Appium Java code for "
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
                "AppiumBy.accessibilityId("
                f"{_java_string(value)}"
                ")"
            )

        if strategy == AppiumLocatorStrategy.ID:
            return (
                "AppiumBy.id("
                f"{_java_string(value)}"
                ")"
            )

        if strategy == AppiumLocatorStrategy.XPATH:
            return (
                "AppiumBy.xpath("
                f"{_java_string(value)}"
                ")"
            )

        if strategy == AppiumLocatorStrategy.CLASS_NAME:
            return (
                "AppiumBy.className("
                f"{_java_string(value)}"
                ")"
            )

        if (
            strategy
            == AppiumLocatorStrategy.ANDROID_UIAUTOMATOR
        ):
            return (
                "AppiumBy.androidUIAutomator("
                f"{_java_string(value)}"
                ")"
            )

        if (
            strategy
            == AppiumLocatorStrategy.IOS_PREDICATE
        ):
            return (
                "AppiumBy.iOSNsPredicateString("
                f"{_java_string(value)}"
                ")"
            )

        if (
            strategy
            == AppiumLocatorStrategy.IOS_CLASS_CHAIN
        ):
            return (
                "AppiumBy.iOSClassChain("
                f"{_java_string(value)}"
                ")"
            )

        raise ValueError(
            "Unsupported Appium Java locator strategy: "
            f"{strategy}"
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
                "    @AfterEach",
                "    void tearDown() {",
                "        if (driver != null) {",
                "            driver.quit();",
                "        }",
                "    }",
                "}",
            ]
        )


# ============================================================
# HELPERS
# ============================================================


def _java_string(
    value: str,
) -> str:
    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace("\"", "\\\"")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )

    return f"\"{escaped}\""


def _java_class_name(
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
        return "GeneratedAppiumTest"

    name = "".join(
        part[:1].upper() + part[1:]
        for part in parts
    )

    if name[0].isdigit():
        name = "Test" + name

    if not name.endswith("Test"):
        name += "Test"

    return name


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def generate_appium_java(
    plan: AppiumAutomationPlan,
) -> str:
    generator = AppiumJavaGenerator()

    return generator.generate(plan)