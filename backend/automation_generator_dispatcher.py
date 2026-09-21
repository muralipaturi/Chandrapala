"""
Stage 2.13 - Automation Generator Dispatcher

Central routing layer for all supported automation
framework + language combinations.

Supported combinations:

Selenium
    Python
    Java
    JavaScript

Playwright
    Python
    Java
    JavaScript

Appium
    Python
    Java
    JavaScript

Cypress
    JavaScript only

Responsibilities:
    1. Validate framework/language compatibility.
    2. Select the correct generator.
    3. Adapt a generic ResolvedAutomationPlan to an
       AppiumAutomationPlan when Appium is selected.
    4. Generate automation source code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Tuple

from automation_models import (
    ActionType,
    AutomationFramework,
    AutomationLanguage,
    validate_framework_language,
)

from automation_plan_resolver import (
    ResolvedAction,
    ResolvedAssertion,
    ResolvedAutomationPlan,
)

# ============================================================
# APPIUM MODELS
# ============================================================

from appium_models import (
    AppiumAction,
    AppiumActionType,
    AppiumAssertion,
    AppiumAutomationPlan,
    AppiumConfig,
    AppiumLocator,
    AppiumLocatorStrategy,
    create_android_config,
    create_ios_config,
)

# ============================================================
# GENERATORS
# ============================================================

from selenium_python_generator import (
    generate_selenium_python,
)

from selenium_java_generator import (
    generate_selenium_java,
)

from selenium_javascript_generator import (
    generate_selenium_javascript,
)

from playwright_python_generator import (
    generate_playwright_python,
)

from playwright_java_generator import (
    generate_playwright_java,
)

from playwright_javascript_generator import (
    generate_playwright_javascript,
)

from appium_python_generator import (
    generate_appium_python,
)

from appium_java_generator import (
    generate_appium_java,
)

from appium_javascript_generator import (
    generate_appium_javascript,
)

from cypress_javascript_generator import (
    generate_cypress_javascript,
)


# ============================================================
# TYPES
# ============================================================

WebGeneratorFunction = Callable[
    [ResolvedAutomationPlan],
    str,
]

AppiumGeneratorFunction = Callable[
    [AppiumAutomationPlan],
    str,
]

GeneratorKey = Tuple[
    AutomationFramework,
    AutomationLanguage,
]


# ============================================================
# RESULT
# ============================================================


@dataclass(frozen=True)
class AutomationGenerationResult:
    """
    Result returned by the central generator dispatcher.
    """

    framework: AutomationFramework

    language: AutomationLanguage

    code: str

    generator_name: str


# ============================================================
# WEB GENERATOR REGISTRY
# ============================================================

WEB_GENERATOR_REGISTRY: Dict[
    GeneratorKey,
    WebGeneratorFunction,
] = {
    # --------------------------------------------------------
    # Selenium
    # --------------------------------------------------------

    (
        AutomationFramework.SELENIUM,
        AutomationLanguage.PYTHON,
    ): generate_selenium_python,

    (
        AutomationFramework.SELENIUM,
        AutomationLanguage.JAVA,
    ): generate_selenium_java,

    (
        AutomationFramework.SELENIUM,
        AutomationLanguage.JAVASCRIPT,
    ): generate_selenium_javascript,

    # --------------------------------------------------------
    # Playwright
    # --------------------------------------------------------

    (
        AutomationFramework.PLAYWRIGHT,
        AutomationLanguage.PYTHON,
    ): generate_playwright_python,

    (
        AutomationFramework.PLAYWRIGHT,
        AutomationLanguage.JAVA,
    ): generate_playwright_java,

    (
        AutomationFramework.PLAYWRIGHT,
        AutomationLanguage.JAVASCRIPT,
    ): generate_playwright_javascript,

    # --------------------------------------------------------
    # Cypress
    # --------------------------------------------------------

    (
        AutomationFramework.CYPRESS,
        AutomationLanguage.JAVASCRIPT,
    ): generate_cypress_javascript,
}


# ============================================================
# APPIUM GENERATOR REGISTRY
# ============================================================

APPIUM_GENERATOR_REGISTRY: Dict[
    GeneratorKey,
    AppiumGeneratorFunction,
] = {
    (
        AutomationFramework.APPIUM,
        AutomationLanguage.PYTHON,
    ): generate_appium_python,

    (
        AutomationFramework.APPIUM,
        AutomationLanguage.JAVA,
    ): generate_appium_java,

    (
        AutomationFramework.APPIUM,
        AutomationLanguage.JAVASCRIPT,
    ): generate_appium_javascript,
}


# ============================================================
# COMBINED REGISTRY
# ============================================================

GENERATOR_REGISTRY = {
    **WEB_GENERATOR_REGISTRY,
    **APPIUM_GENERATOR_REGISTRY,
}


# ============================================================
# SUPPORTED COMBINATIONS
# ============================================================


def get_supported_combinations():
    """
    Return all framework/language combinations that have
    implemented generators.
    """

    return list(
        GENERATOR_REGISTRY.keys()
    )


# ============================================================
# GENERATOR LOOKUP
# ============================================================


def get_generator(
    framework: AutomationFramework,
    language: AutomationLanguage,
):
    """
    Return the registered generator for the selected
    framework/language combination.

    Compatibility validation occurs before lookup.
    """

    validate_framework_language(
        framework,
        language,
    )

    key = (
        framework,
        language,
    )

    generator = GENERATOR_REGISTRY.get(
        key
    )

    if generator is None:
        raise ValueError(
            "No automation generator is registered for "
            f"{framework.value} + {language.value}."
        )

    return generator


# ============================================================
# GENERATOR NAME
# ============================================================


def get_generator_name(
    framework: AutomationFramework,
    language: AutomationLanguage,
) -> str:
    """
    Return the selected generator function name.
    """

    generator = get_generator(
        framework,
        language,
    )

    return generator.__name__


# ============================================================
# APPIUM CONFIGURATION
# ============================================================


def _create_default_appium_config(
    *,
    platform: str = "android",
    device_name: str = "Android Emulator",
    app_package: str = "com.example.app",
    app_activity: str = ".MainActivity",
    app_path: str | None = None,
    bundle_id: str | None = None,
    platform_version: str | None = None,
    appium_server_url: str = (
        "http://127.0.0.1:4723"
    ),
) -> AppiumConfig:
    """
    Create a safe default Appium configuration.

    This configuration is intended for generated-code
    validation only.

    It does not start an Appium session.
    """

    normalized = (
        platform or "android"
    ).strip().lower()

    if normalized == "android":

        return create_android_config(
            device_name=device_name,
            app_package=app_package,
            app_activity=app_activity,
            app_path=app_path,
            platform_version=platform_version,
            appium_server_url=appium_server_url,
        )

    if normalized == "ios":

        return create_ios_config(
            device_name=(
                device_name
                or "iPhone Simulator"
            ),
            bundle_id=bundle_id,
            app_path=app_path,
            platform_version=platform_version,
            appium_server_url=appium_server_url,
        )

    raise ValueError(
        "Unsupported Appium platform: "
        f"{platform}"
    )


# ============================================================
# WEB LOCATOR -> APPIUM LOCATOR
# ============================================================


def _convert_locator_to_appium(
    locator,
) -> AppiumLocator | None:
    """
    Convert an existing web locator into an Appium
    locator where a safe semantic equivalent exists.

    This is intentionally conservative.

    We do not blindly convert arbitrary CSS selectors
    into mobile locators.
    """

    if locator is None:
        return None

    strategy = str(
        locator.strategy.value
    )

    value = str(
        locator.value
    )

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    if strategy == "id":

        return AppiumLocator(
            strategy=AppiumLocatorStrategy.ID,
            value=value,
            description=(
                "Converted from resolved web ID locator."
            ),
        )

    # --------------------------------------------------------
    # XPATH
    # --------------------------------------------------------

    if strategy == "xpath":

        return AppiumLocator(
            strategy=AppiumLocatorStrategy.XPATH,
            value=value,
            description=(
                "Converted from resolved web XPath locator."
            ),
        )

    # --------------------------------------------------------
    # ACCESSIBILITY ID
    # --------------------------------------------------------

    if strategy == "accessibility_id":

        return AppiumLocator(
            strategy=(
                AppiumLocatorStrategy.ACCESSIBILITY_ID
            ),
            value=value,
            description=(
                "Converted from accessibility identifier."
            ),
        )

    # --------------------------------------------------------
    # PLACEHOLDER
    #
    # Mobile does not have a universal HTML placeholder
    # equivalent. We therefore use XPath based on common
    # mobile text/content-desc evidence.
    # --------------------------------------------------------

    if strategy == "placeholder":

        xpath = (
            f"//*[@text={_xpath_literal(value)} "
            f"or @content-desc={_xpath_literal(value)}]"
        )

        return AppiumLocator(
            strategy=AppiumLocatorStrategy.XPATH,
            value=xpath,
            description=(
                "Converted placeholder evidence to a "
                "mobile text/content-desc XPath."
            ),
        )

    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    if strategy == "name":

        xpath = (
            f"//*[@name={_xpath_literal(value)} "
            f"or @resource-id={_xpath_literal(value)}]"
        )

        return AppiumLocator(
            strategy=AppiumLocatorStrategy.XPATH,
            value=xpath,
            description=(
                "Converted name evidence to a mobile "
                "attribute XPath."
            ),
        )

    # --------------------------------------------------------
    # CLASS NAME
    # --------------------------------------------------------

    if strategy == "class_name":

        return AppiumLocator(
            strategy=(
                AppiumLocatorStrategy.CLASS_NAME
            ),
            value=value,
            description=(
                "Converted class name locator."
            ),
        )

    # --------------------------------------------------------
    # OTHER WEB STRATEGIES
    # --------------------------------------------------------

    return None


# ============================================================
# ACTION TYPE CONVERSION
# ============================================================


def _convert_action_type(
    action: ActionType,
) -> AppiumActionType | None:

    mapping = {
        ActionType.CLICK:
            AppiumActionType.CLICK,

        ActionType.FILL:
            AppiumActionType.FILL,

        ActionType.UPLOAD:
            AppiumActionType.UPLOAD,

        ActionType.NAVIGATE:
            AppiumActionType.NAVIGATE,

        ActionType.ASSERT_VISIBLE:
            AppiumActionType.ASSERT_VISIBLE,

        ActionType.LOGIN:
            AppiumActionType.NAVIGATE,
    }

    return mapping.get(
        action
    )


# ============================================================
# RESOLVED ACTION -> APPIUM ACTION
# ============================================================


def _convert_resolved_action(
    action: ResolvedAction,
) -> AppiumAction | None:
    """
    Convert a generic resolved action into an Appium action.

    Returns None when the action cannot safely be represented
    by the current Appium model.
    """

    appium_action_type = (
        _convert_action_type(
            action.action
        )
    )

    if appium_action_type is None:
        return None

    locator = None

    if action.locator_resolution:
        if (
            action.locator_resolution.found
            and action.locator_resolution.locator
        ):
            locator = (
                _convert_locator_to_appium(
                    action.locator_resolution.locator
                )
            )

    value = None

    if action.value_reference:
        value = (
            action.value_reference
        )

    return AppiumAction(
        step_number=action.step_number,
        action=appium_action_type,
        target=action.business_target,
        locator=locator,
        value=value,
        description=(
            action.expected_result
            or ""
        ),
    )


# ============================================================
# RESOLVED ASSERTION -> APPIUM ASSERTION
# ============================================================


def _convert_resolved_assertion(
    assertion: ResolvedAssertion,
) -> AppiumAssertion | None:
    """
    Convert a generic resolved assertion into an Appium
    assertion.
    """

    assertion_type = (
        assertion.assertion_type
    )

    if (
        assertion_type
        != ActionType.ASSERT_VISIBLE
    ):
        return None

    locator = None

    if assertion.locator_resolution:

        if (
            assertion.locator_resolution.found
            and assertion.locator_resolution.locator
        ):
            locator = (
                _convert_locator_to_appium(
                    assertion.locator_resolution.locator
                )
            )

    return AppiumAssertion(
        assertion_type=(
            AppiumActionType.ASSERT_VISIBLE
        ),
        target=assertion.business_target,
        locator=locator,
        expected_value=None,
        description=(
            assertion.description
            or assertion.source_expected_result
            or ""
        ),
    )


# ============================================================
# RESOLVED PLAN -> APPIUM PLAN
# ============================================================


def _adapt_to_appium_plan(
    plan: ResolvedAutomationPlan,
    *,
    appium_platform: str = "android",
    device_name: str = "Android Emulator",
    app_package: str = "com.example.app",
    app_activity: str = ".MainActivity",
    app_path: str | None = None,
    bundle_id: str | None = None,
    platform_version: str | None = None,
    appium_server_url: str = (
        "http://127.0.0.1:4723"
    ),
) -> AppiumAutomationPlan:
    """
    Adapt the generic resolved plan to the mobile-specific
    Appium plan model.
    """

    config = _create_default_appium_config(
        platform=appium_platform,
        device_name=device_name,
        app_package=app_package,
        app_activity=app_activity,
        app_path=app_path,
        bundle_id=bundle_id,
        platform_version=platform_version,
        appium_server_url=appium_server_url,
    )

    actions = []

    for action in plan.actions:

        converted = (
            _convert_resolved_action(
                action
            )
        )

        if converted is not None:
            actions.append(
                converted
            )

    assertions = []

    for assertion in plan.assertions:

        converted = (
            _convert_resolved_assertion(
                assertion
            )
        )

        if converted is not None:
            assertions.append(
                converted
            )

    if not actions:
        raise ValueError(
            "The resolved automation plan contains no "
            "Appium-compatible actions."
        )

    if not assertions:
        raise ValueError(
            "The resolved automation plan contains no "
            "Appium-compatible assertions."
        )

    return AppiumAutomationPlan(
        test_case_id=plan.test_case_id,
        title=plan.title,
        config=config,
        actions=actions,
        assertions=assertions,
    )


# ============================================================
# GENERATE AUTOMATION
# ============================================================


def generate_automation(
    framework: AutomationFramework,
    language: AutomationLanguage,
    plan: ResolvedAutomationPlan,
    *,
    appium_platform: str = "android",
    device_name: str = "Android Emulator",
    app_package: str = "com.example.app",
    app_activity: str = ".MainActivity",
    app_path: str | None = None,
    bundle_id: str | None = None,
    platform_version: str | None = None,
    appium_server_url: str = (
        "http://127.0.0.1:4723"
    ),
) -> AutomationGenerationResult:
    """
    Main central automation-generation entry point.

    Web frameworks receive the ResolvedAutomationPlan
    directly.

    Appium receives an adapted AppiumAutomationPlan.
    """

    if plan is None:
        raise ValueError(
            "Resolved automation plan cannot be None."
        )

    generator = get_generator(
        framework,
        language,
    )

    # --------------------------------------------------------
    # APPIUM
    # --------------------------------------------------------

    if framework == AutomationFramework.APPIUM:

        if isinstance(plan, AppiumAutomationPlan):
            appium_plan = plan
        else:
            appium_plan = (
                _adapt_to_appium_plan(
                    plan,
                    appium_platform=appium_platform,
                    device_name=device_name,
                    app_package=app_package,
                    app_activity=app_activity,
                    app_path=app_path,
                    bundle_id=bundle_id,
                    platform_version=platform_version,
                    appium_server_url=appium_server_url,
                )
            )

        code = generator(
            appium_plan
        )

    # --------------------------------------------------------
    # WEB FRAMEWORKS
    # --------------------------------------------------------

    else:

        code = generator(
            plan
        )

    if not code or not code.strip():
        raise ValueError(
            "Automation generator returned empty code for "
            f"{framework.value} + {language.value}."
        )

    return AutomationGenerationResult(
        framework=framework,
        language=language,
        code=code,
        generator_name=generator.__name__,
    )


# ============================================================
# GENERATE CODE ONLY
# ============================================================


def generate_automation_code(
    framework: AutomationFramework,
    language: AutomationLanguage,
    plan: ResolvedAutomationPlan,
    **kwargs,
) -> str:
    """
    Generate automation source code only.
    """

    result = generate_automation(
        framework=framework,
        language=language,
        plan=plan,
        **kwargs,
    )

    return result.code


# ============================================================
# HELPERS
# ============================================================


def _xpath_literal(
    value: str,
) -> str:
    """
    Safely represent a string inside an XPath expression.
    """

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