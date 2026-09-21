from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# SUPPORTED AUTOMATION FRAMEWORKS
# ============================================================

class AutomationFramework(str, Enum):
    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"
    APPIUM = "appium"
    CYPRESS = "cypress"


# ============================================================
# SUPPORTED LANGUAGES
# ============================================================

class AutomationLanguage(str, Enum):
    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"


# ============================================================
# APPLICATION TYPES
# ============================================================

class ApplicationType(str, Enum):
    WEB = "web"
    MOBILE = "mobile"
    RESPONSIVE_WEB = "responsive_web"


# ============================================================
# SUPPORTED PLATFORMS
# ============================================================

class MobilePlatform(str, Enum):
    ANDROID = "android"
    IOS = "ios"


# ============================================================
# TEST RUNNERS
# ============================================================

class TestRunner(str, Enum):
    PYTEST = "pytest"
    TESTNG = "testng"
    JUNIT = "junit"
    CYPRESS = "cypress"


# ============================================================
# AUTOMATION ACTION TYPES
# ============================================================

class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    ENTER = "enter"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    HOVER = "hover"
    PRESS = "press"
    CLEAR = "clear"
    UPLOAD = "upload"
    LOGIN = "login"
    CAPTURE = "capture"
    CAPTURE_TEXT = "capture_text"
    RECEIVE_OTP = "receive_otp"
    EXTRACT_VALUE = "extract_value"

    ASSERT_VISIBLE = "assert_visible"
    ASSERT_NOT_VISIBLE = "assert_not_visible"
    ASSERT_HIDDEN = "assert_hidden"
    ASSERT_TEXT = "assert_text"
    ASSERT_VALUE = "assert_value"
    ASSERT_URL = "assert_url"
    ASSERT_ENABLED = "assert_enabled"
    ASSERT_DISABLED = "assert_disabled"
    ASSERT = "assert"
    VERIFY = "verify"

    WAIT = "wait"


# ============================================================
# LOCATOR STRATEGY
# ============================================================

class LocatorStrategy(str, Enum):
    ROLE = "role"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    TEXT = "text"
    TEST_ID = "test_id"
    ACCESSIBILITY_ID = "accessibility_id"
    CSS = "css"
    XPATH = "xpath"
    ID = "id"
    NAME = "name"


# ============================================================
# LOCATOR
# ============================================================

class Locator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: LocatorStrategy
    value: str = Field(min_length=1)

    # Optional semantic information used by the generator
    description: Optional[str] = None
    name: Optional[str] = None


# ============================================================
# TEST DATA
# ============================================================

class TestData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: Optional[str] = None

    # Examples:
    # "valid_username"
    # "existing_employee_id"
    # "valid_leave_date_range"

    source: str = "requirement"

    # IMPORTANT:
    # generated = False means AI must not invent the value.
    generated: bool = False


# ============================================================
# AUTOMATION STEP
# ============================================================

class AutomationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_number: int = Field(ge=1)

    action: ActionType

    # Business-level target (UI element only).
    target: Optional[str] = None

    # Actual locator discovered from application context.
    locator: Optional[Locator] = None

    # Input value / test data reference.
    value: Optional[str] = None

    # Source for operation (e.g., "notification_shade", "sms", "api", "ui")
    source: Optional[str] = None

    # Variable name for dynamic capture
    variable_name: Optional[str] = None

    # Expected behavior associated with this step.
    expected_result: Optional[str] = None

    # Indicates system/non-UI operation
    is_system_operation: bool = False

    # Traceability back to Stage 1.
    source_step: Optional[int] = None


# ============================================================
# ASSERTION
# ============================================================

class AutomationAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_type: ActionType

    target: Optional[str] = None

    locator: Optional[Locator] = None

    expected_value: Optional[str] = None

    description: str

    source_expected_result: Optional[str] = None


# ============================================================
# AUTOMATION CONFIGURATION
# ============================================================

class AutomationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    browser: Optional[str] = "chrome"

    base_url: Optional[str] = None

    headless: bool = True

    timeout_ms: int = 30000

    platform: Optional[MobilePlatform] = None

    device_name: Optional[str] = None


# ============================================================
# AUTOMATION SPECIFICATION
# ============================================================

class AutomationSpec(BaseModel):
    """
    Framework-independent automation contract.

    Stage 1 produces business test cases.
    Stage 2 converts them into this specification.
    Framework-specific generators consume this specification.
    """

    model_config = ConfigDict(extra="forbid")

    test_case_id: str

    title: str

    test_type: Optional[str] = None

    priority: Optional[str] = None

    requirement: str

    application_url: str

    framework: AutomationFramework

    language: AutomationLanguage

    application_type: ApplicationType = ApplicationType.WEB

    test_runner: Optional[TestRunner] = None

    preconditions: List[str] = Field(default_factory=list)

    test_data: List[TestData] = Field(default_factory=list)

    steps: List[AutomationStep] = Field(default_factory=list)

    assertions: List[AutomationAssertion] = Field(
        default_factory=list
    )

    configuration: AutomationConfig = Field(
        default_factory=AutomationConfig
    )


# ============================================================
# FRAMEWORK / LANGUAGE VALIDATION
# ============================================================

SUPPORTED_COMBINATIONS = {
    AutomationFramework.SELENIUM: {
        AutomationLanguage.PYTHON,
        AutomationLanguage.JAVA,
        AutomationLanguage.JAVASCRIPT,
    },

    AutomationFramework.PLAYWRIGHT: {
        AutomationLanguage.PYTHON,
        AutomationLanguage.JAVA,
        AutomationLanguage.JAVASCRIPT,
    },

    AutomationFramework.APPIUM: {
        AutomationLanguage.PYTHON,
        AutomationLanguage.JAVA,
        AutomationLanguage.JAVASCRIPT,
    },

    AutomationFramework.CYPRESS: {
        AutomationLanguage.JAVASCRIPT,
    },
}


def validate_framework_language(
    framework: AutomationFramework,
    language: AutomationLanguage,
) -> None:
    """
    Validate that the selected framework/language combination
    is supported by Stage 2.
    """

    supported_languages = SUPPORTED_COMBINATIONS.get(framework)

    if not supported_languages:
        raise ValueError(
            f"Unsupported automation framework: {framework}"
        )

    if language not in supported_languages:
        raise ValueError(
            f"{framework.value} does not support "
            f"{language.value} in this generator."
        )


# ============================================================
# DEFAULT TEST RUNNER
# ============================================================

def get_default_test_runner(
    framework: AutomationFramework,
    language: AutomationLanguage,
) -> TestRunner:

    validate_framework_language(framework, language)

    if framework == AutomationFramework.CYPRESS:
        return TestRunner.CYPRESS

    if language == AutomationLanguage.PYTHON:
        return TestRunner.PYTEST

    if language == AutomationLanguage.JAVA:
        return TestRunner.TESTNG

    return TestRunner.CYPRESS
