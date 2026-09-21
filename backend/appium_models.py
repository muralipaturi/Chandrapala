"""
Stage 2.11.1 - Appium configuration and models.

Defines mobile automation configuration independently from
Selenium and Playwright web automation.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# PLATFORM
# ============================================================


class AppiumPlatform(str, Enum):
    ANDROID = "android"
    IOS = "ios"


# ============================================================
# AUTOMATION ENGINE
# ============================================================


class AppiumAutomationName(str, Enum):
    UIAUTOMATOR2 = "UiAutomator2"
    XCUITEST = "XCUITest"


# ============================================================
# DEVICE TYPE
# ============================================================


class AppiumDeviceType(str, Enum):
    EMULATOR = "emulator"
    REAL_DEVICE = "real_device"
    SIMULATOR = "simulator"


# ============================================================
# APPIUM CONFIGURATION
# ============================================================


class AppiumConfig(BaseModel):
    """
    Runtime configuration required to launch an Appium session.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    platform: AppiumPlatform

    automation_name: AppiumAutomationName

    device_name: str = Field(
        min_length=1,
        description="Configured mobile device or simulator name.",
    )

    device_type: AppiumDeviceType

    appium_server_url: str = (
        "http://127.0.0.1:4723"
    )

    app_path: Optional[str] = None

    app_package: Optional[str] = None

    app_activity: Optional[str] = None

    bundle_id: Optional[str] = None

    platform_version: Optional[str] = None

    no_reset: bool = True

    auto_grant_permissions: bool = True

    new_command_timeout: int = Field(
        default=120,
        ge=1,
    )


# ============================================================
# APPIUM LOCATOR STRATEGY
# ============================================================


class AppiumLocatorStrategy(str, Enum):
    ACCESSIBILITY_ID = "accessibility_id"
    ID = "id"
    XPATH = "xpath"
    CLASS_NAME = "class_name"
    ANDROID_UIAUTOMATOR = "android_uiautomator"
    IOS_PREDICATE = "ios_predicate"
    IOS_CLASS_CHAIN = "ios_class_chain"


# ============================================================
# APPIUM LOCATOR
# ============================================================


class AppiumLocator(BaseModel):
    """
    A mobile locator resolved from application evidence.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    strategy: AppiumLocatorStrategy

    value: str = Field(
        min_length=1
    )

    description: str = ""


# ============================================================
# APPIUM ACTION TYPES
# ============================================================


class AppiumActionType(str, Enum):
    LAUNCH = "launch"
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    ENTER = "enter"
    CLEAR = "clear"
    SWIPE = "swipe"
    SCROLL = "scroll"
    BACK = "back"
    UPLOAD = "upload"
    RECEIVE_OTP = "receive_otp"
    EXTRACT_VALUE = "extract_value"
    WAIT = "wait"
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_TEXT = "assert_text"
    ASSERT_ENABLED = "assert_enabled"
    ASSERT = "assert"
    VERIFY = "verify"


# ============================================================
# APPIUM ACTION
# ============================================================


class AppiumAction(BaseModel):
    """
    A resolved mobile automation action.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    step_number: int = Field(
        ge=1
    )

    action: AppiumActionType

    target: Optional[str] = None

    locator: Optional[AppiumLocator] = None

    value: Optional[str] = None

    source: Optional[str] = None

    variable_name: Optional[str] = None

    is_system_operation: bool = False

    description: str = ""


# ============================================================
# APPIUM ASSERTION
# ============================================================


class AppiumAssertion(BaseModel):
    """
    Mobile automation assertion.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    assertion_type: AppiumActionType

    target: Optional[str] = None

    locator: Optional[AppiumLocator] = None

    expected_value: Optional[str] = None

    description: str = ""


# ============================================================
# APPIUM AUTOMATION PLAN
# ============================================================


class AppiumAutomationPlan(BaseModel):
    """
    Complete mobile automation plan.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    test_case_id: str = Field(
        min_length=1
    )

    title: str = Field(
        min_length=1
    )

    config: AppiumConfig

    actions: list[AppiumAction] = Field(
        default_factory=list
    )

    assertions: list[AppiumAssertion] = Field(
        default_factory=list
    )


# ============================================================
# PLATFORM VALIDATION
# ============================================================


def validate_appium_config(
    config: AppiumConfig,
) -> None:
    """
    Validate platform-specific Appium requirements.
    """

    if config.platform == AppiumPlatform.ANDROID:

        if (
            config.automation_name
            != AppiumAutomationName.UIAUTOMATOR2
        ):
            raise ValueError(
                "Android Appium automation must use "
                "UiAutomator2."
            )

        if (
            not config.app_package
            and not config.app_path
        ):
            raise ValueError(
                "Android configuration requires either "
                "app_package or app_path."
            )

    elif config.platform == AppiumPlatform.IOS:

        if (
            config.automation_name
            != AppiumAutomationName.XCUITEST
        ):
            raise ValueError(
                "iOS Appium automation must use "
                "XCUITest."
            )

        if (
            not config.bundle_id
            and not config.app_path
        ):
            raise ValueError(
                "iOS configuration requires either "
                "bundle_id or app_path."
            )


# ============================================================
# FACTORY HELPERS
# ============================================================


def create_android_config(
    device_name: str,
    *,
    app_package: Optional[str] = None,
    app_activity: Optional[str] = None,
    app_path: Optional[str] = None,
    platform_version: Optional[str] = None,
    device_type: AppiumDeviceType = (
        AppiumDeviceType.EMULATOR
    ),
    appium_server_url: str = (
        "http://127.0.0.1:4723"
    ),
) -> AppiumConfig:

    config = AppiumConfig(
        platform=AppiumPlatform.ANDROID,
        automation_name=(
            AppiumAutomationName.UIAUTOMATOR2
        ),
        device_name=device_name,
        device_type=device_type,
        appium_server_url=appium_server_url,
        app_path=app_path,
        app_package=app_package,
        app_activity=app_activity,
        platform_version=platform_version,
    )

    validate_appium_config(config)

    return config


def create_ios_config(
    device_name: str,
    *,
    bundle_id: Optional[str] = None,
    app_path: Optional[str] = None,
    platform_version: Optional[str] = None,
    device_type: AppiumDeviceType = (
        AppiumDeviceType.SIMULATOR
    ),
    appium_server_url: str = (
        "http://127.0.0.1:4723"
    ),
) -> AppiumConfig:

    config = AppiumConfig(
        platform=AppiumPlatform.IOS,
        automation_name=(
            AppiumAutomationName.XCUITEST
        ),
        device_name=device_name,
        device_type=device_type,
        appium_server_url=appium_server_url,
        app_path=app_path,
        bundle_id=bundle_id,
        platform_version=platform_version,
    )

    validate_appium_config(config)

    return config