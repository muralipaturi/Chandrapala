"""
TestPilot AI - Automation Service

Stage 2.x
---------
Central automation-generation orchestration layer.

Responsibilities:
    1. Normalize incoming test cases.
    2. Validate framework/language combinations.
    3. Build an automation plan.
    4. Inspect the target application for web automation.
    5. Resolve business targets to real UI locators.
    6. Route generation through automation_generator_dispatcher.
    7. Build AppiumAutomationPlan for mobile automation.

Supported combinations:
    Selenium    + Python
    Selenium    + Java
    Selenium    + JavaScript

    Playwright  + Python
    Playwright  + Java
    Playwright  + JavaScript

    Appium      + Python
    Appium      + Java
    Appium      + JavaScript

    Cypress     + JavaScript
"""

from __future__ import annotations

import json
import re
from typing import Any

# ============================================================
# PROJECT IMPORTS
# ============================================================

from automation_models import (
    ActionType,
    AutomationFramework,
    AutomationLanguage,
    Locator,
    LocatorStrategy,
)

from locator_resolver import (
    LocatorResolution,
    is_valid_ui_target,
)

from automation_planner import (
    AutomationPlan,
    PlannedAction,
    PlannedAssertion,
)

from automation_plan_resolver import (
    resolve_automation_plan,
    ResolvedAutomationPlan,
    ResolvedAction,
    ResolvedAssertion,
)

from automation_generator_dispatcher import (
    generate_automation as dispatch_automation,
)

from application_context import (
    inspect_application,
)

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
# PUBLIC API
# ============================================================


def generate_automation(
    test_case: Any,
    framework: str,
    language: str,
    base_url: str = "",
) -> dict[str, Any]:
    """
    Main automation-generation entry point.

    The FastAPI layer calls this function.

    Web:
        TestCase
          -> AutomationPlan
          -> ApplicationContext
          -> ResolvedAutomationPlan
          -> Dispatcher
          -> Generator

    Mobile:
        TestCase
          -> AppiumAutomationPlan
          -> Dispatcher
          -> Appium Generator
    """

    framework_value = normalize_framework(framework)
    language_value = normalize_language(language)

    test_case_data = normalize_test_case(test_case)

    base_url = (
        str(base_url or "").strip()
        or "http://localhost"
    )

    # --------------------------------------------------------
    # Validate framework/language
    # --------------------------------------------------------

    validate_framework_language(
        framework_value,
        language_value,
    )

    # --------------------------------------------------------
    # Cypress
    # --------------------------------------------------------

    if framework_value == "cypress":
        return _generate_cypress(
            test_case_data,
            language_value,
            base_url,
        )

    # --------------------------------------------------------
    # Appium
    # --------------------------------------------------------

    if framework_value == "appium":
        return _generate_appium(
            test_case_data,
            language_value,
            base_url,
        )

    # --------------------------------------------------------
    # Selenium / Playwright
    # --------------------------------------------------------

    if framework_value in {
        "selenium",
        "playwright",
    }:
        return _generate_web_automation(
            test_case_data,
            framework_value,
            language_value,
            base_url,
        )

    raise ValueError(
        f"Unsupported framework: {framework_value}"
    )


# ============================================================
# FRAMEWORK / LANGUAGE VALIDATION
# ============================================================


def validate_framework_language(
    framework: str,
    language: str,
) -> None:
    """
    Explicitly validate supported combinations.

    This keeps invalid routes from reaching generators.
    """

    supported = {
        "selenium": {
            "python",
            "java",
            "javascript",
        },
        "playwright": {
            "python",
            "java",
            "javascript",
        },
        "appium": {
            "python",
            "java",
            "javascript",
        },
        "cypress": {
            "javascript",
        },
    }

    if framework not in supported:
        raise ValueError(
            f"Unsupported framework: {framework}"
        )

    if language not in supported[framework]:
        raise ValueError(
            f"{framework} does not support "
            f"{language} in this generator."
        )


# ============================================================
# HEURISTIC FALLBACK RESOLUTION
# ============================================================


def clean_business_target(target: str) -> str:
    """
    Strips test data values, verb prefixes, and extraneous phrases from business target names
    so locator resolution only matches true UI element names.
    """
    if not target:
        return "page"
    t = target.strip()

    # Strip precondition prefix if present
    t = re.sub(r"^PRECONDITION:\s*", "", t, flags=re.I).strip()

    # Strip trailing data value expressions like 'with RX-2026-8812', 'as test@example.com', 'to 20'
    t = re.split(r"\s+\b(?:with|using|as|by)\b\s*[:=]?\s*|\s+\bto\b\s*[:=]\s*|\s+\bto\b\s+(?=\d|['\"])", t, maxsplit=1, flags=re.I)[0].strip()

    # Pattern: "Capture X from Y" -> "X"
    m_from = re.search(r"^(?:capture|extract|store|save|get)\s+(?:the\s+)?([a-z0-9_\s-]+?)\s+\b(?:from|in|into|on|for)\b", t, re.I)
    if m_from and len(m_from.group(1).strip()) >= 2:
        return re.sub(r"\s+(?:field|input|dropdown|box|form|label)$", "", m_from.group(1).strip(), flags=re.I).strip()

    # Extract UI target name from patterns like "patient details into Patient Details form"
    m_in = re.search(r"\b(?:in|into|for|on|to|from)\b\s+(?:the\s+)?([a-z0-9_\s-]+?)(?:\s+field|\s+input|\s+dropdown|\s+box|\s+form|\s+label)?$", t, re.I)
    if m_in and len(m_in.group(1).strip()) >= 2:
        extracted = m_in.group(1).strip()
        if not re.search(r"\b(enter|input|fill|select|type|click|verify|assert|into|in|from)\b", extracted, re.I):
            return re.sub(r"\s+(?:field|input|dropdown|box|form|label)$", "", extracted, flags=re.I).strip()

    # Don't alter short concise element names
    if len(t.split()) <= 3 and not re.search(r"\b(enter|click|verify|assert|fill|select|navigate|as|with|into|in|for|on|from|apply|update)\b", t, re.I):
        return re.sub(r"\s+(?:field|input|dropdown|box|form|label)$", "", t, flags=re.I).strip()

    # Strip verb/data prefix phrases e.g. "enter Admin in " or "patient details into "
    t_clean = re.sub(r"^(?:enter|input|select|fill|type|update|apply|modify|change|edit|click|verify|assert|capture|search|patient\s+details)\s+.*?\s+\b(?:in|into|to|for|on|as|from)\b\s+", "", t, flags=re.I).strip()
    if t_clean:
        t = t_clean

    # Strip starting action verbs & descriptive adjectives
    t = re.sub(r"^(?:enter|input|select|fill|type|update|apply|modify|change|edit|click|verify|assert|capture|search|open|goto|retry|execute|perform|run|review|inspect|observe)\s+", "", t, flags=re.I).strip()
    t = re.sub(r"^(?:updated|new|current)\s+", "", t, flags=re.I).strip()

    # Strip any leading prepositions
    t = re.sub(r"^\b(?:with|using|for|to|of|in|on|by|as|and|or)\b\s*", "", t, flags=re.I).strip()

    t = re.sub(r"\s+(?:field|input|dropdown|box|form|label|changes|detail|details|action)$", "", t, flags=re.I).strip()
    return t or target


def is_technical_environment_phrase(text: str) -> bool:
    """
    Returns True for non-UI technical environment phrases (e.g. 'Restore network connectivity').
    """
    low = str(text or "").lower().strip()
    return any(p in low for p in [
        "network connectivity", "network connection", "internet connection",
        "offline mode", "online mode", "server running", "database initialized",
        "environment deployed", "system environment", "code build"
    ])


def expand_compound_steps(steps: list[str]) -> list[str]:
    """
    Expands compound requirement steps (e.g. 'Execute search and review returned list')
    into individual actionable steps so each action targets a clear UI element.
    """
    expanded: list[str] = []
    for step in steps:
        s = str(step).strip()
        if not s:
            continue
        # Don't split buttons or links containing 'and' e.g. 'Click Dispense and Update Inventory button'
        if re.search(r"\b(?:button|link)\s*$", s, re.I):
            expanded.append(s)
            continue
        if re.search(r"\b\s+and\s+(?:save|click|submit|confirm|enter|fill|select|type|update|apply|retry|resend|reload|refresh|execute|perform|run|review|verify|assert|check|inspect|observe|view)\b", s, re.I):
            parts = re.split(r"\b\s+and\s+(?=(?:save|click|submit|confirm|enter|fill|select|type|update|apply|retry|resend|reload|refresh|execute|perform|run|review|verify|assert|check|inspect|observe|view)\b)", s, flags=re.I)
            for p in parts:
                if p.strip():
                    expanded.append(p.strip())
        else:
            expanded.append(s)
    return expanded


def build_heuristic_fallback_resolution(target: str) -> LocatorResolution:
    """
    Creates a safe heuristic fallback LocatorResolution for targets that could not be
    located directly via static DOM inspection.
    """
    raw_target = (target or "").strip()
    clean_target = clean_business_target(raw_target)

    if not is_valid_ui_target(clean_target):
        return LocatorResolution(
            target=clean_target,
            found=False,
            reason="Not a valid UI element target for locator resolution."
        )

    target_lower = clean_target.lower()
    target_key = re.sub(r"[^a-z0-9]", "", target_lower)

    if any(k in target_key for k in ["firstname", "fname", "patientname"]) or any(k in target_lower for k in ["first name", "first_name", "fname", "patient name", "patient_name"]):
        best_locator = Locator(
            strategy=LocatorStrategy.ID,
            value="firstName",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.NAME, value="firstName"),
            Locator(strategy=LocatorStrategy.XPATH, value="//label[normalize-space()='First Name']/following-sibling::input[1]"),
            Locator(strategy=LocatorStrategy.LABEL, value="First Name"),
            Locator(strategy=LocatorStrategy.PLACEHOLDER, value="First Name"),
        ]
    elif any(k in target_key for k in ["lastname", "lname", "surname"]) or any(k in target_lower for k in ["last name", "last_name", "lname", "surname"]):
        best_locator = Locator(
            strategy=LocatorStrategy.ID,
            value="lastName",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.NAME, value="lastName"),
            Locator(strategy=LocatorStrategy.XPATH, value="//label[normalize-space()='Last Name']/following-sibling::input[1]"),
            Locator(strategy=LocatorStrategy.LABEL, value="Last Name"),
            Locator(strategy=LocatorStrategy.PLACEHOLDER, value="Last Name"),
        ]
    elif any(k in target_lower for k in ["dob", "date of birth", "birth date", "birthdate"]):
        best_locator = Locator(
            strategy=LocatorStrategy.ID,
            value="dob",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.NAME, value="dob"),
            Locator(strategy=LocatorStrategy.XPATH, value="//label[normalize-space()='Date of Birth']/following-sibling::input[1]"),
            Locator(strategy=LocatorStrategy.LABEL, value="Date of Birth"),
        ]
    elif any(k in target_lower for k in ["gender", "sex"]):
        best_locator = Locator(
            strategy=LocatorStrategy.ID,
            value="gender",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.NAME, value="gender"),
            Locator(strategy=LocatorStrategy.XPATH, value="//label[normalize-space()='Gender']/following-sibling::select[1]"),
            Locator(strategy=LocatorStrategy.LABEL, value="Gender"),
        ]
    elif any(k in target_lower for k in ["phone", "mobile", "contact number"]):
        best_locator = Locator(
            strategy=LocatorStrategy.ID,
            value="phone",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.NAME, value="phone"),
            Locator(strategy=LocatorStrategy.LABEL, value="Phone"),
        ]
    elif any(k in target_lower for k in ["email", "e-mail"]):
        best_locator = Locator(
            strategy=LocatorStrategy.ID,
            value="email",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.NAME, value="email"),
            Locator(strategy=LocatorStrategy.LABEL, value="Email"),
        ]
    elif any(k in target_lower for k in ["address", "street"]):
        best_locator = Locator(
            strategy=LocatorStrategy.ID,
            value="address",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.NAME, value="address"),
            Locator(strategy=LocatorStrategy.LABEL, value="Address"),
        ]
    elif "username" in target_lower or "user name" in target_lower or "user" in target_lower:
        best_locator = Locator(
            strategy=LocatorStrategy.PLACEHOLDER,
            value="Username",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.NAME, value="username"),
            Locator(strategy=LocatorStrategy.CSS, value="input[name='username']"),
        ]
    elif "password" in target_lower or "pass" in target_lower:
        best_locator = Locator(
            strategy=LocatorStrategy.PLACEHOLDER,
            value="Password",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.NAME, value="password"),
            Locator(strategy=LocatorStrategy.CSS, value="input[type='password']"),
        ]
    elif any(k in target_lower for k in ["uhid", "patient identifier"]):
        best_locator = Locator(
            strategy=LocatorStrategy.LABEL,
            value="UHID",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.PLACEHOLDER, value="Enter UHID"),
            Locator(strategy=LocatorStrategy.NAME, value="uhid"),
        ]
    elif any(k in target_lower for k in ["doctor", "physician", "surgeon"]):
        best_locator = Locator(
            strategy=LocatorStrategy.LABEL,
            value="Doctor",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.ROLE, value="combobox", name="Doctor"),
            Locator(strategy=LocatorStrategy.NAME, value="doctor_id"),
        ]
    elif any(k in target_lower for k in ["department", "specialty"]):
        best_locator = Locator(
            strategy=LocatorStrategy.LABEL,
            value="Department",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.ROLE, value="combobox", name="Department"),
            Locator(strategy=LocatorStrategy.NAME, value="department"),
        ]
    elif any(k in target_lower for k in ["ward", "room", "bed"]):
        name = "Bed" if "bed" in target_lower else ("Room" if "room" in target_lower else "Ward")
        best_locator = Locator(
            strategy=LocatorStrategy.LABEL,
            value=name,
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.ROLE, value="combobox", name=name),
            Locator(strategy=LocatorStrategy.NAME, value=name.lower()),
        ]
    elif any(k in target_lower for k in ["barcode", "sample", "specimen"]):
        best_locator = Locator(
            strategy=LocatorStrategy.PLACEHOLDER,
            value="Scan Specimen Barcode",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.LABEL, value="Barcode"),
            Locator(strategy=LocatorStrategy.NAME, value="barcode"),
        ]
    elif any(k in target_lower for k in ["diagnosis", "icd", "chief complaint"]):
        best_locator = Locator(
            strategy=LocatorStrategy.LABEL,
            value=clean_target.title(),
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.PLACEHOLDER, value=clean_target.title()),
            Locator(strategy=LocatorStrategy.ROLE, value="textbox", name=clean_target.title()),
        ]
    elif any(k in target_lower for k in ["medicine", "batch", "dosage", "prescription", "rx"]):
        best_locator = Locator(
            strategy=LocatorStrategy.LABEL,
            value=clean_target.title(),
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.PLACEHOLDER, value=clean_target.title()),
            Locator(strategy=LocatorStrategy.NAME, value=clean_target.lower().replace(" ", "_")),
        ]
    elif any(k in target_lower for k in ["status", "appointment status", "bed status", "triage", "acuity"]):
        name = "Triage Category" if any(k in target_lower for k in ["triage", "acuity"]) else "Status"
        best_locator = Locator(
            strategy=LocatorStrategy.LABEL,
            value=name,
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.NAME, value=name.lower().replace(" ", "_")),
            Locator(strategy=LocatorStrategy.CSS, value=f"select[name='{name.lower().replace(' ', '_')}']"),
        ]
    elif any(k in target_lower for k in ["login", "submit", "sign in", "signin", "log in"]):
        btn_text = "Login" if ("login" in target_lower or "log in" in target_lower) else "Submit"
        best_locator = Locator(
            strategy=LocatorStrategy.ROLE,
            value="button",
            name=btn_text,
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.TEXT, value=btn_text),
            Locator(strategy=LocatorStrategy.CSS, value="button[type='submit']"),
        ]
    elif any(k in target_lower for k in ["save", "confirm", "submit", "register", "dispense", "button", "retry", "resend", "reload", "refresh", "admit", "discharge", "finalize", "pay"]):
        if "register" in target_lower and "patient" in target_lower:
            btn_name = "Register Patient"
        elif "dispense" in target_lower:
            btn_name = "Dispense"
        elif "admit" in target_lower:
            btn_name = "Admit"
        elif "discharge" in target_lower:
            btn_name = "Discharge"
        elif "pay" in target_lower:
            btn_name = "Pay"
        elif "retry" in target_lower:
            btn_name = "Retry"
        elif "register" in target_lower:
            btn_name = "Register"
        elif "save" in target_lower:
            btn_name = "Save"
        elif "confirm" in target_lower:
            btn_name = "Confirm"
        else:
            btn_name = clean_target.title()

        best_locator = Locator(
            strategy=LocatorStrategy.ROLE,
            value="button",
            name=btn_name,
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.TEXT, value=btn_name),
            Locator(strategy=LocatorStrategy.XPATH, value=f"//button[normalize-space()='{btn_name}']"),
        ]
    elif any(k in target_lower for k in ["link", "section", "menu", "tab", "registration", "patient registration", "appointment", "emr", "pharmacy", "laboratory", "billing", "patients"]):
        if ("patient" in target_lower or "patients" in target_lower) and "registration" not in target_lower:
            link_name = "Patients"
        elif "patient" in target_lower and "registration" in target_lower:
            link_name = "Patient Registration"
        else:
            link_name = clean_target.title()
        best_locator = Locator(
            strategy=LocatorStrategy.ROLE,
            value="link",
            name=link_name,
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.TEXT, value=link_name),
            Locator(strategy=LocatorStrategy.CSS, value=f"a[href*='{link_name.lower().replace(' ', '')}']"),
        ]
    elif any(k in target_lower for k in ["created", "generated", "scheduled", "success", "id", "patient id", "receipt", "alert", "token"]):
        best_locator = Locator(
            strategy=LocatorStrategy.TEXT,
            value=clean_target.title(),
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [best_locator, Locator(strategy=LocatorStrategy.LABEL, value=clean_target.title())]
    elif "search" in target_lower:
        best_locator = Locator(
            strategy=LocatorStrategy.PLACEHOLDER,
            value="Search",
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.ROLE, value="searchbox"),
            Locator(strategy=LocatorStrategy.CSS, value="input[type='search'], input[name*='search']"),
        ]
    else:
        best_locator = Locator(
            strategy=LocatorStrategy.LABEL,
            value=clean_target.title(),
            description=f"Fallback locator for {clean_target}"
        )
        candidates = [
            best_locator,
            Locator(strategy=LocatorStrategy.PLACEHOLDER, value=clean_target.title()),
            Locator(strategy=LocatorStrategy.NAME, value=clean_target.lower().replace(" ", "_")),
            Locator(strategy=LocatorStrategy.TEXT, value=clean_target),
        ]

    return LocatorResolution(
        target=clean_target,
        found=True,
        locator=best_locator,
        confidence=0.50,
        candidates=candidates,
        reason="Resolved using safe heuristic fallback."
    )


def ensure_plan_resolved(resolved_plan: ResolvedAutomationPlan) -> ResolvedAutomationPlan:
    """
    Ensures that every action and assertion in resolved_plan has a valid locator resolution,
    using heuristic fallback locators when live DOM inspection could not match elements.
    Synthesizes a default action and assertion if the test plan is missing either.
    """
    if not resolved_plan.actions:
        fallback_action = ResolvedAction(
            step_number=1,
            action=ActionType.NAVIGATE,
            business_target=resolved_plan.application_url or "http://localhost",
            value_reference=resolved_plan.application_url or "http://localhost",
            locator_resolution=build_heuristic_fallback_resolution("page"),
        )
        resolved_plan.actions.append(fallback_action)

    for action in resolved_plan.actions:
        if action.action == ActionType.NAVIGATE:
            continue
        if action.business_target and is_valid_ui_target(action.business_target):
            if (
                action.locator_resolution is None
                or not action.locator_resolution.found
                or action.locator_resolution.locator is None
            ):
                fallback = build_heuristic_fallback_resolution(action.business_target)
                if fallback.found:
                    action.locator_resolution = fallback
                else:
                    action.locator_resolution = LocatorResolution(
                        target=action.business_target,
                        found=False,
                        locator=None,
                        reason="Target not present in inspected application UI context."
                    )

    for assertion in resolved_plan.assertions:
        if assertion.assertion_type == ActionType.ASSERT_URL:
            continue
        if assertion.business_target and is_valid_ui_target(assertion.business_target):
            if (
                assertion.locator_resolution is None
                or not assertion.locator_resolution.found
                or assertion.locator_resolution.locator is None
            ):
                fallback = build_heuristic_fallback_resolution(assertion.business_target)
                if fallback.found:
                    assertion.locator_resolution = fallback
                else:
                    assertion.locator_resolution = LocatorResolution(
                        target=assertion.business_target,
                        found=False,
                        locator=None,
                        reason="Target not present in inspected application UI context."
                    )

    if not resolved_plan.assertions:
        exp_target = "page"
        if resolved_plan.actions:
            last_act = resolved_plan.actions[-1]
            if last_act.business_target and is_valid_ui_target(last_act.business_target):
                exp_target = last_act.business_target

        fallback_res = build_heuristic_fallback_resolution(exp_target)
        fallback_assertion = ResolvedAssertion(
            assertion_type=ActionType.ASSERT_VISIBLE,
            business_target=exp_target,
            description=f"Verify visibility of {exp_target}",
            locator_resolution=fallback_res if fallback_res.found else LocatorResolution(target=exp_target, found=False, locator=None),
        )
        resolved_plan.assertions.append(fallback_assertion)

    # Clean unresolved_targets for any target successfully resolved by fallbacks
    resolved_plan.unresolved_targets = [
        t for t in resolved_plan.unresolved_targets
        if not any(
            (a.business_target == t and a.locator_resolution and a.locator_resolution.found)
            for a in resolved_plan.actions
        ) and not any(
            (ass.business_target == t and ass.locator_resolution and ass.locator_resolution.found)
            for ass in resolved_plan.assertions
        )
    ]

    return resolved_plan


# ============================================================
# WEB AUTOMATION & VALIDATION
# ============================================================


def validate_automation_plan(plan: Any) -> None:
    """
    Pre-generation validation pass.
    Verifies target/data/assertion separation and rejects:
    1. Expected results or prose sentences converted into UI locators
    2. Non-UI system operations attempting fake UI locator resolution
    3. Duplicated action steps
    """
    actions = getattr(plan, "actions", [])
    assertions = getattr(plan, "assertions", [])
    seen = set()

    for action in actions:
        target = getattr(action, "business_target", None) or getattr(action, "target", None)
        act_type = getattr(action, "action", None)

        if target and not is_valid_ui_target(target):
            # Attempt to clean target if it has prepositions/values
            cleaned = clean_business_target(target)
            if cleaned and is_valid_ui_target(cleaned):
                if hasattr(action, "business_target"):
                    action.business_target = cleaned
                if hasattr(action, "target"):
                    action.target = cleaned
                target = cleaned
            elif str(act_type) not in ("ActionType.NAVIGATE", "ActionType.RECEIVE_OTP", "ActionType.EXTRACT_VALUE", "ActionType.WAIT", "AppiumActionType.RECEIVE_OTP", "AppiumActionType.WAIT"):
                raise ValueError(
                    f"Invalid UI target '{target}' in action step {getattr(action, 'step_number', 1)}. "
                    "Expected results and natural language prose cannot be converted into UI element locators."
                )

        sig = (getattr(action, "step_number", 0), str(act_type), str(target or "").lower())
        if sig in seen and getattr(action, "step_number", 0) > 0:
            raise ValueError(f"Duplicate action detected at step {action.step_number}: {act_type} on {target}")
        seen.add(sig)


def _generate_web_automation(
    tc: dict[str, Any],
    framework: str,
    language: str,
    base_url: str,
) -> dict[str, Any]:

    context = inspect_application(
        base_url
    )

    plan = build_automation_plan(
        tc,
        framework=framework,
        language=language,
        base_url=base_url,
    )

    resolved_plan = resolve_automation_plan(
        plan,
        context,
    )

    resolved_plan = ensure_plan_resolved(resolved_plan)

    # Pre-generation validation pass
    validate_automation_plan(resolved_plan)

    framework_enum = AutomationFramework(
        framework
    )

    language_enum = AutomationLanguage(
        language
    )

    result = dispatch_automation(
        framework_enum,
        language_enum,
        resolved_plan,
    )

    return build_dispatch_response(
        result=result,
        tc=tc,
        framework=framework,
        language=language,
        base_url=base_url,
    )


# ============================================================
# CYPRESS
# ============================================================


def _generate_cypress(
    tc: dict[str, Any],
    language: str,
    base_url: str,
) -> dict[str, Any]:

    # Cypress is intentionally restricted to JavaScript.
    validate_framework_language(
        "cypress",
        language,
    )

    plan = build_automation_plan(
        tc,
        framework="cypress",
        language="javascript",
        base_url=base_url,
    )

    # Cypress is web-based, therefore inspect the UI
    # before resolving locators.
    context = inspect_application(
        base_url
    )

    resolved_plan = resolve_automation_plan(
        plan,
        context,
    )

    # Ensure plan is fully resolved using heuristic fallbacks if needed
    resolved_plan = ensure_plan_resolved(resolved_plan)

    result = dispatch_automation(
        AutomationFramework.CYPRESS,
        AutomationLanguage.JAVASCRIPT,
        resolved_plan,
    )

    return build_dispatch_response(
        result=result,
        tc=tc,
        framework="cypress",
        language="javascript",
        base_url=base_url,
    )


# ============================================================
# APPIUM
# ============================================================


def _generate_appium(
    tc: dict[str, Any],
    language: str,
    base_url: str,
) -> dict[str, Any]:

    validate_framework_language(
        "appium",
        language,
    )

    # --------------------------------------------------------
    # Build actual Appium configuration
    # --------------------------------------------------------

    config = build_appium_config(
        tc
    )

    # --------------------------------------------------------
    # Build Appium-specific plan
    #
    # IMPORTANT:
    # Do NOT pass ResolvedAutomationPlan here.
    #
    # Appium generators require:
    #     AppiumAutomationPlan.config
    # --------------------------------------------------------

    appium_plan = build_appium_plan(
        tc,
        config,
    )

    # --------------------------------------------------------
    # Dispatcher
    # --------------------------------------------------------

    result = dispatch_automation(
        AutomationFramework.APPIUM,
        AutomationLanguage(language),
        appium_plan,
    )

    return build_dispatch_response(
        result=result,
        tc=tc,
        framework="appium",
        language=language,
        base_url=base_url,
    )


# ============================================================
# BUILD WEB AUTOMATION PLAN
# ============================================================


def build_automation_plan(
    tc: dict[str, Any],
    framework: str,
    language: str,
    base_url: str,
) -> AutomationPlan:

    actions: list[PlannedAction] = []
    assertions: list[PlannedAssertion] = []

    workflow = expand_compound_steps(extract_workflow(tc))
    step_number = 1

    for raw_step in workflow:
        step = str(raw_step).strip()
        if not step:
            continue

        low = step.lower()

        # Technical environment / network state precondition (without explicit UI verb)
        if is_technical_environment_phrase(step) and not re.search(r"\b(click|tap|press|fill|enter|select|type|retry|resend|reload|refresh)\b", low):
            continue

        # Application launch / initial startup step (e.g. "Open app", "Open browser", "Launch application")
        # Every test generator already navigates to BASE_URL at test function start.
        if re.search(r"^(?:open|launch|start|visit)\s+(?:the\s+)?(?:app|application|browser|system|site|website|portal|url|base\s*url|page)$", low) or low in {
            "open app", "open the app", "open application", "launch app", "launch application", "open browser", "launch browser", "open website", "visit app"
        }:
            continue

        # LOGIN shortcut
        if is_login_step(step) or re.search(r"\blogin\s+as\b", low):
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.FILL,
                    business_target="Username",
                    value_reference=tc.get("username") or extract_test_data_value(tc.get("test_data", []), "username") or "test_username",
                    source_step=step_number,
                )
            )
            step_number += 1
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.FILL,
                    business_target="Password",
                    value_reference=tc.get("password") or extract_test_data_value(tc.get("test_data", []), "password") or "test_password",
                    source_step=step_number,
                )
            )
            step_number += 1
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.CLICK,
                    business_target="Login",
                    value_reference=None,
                    source_step=step_number,
                )
            )
            step_number += 1
            continue

        # CAPTURE / STORE DYNAMIC VALUE (e.g. Capture Patient ID)
        if re.search(r"\b(capture|extract|store|save|record|get)\s+.*?\s*(?:id|number|value|code|token)\b", low) or ("capture" in low and "id" in low):
            cap_target = extract_target(step) or "Patient ID"
            var_name = clean_business_target(cap_target).lower().replace(" ", "_") or "patient_id"
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.CAPTURE_TEXT,
                    business_target=cap_target,
                    value_reference=var_name,
                    variable_name=var_name,
                    source_step=step_number,
                )
            )
            step_number += 1
            continue

        # SEARCH (e.g. Search Patient ID)
        if re.search(r"\bsearch\b", low):
            target = "Search Patient ID" if "patient" in low else (extract_target(step) or "Search Input")
            val = extract_value(step)
            if not val and ("id" in low or "patient" in low):
                val = "patient_id"
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.FILL,
                    business_target=target,
                    value_reference=val or "patient_id",
                    source_step=step_number,
                )
            )
            step_number += 1
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.CLICK,
                    business_target="Search",
                    value_reference=None,
                    source_step=step_number,
                )
            )
            step_number += 1
            continue

        # NAVIGATE
        if re.search(r"\b(navigate|open|goto|go to|visit)\b", low):
            target = extract_target(step) or "Appointments"
            is_app_dest = (
                target.startswith(("http://", "https://"))
                or target.lower() in {"app", "application", "browser", "system", "url", "portal", "website", "site", "page", "base url"}
            )
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.NAVIGATE if is_app_dest else ActionType.CLICK,
                    business_target=target,
                    value_reference=base_url if is_app_dest and not target.startswith(("http://", "https://")) else (target if target.startswith(("http://", "https://")) else None),
                    source_step=step_number,
                )
            )
            step_number += 1
            continue

        # CLICK / TAP / PRESS / SAVE / CONFIRM / SUBMIT / REGISTER / RETRY / RESEND / RELOAD / REFRESH / EXECUTE / PERFORM / RUN
        if re.search(r"\b(click|tap|press|save|confirm|submit|register|retry|resend|reload|refresh|execute|perform|run)\b", low):
            target = "Search" if "search" in low else ("Retry" if "retry" in low else (extract_target(step) or ("Save Changes" if "save" in low or "changes" in low else ("Register" if "register" in low else "Submit"))))
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.CLICK,
                    business_target=target,
                    value_reference=None,
                    source_step=step_number,
                )
            )
            step_number += 1
            continue

        # Check if step is a form fill for details where test_data has specific field key/values
        target_name = extract_fill_target(step) or extract_target(step) or clean_business_target(step) or ""
        form_fill_match = (
            re.search(r"\b(fill|enter|input)\s+.*?(?:details|information|form)\b", low)
            or target_name.lower() in {"patient details", "patient details form", "details form", "registration form"}
        )
        test_data_list = tc.get("test_data", [])
        if form_fill_match and test_data_list:
            parsed_data = []
            for item in test_data_list:
                if isinstance(item, str) and ":" in item:
                    k, v = item.split(":", 1)
                    parsed_data.append((k.strip(), v.strip()))
                elif isinstance(item, str) and "=" in item:
                    k, v = item.split("=", 1)
                    parsed_data.append((k.strip(), v.strip()))
                elif isinstance(item, dict):
                    for k, v in item.items():
                        parsed_data.append((str(k).strip(), str(v).strip()))

            if len(parsed_data) > 1:
                for field_k, field_v in parsed_data:
                    act_type = ActionType.SELECT if any(w in field_k.lower() for w in ["gender", "sex", "department", "doctor", "status", "country", "state"]) else ActionType.FILL
                    actions.append(
                        PlannedAction(
                            step_number=step_number,
                            action=act_type,
                            business_target=field_k,
                            value_reference=field_v,
                            source_step=step_number,
                        )
                    )
                    step_number += 1
                continue

        # FILL / TYPE / ENTER / DATE / APPLY / UPDATE / MODIFY / EDIT / CHANGE
        if re.search(r"\b(fill|enter|type|input|set|date|apply|update|modify|change|edit)\b", low):
            target = extract_fill_target(step) or extract_target(step) or clean_business_target(step) or "input"
            val = extract_value(step) or extract_test_data_value(test_data_list, target)
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.FILL,
                    business_target=target,
                    value_reference=val,
                    source_step=step_number,
                )
            )
            step_number += 1
            continue

        # SELECT / CHOOSE / TIME / DROP DOWN
        if re.search(r"\b(select|choose|pick|option|dropdown|department|doctor|time|status)\b", low):
            target = extract_target(step) or "select"
            val = extract_value(step) or extract_test_data_value(test_data_list, target)
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.SELECT if "select" in low or "choose" in low or "department" in low or "doctor" in low or "status" in low else ActionType.FILL,
                    business_target=target,
                    value_reference=val or target,
                    source_step=step_number,
                )
            )
            step_number += 1
            continue

        # ASSERTION IN STEP (verify / review / inspect / observe / view)
        if re.search(r"\b(verify|assert|check|validate|confirm|review|inspect|observe|view)\b", low):
            target = extract_target(step) or clean_business_target(step) or "Success Message"
            assertions.append(
                PlannedAssertion(
                    assertion_type=ActionType.ASSERT_VISIBLE,
                    business_target=target,
                    description=step,
                    source_expected_result=step,
                )
            )
            continue

        # FALLBACK FOR ANY OTHER STEP
        target = clean_business_target(step)
        if is_valid_ui_target(target):
            actions.append(
                PlannedAction(
                    step_number=step_number,
                    action=ActionType.CLICK,
                    business_target=target,
                    value_reference=None,
                    source_step=step_number,
                )
            )
            step_number += 1

    # EXPECTED RESULTS PARSING
    raw_expected = tc.get("expected_result", "")
    if raw_expected:
        # Split expected results by newline, semicolon, bullet points, or period sentence boundaries
        expected_items = [
            item.strip(" -*.\t\r\n")
            for item in re.split(r"[\n;\u2022•]|\.\s+(?=[A-Z])", str(raw_expected))
            if item.strip(" -*.\t\r\n")
        ]

        for expected_item in expected_items:
            expected_target = clean_business_target(expected_item)
            if is_valid_ui_target(expected_target):
                is_nav = bool(re.search(r"\b(redirected|redirect|navigated|navigate|landed|lands)\b", expected_item, re.I))
                assertions.append(
                    PlannedAssertion(
                        assertion_type=ActionType.ASSERT_URL if is_nav else ActionType.ASSERT_VISIBLE,
                        business_target=expected_target,
                        description=expected_item,
                        source_expected_result=expected_item,
                    )
                )

    plan = AutomationPlan(
        test_case_id=tc.get("id", "TC001"),
        title=tc.get("title", "Test Case"),
        application_url=base_url,
        actions=actions,
        assertions=assertions,
    )
    return validate_plan_semantics(plan, tc)


def validate_plan_semantics(plan: AutomationPlan, tc: dict[str, Any]) -> AutomationPlan:
    """
    Enforces 1-to-1 semantic correctness between requirement steps and automation actions.
    Guarantees no requirement step is omitted or misclassified.
    """
    workflow = extract_workflow(tc)
    if not workflow:
        return plan

    covered_steps = {act.source_step for act in plan.actions if act.source_step is not None}

    for idx, raw_step in enumerate(workflow, 1):
        step_str = str(raw_step).strip()
        if not step_str:
            continue
        low = step_str.lower()

        if is_technical_environment_phrase(step_str) or re.search(r"^(?:open|launch|start|visit)\s+(?:the\s+)?(?:app|application|browser|system|site|website|portal|url|base\s*url|page)$", low) or low in {
            "open app", "open the app", "open application", "launch app", "launch application", "open browser", "launch browser", "open website", "visit app"
        }:
            continue

        if idx not in covered_steps:
            target = extract_target(step_str) or clean_business_target(step_str)
            if not is_valid_ui_target(target):
                continue
            val = extract_value(step_str)

            if re.search(r"\b(select|choose|pick)\b", low):
                act_type = ActionType.SELECT
            elif re.search(r"\b(fill|enter|type|input|set)\b", low):
                act_type = ActionType.FILL
            elif re.search(r"\b(navigate|open|goto|visit)\b", low):
                act_type = ActionType.NAVIGATE if target.startswith(("http://", "https://")) else ActionType.CLICK
            elif re.search(r"\b(verify|assert|check|validate|confirm)\b", low):
                plan.assertions.append(
                    PlannedAssertion(
                        assertion_type=ActionType.ASSERT_VISIBLE,
                        business_target=target,
                        description=step_str,
                        source_expected_result=step_str,
                    )
                )
                continue
            else:
                act_type = ActionType.CLICK

            plan.actions.append(
                PlannedAction(
                    step_number=len(plan.actions) + 1,
                    action=act_type,
                    business_target=target,
                    value_reference=val or (target if act_type == ActionType.SELECT else None),
                    source_step=idx,
                )
            )

    plan.actions.sort(key=lambda a: a.step_number)
    return plan


# ============================================================
# APPIUM CONFIGURATION
# ============================================================


def build_appium_config(
    tc: dict[str, Any],
) -> AppiumConfig:

    mobile = tc.get(
        "mobile_config",
        {}
    )

    if not isinstance(
        mobile,
        dict,
    ):
        mobile = {}

    platform = str(
        mobile.get(
            "platform",
            tc.get(
                "platform",
                "android",
            ),
        )
    ).lower()

    device_name = str(
        mobile.get(
            "device_name",
            "Android Emulator",
        )
    )

    app_package = mobile.get(
        "app_package"
    )

    app_activity = mobile.get(
        "app_activity"
    )

    app_path = mobile.get(
        "app_path"
    )

    bundle_id = mobile.get(
        "bundle_id"
    )

    platform_version = mobile.get(
        "platform_version"
    )

    server_url = str(
        mobile.get(
            "appium_server_url",
            "http://127.0.0.1:4723",
        )
    )

    # --------------------------------------------------------
    # Android
    # --------------------------------------------------------

    if platform == "android":

        return create_android_config(
            device_name=device_name,
            app_package=(
                app_package
                or "com.example.app"
            ),
            app_activity=(
                app_activity
                or ".MainActivity"
            ),
            app_path=app_path,
            platform_version=platform_version,
            appium_server_url=server_url,
        )

    # --------------------------------------------------------
    # iOS
    # --------------------------------------------------------

    if platform == "ios":

        return create_ios_config(
            device_name=(
                mobile.get(
                    "device_name",
                    "iPhone Simulator",
                )
            ),
            bundle_id=(
                bundle_id
                or "com.example.app"
            ),
            app_path=app_path,
            platform_version=platform_version,
            appium_server_url=server_url,
        )

    raise ValueError(
        "Unsupported Appium platform: "
        f"{platform}"
    )


# ============================================================
# APPIUM PLAN
# ============================================================


def build_appium_plan(
    tc: dict[str, Any],
    config: AppiumConfig,
) -> AppiumAutomationPlan:

    actions: list[AppiumAction] = []
    assertions: list[AppiumAssertion] = []

    workflow = extract_workflow(
        tc
    )

    step_number = 1

    for step in workflow:

        low = step.lower()

        # ----------------------------------------------------
        # GENERIC NON-UI / SYSTEM OPERATIONS (RECEIVE OTP / EXTRACT)
        # ----------------------------------------------------

        if re.search(r"\b(receive|read|fetch|get|extract)\b", low) and re.search(r"\b(otp|code|token|sms|notification|message)\b", low):

            actions.append(
                AppiumAction(
                    step_number=step_number,
                    action=AppiumActionType.RECEIVE_OTP,
                    target=None,
                    locator=None,
                    value="${EXTRACTED_OTP}",
                    source="notification_shade",
                    is_system_operation=True,
                    description="Generic system operation: Receive OTP from notification/SMS source",
                )
            )

            step_number += 1
            continue

        # ----------------------------------------------------
        # WAIT
        # ----------------------------------------------------

        if re.search(r"\b(wait|pause|delay|sleep)\b", low):

            actions.append(
                AppiumAction(
                    step_number=step_number,
                    action=AppiumActionType.WAIT,
                    target=None,
                    locator=None,
                    is_system_operation=True,
                    description="Wait for system state transition",
                )
            )

            step_number += 1
            continue

        # ----------------------------------------------------
        # CLICK
        # ----------------------------------------------------

        if re.search(
            r"\b(click|tap|press)\b",
            low,
        ):

            target = extract_target(
                step
            )

            if target and is_valid_ui_target(target):

                locator = mobile_locator_for_target(
                    tc,
                    target,
                )

                actions.append(
                    AppiumAction(
                        step_number=step_number,
                        action=AppiumActionType.CLICK,
                        target=target,
                        locator=locator,
                    )
                )

                step_number += 1

            continue

        # ----------------------------------------------------
        # FILL / ENTER
        # ----------------------------------------------------

        if re.search(
            r"\b(fill|enter|type|input|set)\b",
            low,
        ):

            target = extract_fill_target(
                step
            )

            value = extract_value(
                step
            )

            if target and is_valid_ui_target(target):

                actions.append(
                    AppiumAction(
                        step_number=step_number,
                        action=AppiumActionType.FILL,
                        target=target,
                        locator=mobile_locator_for_target(
                            tc,
                            target,
                        ),
                        value=value,
                    )
                )

                step_number += 1

            continue

        # ----------------------------------------------------
        # ASSERT / VERIFY
        # ----------------------------------------------------

        if re.search(
            r"\b(verify|assert|check|validate|confirm)\b",
            low,
        ):

            target = extract_target(
                step
            ) or clean_business_target(step)

            if target and is_valid_ui_target(target):

                assertions.append(
                    AppiumAssertion(
                        assertion_type=(
                            AppiumActionType.ASSERT_VISIBLE
                        ),
                        target=target,
                        locator=mobile_locator_for_target(
                            tc,
                            target,
                        ),
                        description=step,
                    )
                )

            continue

        # ----------------------------------------------------
        # FALLBACK ACTION FOR DESCRIPTIVE STEPS
        # ----------------------------------------------------

        fallback_target = clean_business_target(step) or extract_target(step)
        if fallback_target and is_valid_ui_target(fallback_target):
            actions.append(
                AppiumAction(
                    step_number=step_number,
                    action=AppiumActionType.CLICK,
                    target=fallback_target,
                    locator=mobile_locator_for_target(tc, fallback_target),
                )
            )
            step_number += 1

    if not actions:
        title_text = tc.get("title", "") or tc.get("requirement", "") or "Appium View"
        smart_target = clean_business_target(title_text) or "Appium View"
        actions.append(
            AppiumAction(
                step_number=1,
                action=AppiumActionType.CLICK,
                target=smart_target,
                locator=mobile_locator_for_target(tc, smart_target),
            )
        )

    if not assertions:
        raw_exp = tc.get("expected_result", "") or tc.get("title", "") or "Operation Success"
        exp_target = extract_target(raw_exp) or clean_business_target(raw_exp) or "Operation Success"
        assertions.append(
            AppiumAssertion(
                assertion_type=AppiumActionType.ASSERT_VISIBLE,
                target=exp_target,
                locator=mobile_locator_for_target(tc, exp_target),
                description=f"Verify {exp_target}",
            )
        )

    return AppiumAutomationPlan(
        test_case_id=tc.get("id", "TC001"),
        title=tc.get("title", "Appium Test Case"),
        config=config,
        actions=actions,
        assertions=assertions,
    )


# ============================================================
# MOBILE LOCATOR
# ============================================================


def mobile_locator_for_target(
    tc: dict[str, Any],
    target: str,
) -> AppiumLocator:

    selectors = tc.get(
        "selectors",
        {},
    )

    if not isinstance(
        selectors,
        dict,
    ):
        selectors = {}

    # --------------------------------------------------------
    # Direct selector
    # --------------------------------------------------------

    selector = (
        selectors.get(target)
        or selectors.get(
            normalize_selector_key(target)
        )
    )

    if selector:

        selector = str(
            selector
        ).strip()

        if selector.startswith(
            "accessibility_id="
        ):
            return AppiumLocator(
                strategy=(
                    AppiumLocatorStrategy
                    .ACCESSIBILITY_ID
                ),
                value=selector[
                    len("accessibility_id="):
                ],
            )

        if selector.startswith(
            "xpath="
        ):
            return AppiumLocator(
                strategy=(
                    AppiumLocatorStrategy
                    .XPATH
                ),
                value=selector[
                    len("xpath="):
                ],
            )

        if selector.startswith(
            "id="
        ):
            return AppiumLocator(
                strategy=(
                    AppiumLocatorStrategy.ID
                ),
                value=selector[
                    len("id="):
                ],
            )

        return AppiumLocator(
            strategy=(
                AppiumLocatorStrategy.ID
            ),
            value=selector,
        )

    # --------------------------------------------------------
    # Safe mobile fallback locator using accessibility_id
    # --------------------------------------------------------
    clean_target = clean_business_target(target)
    if clean_target and is_valid_ui_target(clean_target):
        target_id = re.sub(r"[^a-zA-Z0-9_]+", "_", clean_target.lower()).strip("_")
        return AppiumLocator(
            strategy=AppiumLocatorStrategy.ACCESSIBILITY_ID,
            value=target_id or "element",
        )

    return None


# ============================================================
# DISPATCH RESPONSE
# ============================================================


def build_dispatch_response(
    result: Any,
    tc: dict[str, Any],
    framework: str,
    language: str,
    base_url: str,
) -> dict[str, Any]:

    # GeneratorResult from dispatcher
    code = getattr(
        result,
        "code",
        None,
    )

    generator_name = getattr(
        result,
        "generator_name",
        None,
    )

    if code is None:

        if isinstance(
            result,
            dict,
        ):
            code = result.get(
                "code",
                "",
            )

            generator_name = result.get(
                "generator_name"
            )

        else:
            code = str(
                result
            )

    filename = build_filename(
        tc["id"],
        framework,
        language,
    )

    return {
        "code": code,
        "filename": filename,
        "framework": framework,
        "language": language,
        "test_case_id": tc["id"],
        "test_case_type": tc.get(
            "type",
            "functional",
        ),
        "base_url": base_url,
        "status": "success",
        "generator_name": generator_name,
        "automation_analysis": build_analysis(
            tc,
            framework,
            language,
        ),
    }


# ============================================================
# FILENAME
# ============================================================


def build_filename(
    test_case_id: str,
    framework: str,
    language: str,
) -> str:

    safe_id = safe_filename(
        test_case_id
    )

    if language == "java":

        return (
            f"Test"
            f"{pascal_case(safe_id)}"
            f".java"
        )

    if framework == "cypress":

        return (
            f"test_{safe_id}.cy.js"
        )

    if language == "javascript":

        return (
            f"test_{safe_id}.spec.js"
        )

    return (
        f"test_{safe_id}.py"
    )


# ============================================================
# TEST CASE NORMALIZATION
# ============================================================


def normalize_test_case(
    test_case: Any,
) -> dict[str, Any]:

    # Pydantic v2
    if hasattr(
        test_case,
        "model_dump",
    ) and callable(
        test_case.model_dump
    ):
        test_case = test_case.model_dump()

    # Pydantic v1
    elif hasattr(
        test_case,
        "dict",
    ) and callable(
        test_case.dict
    ):
        test_case = test_case.dict()

    # JSON string
    if isinstance(
        test_case,
        str,
    ):

        test_case = test_case.strip()

        if not test_case:
            raise ValueError(
                "test_case cannot be empty."
            )

        try:
            test_case = json.loads(
                test_case
            )

        except json.JSONDecodeError as exc:

            raise ValueError(
                "test_case contains invalid JSON."
            ) from exc

    # Nested test_case
    if (
        isinstance(
            test_case,
            dict,
        )
        and "test_case" in test_case
    ):

        nested = test_case.get(
            "test_case"
        )

        if isinstance(
            nested,
            str,
        ):

            try:
                nested = json.loads(
                    nested
                )

            except json.JSONDecodeError as exc:

                raise ValueError(
                    "Nested test_case contains invalid JSON."
                ) from exc

        if isinstance(
            nested,
            dict,
        ):
            test_case = nested

    if not isinstance(
        test_case,
        dict,
    ):
        raise ValueError(
            "test_case must be a JSON object."
        )

    test_id = (
        test_case.get("id")
        or test_case.get("test_case_id")
        or test_case.get("testCaseId")
        or "TC001"
    )

    title = (
        test_case.get("title")
        or test_case.get("name")
        or "Generated automation test"
    )

    test_type = (
        test_case.get("type")
        or "functional"
    )

    priority = (
        test_case.get("priority")
        or "Medium"
    )

    expected = (
        test_case.get("expected_result")
        or test_case.get("expected")
        or test_case.get("expectedResult")
        or ""
    )

    steps = (
        test_case.get("steps")
        or test_case.get("test_steps")
        or test_case.get("testSteps")
        or []
    )

    if isinstance(
        steps,
        str,
    ):

        steps = [
            x.strip()
            for x in steps.splitlines()
            if x.strip()
        ]

    if not isinstance(
        steps,
        list,
    ):
        steps = []

    preconditions = (
        test_case.get(
            "preconditions"
        )
        or []
    )

    if isinstance(
        preconditions,
        str,
    ):

        preconditions = [
            x.strip()
            for x in preconditions.splitlines()
            if x.strip()
        ]

    if not isinstance(
        preconditions,
        list,
    ):
        preconditions = []

    test_data = (
        test_case.get(
            "test_data"
        )
        or test_case.get(
            "testData"
        )
        or []
    )

    if isinstance(
        test_data,
        str,
    ):
        test_data = [
            test_data
        ]

    if not isinstance(
        test_data,
        list,
    ):
        test_data = []

    selectors = (
        test_case.get(
            "selectors"
        )
        or {}
    )

    if not isinstance(
        selectors,
        dict,
    ):
        selectors = {}

    actions = (
        test_case.get(
            "actions"
        )
        or []
    )

    if not isinstance(
        actions,
        list,
    ):
        actions = []

    username = (
        test_case.get(
            "username"
        )
        or extract_test_data_value(
            test_data,
            "username",
        )
        or "Admin"
    )

    password = (
        test_case.get(
            "password"
        )
        or extract_test_data_value(
            test_data,
            "password",
        )
        or "admin123"
    )

    return {
        "id": str(test_id),
        "type": str(test_type),
        "title": str(title),
        "priority": str(priority),
        "preconditions": [
            str(x)
            for x in preconditions
        ],
        "test_data": [
            str(x)
            for x in test_data
        ],
        "steps": [
            str(x)
            for x in steps
            if str(x).strip()
        ],
        "expected_result": str(
            expected
        ),
        "username": str(
            username
        ),
        "password": str(
            password
        ),
        "selectors": selectors,
        "actions": actions,

        # Preserve mobile configuration
        "mobile_config": test_case.get(
            "mobile_config",
            {},
        ),

        "platform": test_case.get(
            "platform",
            "android",
        ),
    }


# ============================================================
# WORKFLOW
# ============================================================


def extract_workflow(
    tc: dict[str, Any],
) -> list[str]:

    result: list[str] = []

    # Check if preconditions specify a user login role and no explicit login step exists in steps
    preconditions = tc.get("preconditions", [])
    has_explicit_login = any(is_login_step(str(s)) for s in tc.get("steps", []))

    if not has_explicit_login:
        for p in preconditions:
            p_str = str(p).strip().lower()
            if "logged in" in p_str or "authenticated" in p_str or re.search(r"\blogin\s+as\b", p_str):
                result.append(str(p).strip())
                break

    for value in tc.get(
        "steps",
        [],
    ):

        text = str(
            value
        ).strip()

        if text:
            result.append(
                text
            )

    for value in tc.get(
        "actions",
        [],
    ):

        if isinstance(
            value,
            dict,
        ):

            text = (
                value.get(
                    "description"
                )
                or value.get(
                    "step"
                )
                or value.get(
                    "action"
                )
                or ""
            )

        else:

            text = str(
                value
            )

        if str(
            text
        ).strip():

            result.append(
                str(text).strip()
            )

    return result


# ============================================================
# STEP PARSING
# ============================================================


def is_login_step(
    text: str,
) -> bool:
    """
    Detect a complete login/authentication workflow step.

    Must NOT match simple button actions or form mentions such as:
        Click Login button
        Enter OTP on Login form
        Request OTP dispatch on Login form
    """
    value = str(text or "").strip()

    if not value:
        return False

    low = value.lower()

    # Exclude simple element actions
    if re.search(r"^(?:click|tap|press|select|fill|enter|type|input|request|verify|assert)\b", low):
        return False

    # Match explicit full login workflow phrases only
    return bool(
        re.search(
            r"^(?:log\s*in|sign\s*in|authenticate)\s+(?:with|as|using)\b",
            low,
        )
        or re.search(
            r"^(?:login|log\s+in|sign\s+in|authenticate)\s+(?:with\s+valid\s+credentials|as\s+admin|user)\s*$",
            low,
        )
    )


def quoted_value(
    text: str,
) -> str | None:

    match = re.search(
        r"""["']([^"']+)["']""",
        text,
    )

    if match:
        return (
            match.group(1)
            .strip()
        )

    return None


def extract_target(
    text: str,
) -> str | None:
    """
    Extract a business target from action/assertion text.

    Supports common patterns such as:

        Click Login
            -> Login

        Verify Password field is visible
            -> Password field

        Password field is visible
            -> Password field

        Success message is displayed
            -> Success message

        User is redirected to dashboard
            -> dashboard

        User is navigated to dashboard
            -> dashboard

        Dashboard is displayed
            -> Dashboard
    """

    value = str(text or "").strip()

    if not value:
        return None

    # --------------------------------------------------------
    # Explicit quoted target
    # --------------------------------------------------------

    quoted = quoted_value(
        value
    )

    if quoted:
        return quoted

    # --------------------------------------------------------
    # CLICK / TAP / PRESS
    # --------------------------------------------------------

    patterns = [

        r"(?:click|tap|press)"
        r"\s+(?:on\s+)?(?:the\s+)?"
        r"(.+?)(?:\s+button|\s+link)?$",

        # ----------------------------------------------------
        # Explicit assertion verbs
        # ----------------------------------------------------

        r"(?:verify|check|assert|confirm|validate)"
        r"\s+(?:that\s+)?"
        r"(.+)$",

        # ----------------------------------------------------
        # Visibility / display assertions
        # ----------------------------------------------------

        r"(.+?)\s+is\s+"
        r"(?:visible|displayed|shown)$",

        # ----------------------------------------------------
        # Redirect / navigation assertions
        #
        # User is redirected to dashboard
        # User is navigated to dashboard
        # User is redirected to the dashboard
        # ----------------------------------------------------

        r"(?:user\s+)?"
        r"(?:is\s+)?"
        r"(?:redirected|navigated|taken|sent)"
        r"\s+(?:to|into)\s+"
        r"(?:the\s+)?"
        r"(.+)$",

        # ----------------------------------------------------
        # Generic "appears" / "exists" assertions
        # ----------------------------------------------------

        r"(.+?)\s+"
        r"(?:appears|exists|is\s+present)$",

        # ----------------------------------------------------
        # Page / screen navigation
        #
        # Page changes to dashboard
        # Screen changes to dashboard
        # ----------------------------------------------------

        r"(?:page|screen)"
        r"\s+(?:changes|navigates|moves)"
        r"\s+(?:to|into)\s+"
        r"(?:the\s+)?"
        r"(.+)$",

        # ----------------------------------------------------
        # SELECT / CHOOSE / PICK
        # ----------------------------------------------------
        r"^(?:select|choose|pick)\s+(?:the\s+)?(.+?)$",

        # ----------------------------------------------------
        # SEARCH / FIND / LOOKUP / QUERY
        # ----------------------------------------------------
        r"^(?:search|find|lookup|query)\s+(?:for\s+)?(?:the\s+)?(.+?)$",

        # ----------------------------------------------------
        # FILL / ENTER / TYPE / INPUT
        # ----------------------------------------------------
        r"^(?:enter|type|fill|input|set)\s+(?:the\s+)?(.+?)$",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            value,
            re.I,
        )

        if not match:
            continue

        target = (
            match.group(1)
            .strip(
                " .,:;"
            )
        )

        if not target:
            continue

        # ----------------------------------------------------
        # Remove trailing assertion wording.
        # ----------------------------------------------------

        target = re.sub(
            r"\s+(?:button|link)$",
            "",
            target,
            flags=re.I,
        ).strip()

        target = re.sub(
            r"\s+(?:is|was|has been)\s+"
            r"(?:visible|displayed|shown)$",
            "",
            target,
            flags=re.I,
        ).strip()

        if target:
            return clean_business_target(target)

    cleaned = clean_business_target(value)
    return cleaned if cleaned else value


def extract_fill_target(
    text: str,
) -> str | None:
    """
    Extract the business target from a fill/input step.

    Examples:
        Enter username
            -> username

        Enter password
            -> password

        Fill username
            -> username

        Type password
            -> password

        Enter username with Admin
            -> username

        Enter email as test@example.com
            -> email

        Fill the username field
            -> username

        Enter the password textbox
            -> password
    """

    value = str(text or "").strip()

    if not value:
        return None

    # Remove the action keyword.
    match = re.match(
        r"^(?:enter|type|fill|input|set)\b\s*(.+?)\s*$",
        value,
        re.I,
    )

    if not match:
        return None

    target = match.group(1).strip()

    if not target:
        return None

    # Handle preposition patterns like "patient details into Patient Details form"
    m_prep = re.search(r"\b(?:in|into|for|on|to)\b\s+(?:the\s+)?(.+?)$", target, re.I)
    if m_prep:
        target = m_prep.group(1).strip()

    # Remove explicit input value.
    #
    # Enter username with Admin
    # Enter email as test@example.com
    # Enter phone to 9876543210
    target = re.split(
        r"\s+\b(?:as|to|with)\b\s*[:=]?\s*",
        target,
        maxsplit=1,
        flags=re.I,
    )[0].strip()

    # Remove common field terminology.
    #
    # username field
    # password textbox
    # email input
    target = re.sub(
        r"\s+(?:field|textbox|input|box|element|form)$",
        "",
        target,
        flags=re.I,
    ).strip()

    # Remove leading "the".
    target = re.sub(
        r"^the\s+",
        "",
        target,
        flags=re.I,
    ).strip()

    # Remove punctuation.
    target = target.strip(
        " .,:;\"'"
    )

    if not target:
        return None

    # Normalize common field names.
    normalized_targets = {
        "user name": "username",
        "user-name": "username",
        "user_name": "username",
        "pass word": "password",
        "pass-word": "password",
        "pass_word": "password",
        "email address": "email",
        "phone number": "phone",
        "mobile number": "mobile",
    }

    return normalized_targets.get(
        target.lower(),
        target,
    )

def extract_value(
    text: str,
) -> str | None:
    """
    Extract an explicit input value from a test step.

    Examples:
        Enter username
            -> None
        Enter password
            -> None
        Enter username with Admin
            -> Admin
        Enter password with Admin@123
            -> Admin@123
        Enter email as test@example.com
            -> test@example.com
        Enter phone to 9876543210
            -> 9876543210
        Enter username with: Admin
            -> Admin

    A field name by itself is never treated as an input value.
    This prevents values such as "sword" from being extracted
    from the word "password".
    """

    value = str(text or "").strip()

    if not value:
        return None

    # Explicitly quoted values have the highest priority.
    quoted = quoted_value(value)

    if quoted:
        return quoted

    # Only accept an explicit value introduced by a real word
    # boundary: as / to / with.
    explicit_patterns = [
        r"\b(?:as|to|with)\b\s*[:=]?\s*(.+)$",
        r"\b(?:value|name|id|email|username|password)\b\s*[:=]\s*(.+)$",
    ]

    for pattern in explicit_patterns:
        match = re.search(
            pattern,
            value,
            re.I,
        )

        if not match:
            continue

        extracted = (
            match.group(1)
            .strip()
            .strip("\"'")
            .strip()
        )

        if not extracted:
            continue

        # Never return another field keyword as a value.
        if extracted.lower() in {
            "username",
            "password",
            "email",
            "name",
            "id",
            "value",
            "field",
            "textbox",
            "input",
        }:
            return None

        return extracted.rstrip(".")

    return None


# ============================================================
# TEST DATA
# ============================================================


def extract_test_data_value(
    test_data: Any,
    key: str,
) -> str | None:
    """
    Extract a test data value from test_data using smart key aliases and normalizations.
    Supports list of strings, dicts, and list of dicts.
    """
    if not test_data or not key:
        return None

    norm_key = re.sub(r"[^a-z0-9]", "", key.lower())

    alias_groups = [
        {"firstname", "first_name", "fname", "patientname", "patient_name", "name", "givenname", "given_name"},
        {"lastname", "last_name", "lname", "surname", "familyname", "family_name"},
        {"dob", "dateofbirth", "date_of_birth", "birthdate", "birth_date", "birth"},
        {"gender", "sex"},
        {"phone", "mobile", "contact", "telephone", "phonenumber", "phone_number", "contactnumber", "contact_number", "cell"},
        {"email", "emailaddress", "email_address", "mail"},
        {"username", "user", "user_name", "login_id", "loginid"},
        {"password", "pass", "pwd"},
        {"address", "street", "residential_address"},
        {"patientid", "patient_id", "uhid", "mrn", "id"},
        {"doctor", "doctor_id", "doctorname", "physician", "provider"},
        {"department", "dept", "specialty"},
        {"status", "appointment_status", "state"},
    ]

    target_aliases = {norm_key, key.lower(), key.lower().replace(" ", "_")}
    for group in alias_groups:
        group_norm = {re.sub(r"[^a-z0-9]", "", g) for g in group}
        if norm_key in group_norm or any(a in group for a in target_aliases):
            target_aliases.update(group)
            target_aliases.update(group_norm)

    def check_pair(k: str, v: Any) -> str | None:
        if v is None:
            return None
        k_str = str(k).strip()
        k_norm = re.sub(r"[^a-z0-9]", "", k_str.lower())
        if k_norm in target_aliases or k_str.lower() in target_aliases:
            val_str = str(v).strip().strip("\"'")
            if val_str:
                return val_str
        return None

    if isinstance(test_data, dict):
        for k, v in test_data.items():
            res = check_pair(k, v)
            if res:
                return res
        return None

    if isinstance(test_data, list):
        for item in test_data:
            if isinstance(item, dict):
                if "key" in item and "value" in item:
                    res = check_pair(item["key"], item["value"])
                    if res:
                        return res
                if "name" in item and "value" in item:
                    res = check_pair(item["name"], item["value"])
                    if res:
                        return res
                for k, v in item.items():
                    res = check_pair(k, v)
                    if res:
                        return res
            else:
                text = str(item).strip()
                m = re.match(r"^([^:=]+)\s*[:=]\s*(.*)$", text)
                if m:
                    res = check_pair(m.group(1), m.group(2))
                    if res:
                        return res
                for alias in target_aliases:
                    if len(alias) >= 2:
                        match = re.search(
                            rf"\b{re.escape(alias)}\b\s*[:=]\s*([^,;\n]+)",
                            text,
                            re.I,
                        )
                        if match:
                            return match.group(1).strip().strip("\"'")

    return None


# ============================================================
# SELECTOR HELPERS
# ============================================================


def normalize_selector_key(
    value: str,
) -> str:

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).lower(),
    ).strip("_")


# ============================================================
# ANALYSIS
# ============================================================


def build_analysis(
    tc: dict[str, Any],
    framework: str,
    language: str,
) -> dict[str, Any]:

    return {
        "test_case_id": tc["id"],
        "title": tc["title"],
        "framework": framework,
        "language": language,
        "steps_count": len(
            tc["steps"]
        ),
        "selectors_detected": bool(
            tc["selectors"]
        ),
        "actions_detected": bool(
            tc["actions"]
        ),
        "expected_result": tc[
            "expected_result"
        ],
        "editable": True,
        "architecture": (
            "automation_service -> "
            "planner -> resolver -> "
            "dispatcher -> generator"
        ),
    }


# ============================================================
# NORMALIZATION
# ============================================================


def normalize_framework(
    framework: str,
) -> str:

    value = str(
        framework or ""
    ).strip().lower()

    return {
        "pw": "playwright",
        "playwright-python": "playwright",
        "playwright-java": "playwright",
        "playwright-javascript": "playwright",

        "selenium-webdriver": "selenium",
        "selenium-python": "selenium",
        "selenium-java": "selenium",
        "selenium-javascript": "selenium",

        "appium-mobile": "appium",
        "appium-python": "appium",
        "appium-java": "appium",
        "appium-javascript": "appium",

        "cypress-js": "cypress",
        "cypress-javascript": "cypress",
    }.get(
        value,
        value,
    )


def normalize_language(
    language: str,
) -> str:

    value = str(
        language or ""
    ).strip().lower()

    return {
        "py": "python",
        "python3": "python",

        "java8": "java",
        "java11": "java",

        "js": "javascript",
        "node": "javascript",

        "ts": "typescript",
    }.get(
        value,
        value,
    )


# ============================================================
# FILE NAME HELPERS
# ============================================================


def snake_case(
    value: str,
) -> str:

    value = str(
        value or ""
    )

    value = re.sub(
        r"([a-z0-9])([A-Z])",
        r"\1_\2",
        value,
    )

    value = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        value,
    )

    value = re.sub(
        r"_+",
        "_",
        value,
    ).strip(
        "_"
    ).lower()

    if not value:
        value = "generated_test"

    if value[0].isdigit():
        value = "test_" + value

    return value


def pascal_case(
    value: str,
) -> str:

    words = re.findall(
        r"[A-Za-z0-9]+",
        str(value or ""),
    )

    if not words:
        return "GeneratedTest"

    return "".join(
        word[:1].upper()
        + word[1:]
        for word in words
    )


def safe_filename(
    value: str,
) -> str:

    return snake_case(
        value
    )


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================


def generate_automation_code(
    test_case: Any,
    framework: str,
    language: str,
    base_url: str = "",
) -> str:

    result = generate_automation(
        test_case=test_case,
        framework=framework,
        language=language,
        base_url=base_url,
    )

    return result["code"]
