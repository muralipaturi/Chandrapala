"""
Stage 2.7.2 - Selenium Java Generator

Deterministic Selenium + Java code generator.

Input:
    ResolvedAutomationPlan

Output:
    Selenium Java source code

Design principles:
    - No Gemini call
    - No AI-generated locators
    - Uses only resolved application evidence
    - Framework-independent planning remains unchanged
    - Generates JUnit 5 compatible Selenium Java
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
# SELENIUM JAVA GENERATOR
# ============================================================


class SeleniumJavaGenerator:
    """
    Generates deterministic Selenium Java automation code
    from a ResolvedAutomationPlan.
    """

    def generate(
        self,
        plan: ResolvedAutomationPlan,
    ) -> str:

        self._validate_plan(plan)

        lines: List[str] = []

        self._add_header(lines)
        self._add_class(lines, plan)
        self._add_setup(lines, plan)
        self._add_test_method(lines, plan)
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
                "Cannot generate Selenium Java code: "
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
                "package com.hospital.tests;",
                "",
                "import java.time.Duration;",
                "",
                "import org.junit.jupiter.api.AfterEach;",
                "import org.junit.jupiter.api.BeforeEach;",
                "import org.junit.jupiter.api.Test;",
                "import static org.junit.jupiter.api.Assertions.assertTrue;",
                "",
                "import org.openqa.selenium.By;",
                "import org.openqa.selenium.JavascriptExecutor;",
                "import org.openqa.selenium.WebDriver;",
                "import org.openqa.selenium.WebElement;",
                "import org.openqa.selenium.chrome.ChromeDriver;",
                "import org.openqa.selenium.support.ui.ExpectedConditions;",
                "import org.openqa.selenium.support.ui.Select;",
                "import org.openqa.selenium.support.ui.WebDriverWait;",
                "",
            ]
        )

    # ========================================================
    # CLASS
    # ========================================================

    @staticmethod
    def _add_class(
        lines: List[str],
        plan: ResolvedAutomationPlan,
    ) -> None:

        class_name = _java_class_name(
            plan.test_case_id,
            plan.title,
        )

        lines.extend(
            [
                f"public class {class_name} {{",
                "",
                "    private WebDriver driver;",
                "    private WebDriverWait wait;",
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

        url = _java_string(
            plan.application_url
        )

        lines.extend(
            [
                "    @BeforeEach",
                "    void setUp() {",
                "        System.out.println(\"Launching Chrome Browser...\");",
                "        driver = new ChromeDriver();",
                "",
                "        driver.manage()",
                "              .window()",
                "              .maximize();",
                "",
                "        wait = new WebDriverWait(",
                "            driver,",
                "            Duration.ofSeconds(15)",
                "        );",
                "",
                f"        driver.get({url});",
                "    }",
                "",
            ]
        )

    # ========================================================
    # TEST METHOD
    # ========================================================

    def _add_test_method(
        self,
        lines: List[str],
        plan: ResolvedAutomationPlan,
    ) -> None:

        lines.extend(
            [
                "    @Test",
                "    void generatedScenario() {",
                "",
                "        WebElement element;",
                "        String patient_id = \"\";",
                "        String capturedText = \"\";",
                "",
                "        try {",
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
            step_log = _java_string(f"Step {action.step_number}: {description}")
            lines.append(
                f"            System.out.println({step_log});"
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

            assert_log = _java_string(f"Verifying: {assertion.description}")
            lines.append(
                f"            System.out.println({assert_log});"
            )

            self._generate_assertion(
                lines,
                assertion,
            )

            lines.append("")

        lines.extend(
            [
                "            System.out.println(\"Test scenario completed successfully.\");",
                "",
                "        } catch (Exception e) {",
                "            System.err.println(\"Test scenario encountered an exception: \" + e.getMessage());",
                "            throw e;",
                "        } finally {",
                "            if (driver != null) {",
                "                driver.quit();",
                "            }",
                "        }",
                "    }",
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
            self._generate_navigate(
                lines,
                action,
            )
            return

        if action_type == ActionType.LOGIN:
            self._generate_login(
                lines,
                action,
            )
            return

        if action_type == ActionType.CLICK:
            self._generate_click(
                lines,
                action,
            )
            return

        if action_type == ActionType.FILL:
            self._generate_fill(
                lines,
                action,
            )
            return

        if action_type == ActionType.UPLOAD:
            self._generate_upload(
                lines,
                action,
            )
            return

        if action_type == ActionType.CAPTURE_TEXT:
            self._generate_capture_text(
                lines,
                action,
            )
            return

        if action_type == ActionType.SELECT:
            self._generate_select(
                lines,
                action,
            )
            return

        if action_type == ActionType.CLEAR:
            self._generate_clear(
                lines,
                action,
            )
            return

        if action_type == ActionType.ASSERT_VISIBLE:
            self._generate_assert_visible_action(
                lines,
                action,
            )
            return

        lines.append(
            f"            // Step action: {action_type.value} on {action.business_target or 'target'}"
        )

    # ========================================================
    # NAVIGATE
    # ========================================================

    @staticmethod
    def _generate_navigate(
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
                "            driver.get("
                f"{_java_string(target)}"
                ");"
            )

        else:

            lines.append(
                "            // Navigate to: "
                f"{_java_string(target)}"
            )

    # ========================================================
    # LOGIN
    # ========================================================

    @staticmethod
    def _generate_login(
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        lines.extend(
            [
                "            String username = System.getenv(\"TEST_USERNAME\");",
                "            String password = System.getenv(\"TEST_PASSWORD\");",
                "",
                "            if (username == null || password == null) {",
                "                throw new IllegalStateException(",
                "                    \"TEST_USERNAME and TEST_PASSWORD must be configured.\"",
                "                );",
                "            }",
                "",
                "            // Login credentials loaded from environment variables.",
            ]
        )

    # ========================================================
    # CLICK
    # ========================================================

    def _generate_click(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        locator = self._require_locator(
            action
        )

        selenium_locator = (
            self._selenium_locator(
                locator,
                action,
            )
        )

        lines.extend(
            [
                "            element = wait.until(",
                "                ExpectedConditions."
                "elementToBeClickable(",
                f"                    {selenium_locator}",
                "                )",
                "            );",
                "",
                "            element.click();",
            ]
        )

    # ========================================================
    # FILL
    # ========================================================

    def _generate_fill(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        locator = self._require_locator(
            action
        )

        selenium_locator = (
            self._selenium_locator(
                locator,
                action,
            )
        )

        value = self._value_expression(
            action
        )

        # Detect date fields by target name or date format value
        target_name = (action.business_target or "").lower()
        is_date = (
            any(k in target_name for k in ["dob", "date", "birth"])
            or (action.value_reference and bool(re.search(r"^\d{4}-\d{2}-\d{2}$|^\d{2}/\d{2}/\d{4}$", str(action.value_reference).strip())))
        )

        if is_date:
            lines.extend(
                [
                    "            element = wait.until(",
                    "                ExpectedConditions."
                    "presenceOfElementLocated(",
                    f"                    {selenium_locator}",
                    "                )",
                    "            );",
                    "",
                    "            ((JavascriptExecutor) driver).executeScript(",
                    "                \"arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change', { bubbles: true })); arguments[0].dispatchEvent(new Event('input', { bubbles: true }));\",",
                    "                element,",
                    f"                {value}",
                    "            );",
                ]
            )
        else:
            lines.extend(
                [
                    "            element = wait.until(",
                    "                ExpectedConditions."
                    "visibilityOfElementLocated(",
                    f"                    {selenium_locator}",
                    "                )",
                    "            );",
                    "",
                    "            element.clear();",
                    "",
                    f"            element.sendKeys({value});",
                ]
            )

    # ========================================================
    # UPLOAD
    # ========================================================

    def _generate_upload(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:

        locator = self._require_locator(
            action
        )

        selenium_locator = (
            self._selenium_locator(
                locator,
                action,
            )
        )

        value = self._value_expression(
            action
        )

        lines.extend(
            [
                "            WebElement fileInput = wait.until(",
                "                ExpectedConditions."
                "presenceOfElementLocated(",
                f"                    {selenium_locator}",
                "                )",
                "            );",
                "",
                f"            fileInput.sendKeys({value});",
            ]
        )

    # ========================================================
    # CAPTURE TEXT / SELECT / CLEAR
    # ========================================================

    def _generate_capture_text(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        selenium_locator = self._selenium_locator(locator, action)
        var_name = getattr(action, "variable_name", None) or "capturedText"
        var_assign = f"{var_name} =" if var_name in ("patient_id", "capturedText") else f"String {var_name} ="
        lines.extend(
            [
                "            element = wait.until(",
                "                ExpectedConditions.visibilityOfElementLocated(",
                f"                    {selenium_locator}",
                "                )",
                "            );",
                "",
                f"            {var_assign} element.getText().trim();",
                f"            System.out.println(\"Captured {var_name}: \" + {var_name});",
            ]
        )

    def _generate_select(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        selenium_locator = self._selenium_locator(locator, action)
        value = self._value_expression(action)
        lines.extend(
            [
                "            element = wait.until(",
                "                ExpectedConditions.visibilityOfElementLocated(",
                f"                    {selenium_locator}",
                "                )",
                "            );",
                "",
                "            new Select(element)",
                f"                .selectByVisibleText({value});",
            ]
        )

    def _generate_clear(
        self,
        lines: List[str],
        action: ResolvedAction,
    ) -> None:
        locator = self._require_locator(action)
        selenium_locator = self._selenium_locator(locator, action)
        lines.extend(
            [
                "            element = wait.until(",
                "                ExpectedConditions.visibilityOfElementLocated(",
                f"                    {selenium_locator}",
                "                )",
                "            );",
                "",
                "            element.clear();",
            ]
        )

    # ========================================================
    # ASSERT VISIBLE ACTION
    # ========================================================

    def _generate_assert_visible_action(
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

            selenium_locator = (
                self._selenium_locator(
                    resolution.locator,
                    action,
                )
            )

            lines.extend(
                [
                    "            element = wait.until(",
                    "                ExpectedConditions."
                    "visibilityOfElementLocated(",
                    f"                    {selenium_locator}",
                    "                )",
                    "            );",
                    "",
                    f"            assertTrue(element.isDisplayed(), \"Expected element to be visible: \" + {_java_string(str(action.business_target or 'target'))});",
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
                "            throw new AssertionError(",
                f"                {_java_string(message)}",
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

        if assertion.assertion_type == ActionType.ASSERT_URL:
            url_target = assertion.business_target or ""
            lines.extend(
                [
                    f"            assertTrue(driver.getCurrentUrl().contains({_java_string(url_target)}), \"Expected URL to contain: \" + {_java_string(url_target)});",
                ]
            )
            return

        resolution = (
            assertion.locator_resolution
        )

        if (
            resolution
            and resolution.found
            and resolution.locator
        ):

            selenium_locator = (
                self._selenium_locator(
                    resolution.locator
                )
            )

            lines.extend(
                [
                    "            WebElement assertionElement = wait.until(",
                    "                ExpectedConditions."
                    "visibilityOfElementLocated(",
                    f"                    {selenium_locator}",
                    "                )",
                    "            );",
                    "",
                    f"            assertTrue(assertionElement.isDisplayed(), \"Expected element to be visible: \" + {_java_string(str(assertion.description))});",
                ]
            )

            return

        lines.extend(
            [
                f"            assertTrue(driver.getPageSource().contains({_java_string(assertion.description)}), \"Expected page to contain: \" + {_java_string(assertion.description)});",
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
                "Cannot generate Selenium Java code "
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
        action: ResolvedAction | None = None,
    ) -> str:

        strategy = (
            locator.strategy.value
        )

        value = locator.value

        matched_element = None
        if action and getattr(action, "locator_resolution", None):
            matched_element = getattr(action.locator_resolution, "matched_element", None)

        element_id = getattr(locator, "element_id", None) or (
            getattr(matched_element, "element_id", None) if matched_element else None
        )

        # ----------------------------------------------------
        # ID
        # ----------------------------------------------------

        if strategy == "id":
            return (
                f"By.id({_java_string(value)})"
            )

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if strategy == "name":
            return (
                f"By.name({_java_string(value)})"
            )

        # ----------------------------------------------------
        # CSS
        # ----------------------------------------------------

        if strategy == "css":
            return (
                f"By.cssSelector("
                f"{_java_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # XPATH
        # ----------------------------------------------------

        if strategy == "xpath":
            return (
                f"By.xpath("
                f"{_java_string(value)}"
                ")"
            )

        # ----------------------------------------------------
        # LINK TEXT
        # ----------------------------------------------------

        if strategy in ("link_text", "link"):
            return (
                f"By.linkText({_java_string(value)})"
            )

        # ----------------------------------------------------
        # PLACEHOLDER
        # ----------------------------------------------------

        if strategy == "placeholder":
            css_value = _css_attribute_value(
                value
            )
            return (
                "By.cssSelector("
                f"{_java_string(css_value)}"
                ")"
            )

        # ----------------------------------------------------
        # LABEL / ARIA LABEL
        # ----------------------------------------------------

        if strategy in ("label", "aria_label"):
            if element_id:
                return f"By.id({_java_string(element_id)})"

            escaped = str(value).replace("\"", "\\\"")
            if action and getattr(action, "action", None) == ActionType.SELECT:
                xpath = f"//label[normalize-space()=\"{escaped}\"]/following-sibling::select[1]"
            else:
                xpath = f"//label[normalize-space()=\"{escaped}\"]/following-sibling::input[1]"
            return f"By.xpath({_java_string(xpath)})"

        # ----------------------------------------------------
        # ACCESSIBILITY ID
        # ----------------------------------------------------

        if strategy == "accessibility_id":
            css_value = _css_attribute_value(
                value,
                attribute="aria-label",
            )
            return (
                "By.cssSelector("
                f"{_java_string(css_value)}"
                ")"
            )

        # ----------------------------------------------------
        # TEST ID
        # ----------------------------------------------------

        if strategy == "test_id":
            css_value = _css_attribute_value(
                value,
                attribute="data-testid",
            )
            return (
                "By.cssSelector("
                f"{_java_string(css_value)}"
                ")"
            )

        # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------

        if strategy == "role":
            role_name = getattr(locator, "name", None)
            if not role_name and action and action.business_target:
                t = action.business_target.strip()
                if value == "button" and ("button" in t.lower() or "btn" in t.lower()):
                    role_name = re.sub(r"\s+(?:button|btn)$", "", t, flags=re.I).strip()
                elif value == "link" and "link" in t.lower():
                    role_name = re.sub(r"\s+link$", "", t, flags=re.I).strip()

            if role_name:
                if value == "link":
                    return f"By.linkText({_java_string(role_name)})"
                if value == "button":
                    return f"By.xpath({_java_string(f'//button[normalize-space()={_java_string(role_name)}]')})"

            if value == "link":
                target_text = action.business_target if action else None
                if target_text:
                    clean_t = re.sub(r"\s+link$", "", target_text, flags=re.I).strip()
                    return f"By.linkText({_java_string(clean_t)})"

            if value == "button":
                target_text = action.business_target if action else None
                if target_text:
                    clean_b = re.sub(r"\s+(?:button|btn)$", "", target_text, flags=re.I).strip()
                    return f"By.xpath({_java_string(f'//button[normalize-space()={_java_string(clean_b)}]')})"

            css_value = _css_attribute_value(
                value,
                attribute="role",
            )
            return (
                "By.cssSelector("
                f"{_java_string(css_value)}"
                ")"
            )

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        if strategy == "text":
            # For text / link targets: emit By.linkText(...) when target is a link
            if action and (
                "link" in (action.business_target or "").lower()
                or (matched_element and getattr(matched_element, "tag", None) == "a")
            ):
                link_text = re.sub(r"\s+link$", "", value, flags=re.I).strip() or value
                return f"By.linkText({_java_string(link_text)})"

            xpath = _text_xpath(
                value
            )
            return (
                "By.xpath("
                f"{_java_string(xpath)}"
                ")"
            )

        raise ValueError(
            "Unsupported Selenium Java "
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
            reference = str(action.value_reference).strip()
            clean_var = re.sub(r"^[\$\{\}\s]+|[\}\s]+$", "", reference)
            var_name = getattr(action, "variable_name", None)

            # In-test dynamic variables emitted as raw Java identifiers
            if clean_var in ("patient_id", "patientId", "captured_value", "captured_patient_id", "capturedText", "extractedVal", "extractedOtp", var_name) or (var_name and clean_var == var_name):
                return clean_var

            environment_references = {
                "test_username": "TEST_USERNAME",
                "test_password": "TEST_PASSWORD",
            }

            env_name = environment_references.get(reference.lower())
            if env_name:
                return (
                    "System.getenv("
                    f"{_java_string(env_name)}"
                    ")"
                )

            if reference in ("TEST_USERNAME", "TEST_PASSWORD", "TEST_OTP"):
                return (
                    "System.getenv("
                    f"{_java_string(reference)}"
                    ")"
                )

            # Literal value (e.g. "Murali", "Paturi", "1995-01-15", "Male")
            return _java_string(reference)

        return "\"\""

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
                "",
                "        if (driver != null) {",
                "            driver.quit();",
                "        }",
                "    }",
                "}",
            ]
        )


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def _java_string(
    value: str,
) -> str:
    """
    Safely convert Python text into a Java string literal.
    """

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
    """
    Generate a valid Java class name.
    """

    raw = (
        f"{test_case_id}_{title}"
    )

    parts = re.findall(
        r"[A-Za-z0-9]+",
        raw,
    )

    if not parts:
        return "GeneratedSeleniumTest"

    name = "".join(
        part[:1].upper()
        + part[1:]
        for part in parts
    )

    if name[0].isdigit():
        name = (
            "Test"
            + name
        )

    if not name.endswith("Test"):
        name += "Test"

    return name


def _css_attribute_value(
    value: str,
    attribute: str = "placeholder",
) -> str:
    """
    Build an attribute CSS selector.
    """

    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace("\"", "\\\"")
    )

    return (
        f"[{attribute}=\"{escaped}\"]"
    )


def _text_xpath(
    value: str,
) -> str:
    """
    Build an XPath using normalize-space().
    """

    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace("\"", "\\\"")
    )

    return (
        "//*[normalize-space()="
        f"\"{escaped}\""
        "]"
    )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def generate_selenium_java(
    plan: ResolvedAutomationPlan,
) -> str:
    """
    Generate Selenium Java source code.
    """

    generator = (
        SeleniumJavaGenerator()
    )

    return generator.generate(
        plan
    )