"""
Stage 2.4 - Application/UI Context Extraction

Purpose:
    Inspect a web application's rendered UI and produce
    framework-independent UI evidence for the automation planner.

IMPORTANT:
    - This module does NOT generate automation code.
    - This module does NOT call Gemini.
    - This module does NOT modify Stage 1.
    - Playwright is used only as a browser inspection engine.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TIMEOUT_MS = 10_000
DEFAULT_MAX_ELEMENTS = 300
DEFAULT_MAX_TEXT_LENGTH = 200
CACHE_TTL_SECONDS = 300
_INSPECT_CACHE: Dict[str, tuple[float, ApplicationPageContext]] = {}


# ============================================================
# UI ELEMENT MODEL
# ============================================================

class UIElement(BaseModel):
    """
    Framework-independent representation of an actual
    rendered UI element.
    """

    model_config = ConfigDict(extra="forbid")

    tag: str

    role: Optional[str] = None

    text: Optional[str] = None

    label: Optional[str] = None

    aria_label: Optional[str] = None

    placeholder: Optional[str] = None

    element_id: Optional[str] = None

    name: Optional[str] = None

    test_id: Optional[str] = None

    href: Optional[str] = None

    input_type: Optional[str] = None

    visible: bool = False

    enabled: Optional[bool] = None

    locator_candidates: List[Dict[str, str]] = Field(
        default_factory=list
    )


# ============================================================
# PAGE CONTEXT MODEL
# ============================================================

class ApplicationPageContext(BaseModel):
    """
    Context extracted from one rendered web page.
    """

    model_config = ConfigDict(extra="forbid")

    requested_url: str

    final_url: str

    title: str

    page_text: str = ""

    elements: List[UIElement] = Field(
        default_factory=list
    )

    forms: List[Dict[str, Any]] = Field(
        default_factory=list
    )

    navigation_items: List[Dict[str, Any]] = Field(
        default_factory=list
    )

    screenshot_path: Optional[str] = None


# ============================================================
# EXTRACTOR
# ============================================================

class ApplicationContextExtractor:
    """
    Inspect a web application using Playwright.

    This class is intentionally framework-independent from the
    generated automation target.

    Example:

        extractor = ApplicationContextExtractor()

        context = extractor.inspect(
            "https://example.com"
        )

        print(context.model_dump_json(indent=2))
    """

    def __init__(
        self,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        max_elements: int = DEFAULT_MAX_ELEMENTS,
        headless: bool = True,
    ):
        self.timeout_ms = timeout_ms
        self.max_elements = max_elements
        self.headless = headless

    # ========================================================
    # PUBLIC API
    # ========================================================

    def inspect(
        self,
        url: str,
        screenshot_path: Optional[str] = None,
    ) -> ApplicationPageContext:
        """
        Open the supplied URL and inspect the rendered UI.
        """

        if not url or not url.strip():
            raise ValueError(
                "Application URL is required."
            )

        normalized_url = url.strip()

        self._validate_url(normalized_url)

        try:
            from playwright.sync_api import (
                sync_playwright,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed in the current "
                "virtual environment."
            ) from exc

        with sync_playwright() as playwright:

            browser = playwright.chromium.launch(
                headless=self.headless
            )

            context = browser.new_context(
                viewport={
                    "width": 1440,
                    "height": 900,
                }
            )

            page = context.new_page()

            page.set_default_timeout(
                self.timeout_ms
            )

            try:
                page.goto(
                    normalized_url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )

                # Allow the application to finish initial
                # client-side rendering without introducing
                # an arbitrary long sleep.
                try:
                    page.wait_for_load_state(
                        "networkidle",
                        timeout=5_000,
                    )
                except Exception:
                    # Some modern applications never become
                    # fully network idle. DOM content is still
                    # usable, so continue.
                    pass

                if screenshot_path:
                    page.screenshot(
                        path=screenshot_path,
                        full_page=True,
                    )

                result = self._extract_page(
                    page=page,
                    requested_url=normalized_url,
                    screenshot_path=screenshot_path,
                )

                # Follow internal same-origin navigation links (e.g. patients.html) to discover subpage elements
                try:
                    from urllib.parse import urljoin, urlparse
                    base_parts = urlparse(normalized_url)
                    base_origin = f"{base_parts.scheme}://{base_parts.netloc}"
                    visited_urls = {normalized_url.rstrip("/"), page.url.rstrip("/")}
                    for nav in result.navigation_items:
                        href = nav.get("href")
                        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                            continue
                        sub_url = urljoin(page.url, href)
                        norm_sub = sub_url.rstrip("/")
                        if norm_sub.startswith(base_origin) and norm_sub not in visited_urls:
                            visited_urls.add(norm_sub)
                            try:
                                sub_page = context.new_page()
                                sub_page.goto(sub_url, wait_until="domcontentloaded", timeout=4_000)
                                sub_elements = self._extract_elements(sub_page)
                                result.elements.extend(sub_elements)
                                sub_forms = self._extract_forms(sub_page)
                                result.forms.extend(sub_forms)
                                sub_page.close()
                            except Exception:
                                pass
                            if len(visited_urls) >= 4:
                                break
                except Exception:
                    pass
            except Exception:
                result = ApplicationPageContext(
                    requested_url=normalized_url,
                    final_url=normalized_url,
                    title="Unreachable Page",
                    page_text="",
                    elements=[],
                    forms=[],
                )
            finally:
                context.close()
                browser.close()

        return result

    # ========================================================
    # URL VALIDATION
    # ========================================================

    @staticmethod
    def _validate_url(url: str) -> None:

        if not re.match(
            r"^https?://",
            url,
            flags=re.IGNORECASE,
        ):
            raise ValueError(
                "Application URL must start with "
                "http:// or https://."
            )

    # ========================================================
    # PAGE EXTRACTION
    # ========================================================

    def _extract_page(
        self,
        page,
        requested_url: str,
        screenshot_path: Optional[str],
    ) -> ApplicationPageContext:

        page_text = self._extract_page_text(page)

        elements = self._extract_elements(page)

        forms = self._extract_forms(page)

        navigation_items = (
            self._extract_navigation_items(page)
        )

        return ApplicationPageContext(
            requested_url=requested_url,
            final_url=page.url,
            title=self._safe_page_title(page),
            page_text=page_text,
            elements=elements,
            forms=forms,
            navigation_items=navigation_items,
            screenshot_path=screenshot_path,
        )

    # ========================================================
    # PAGE TITLE
    # ========================================================

    @staticmethod
    def _safe_page_title(page) -> str:

        try:
            return (
                page.title().strip()
                if page.title()
                else ""
            )
        except Exception:
            return ""

    # ========================================================
    # PAGE TEXT
    # ========================================================

    def _extract_page_text(self, page) -> str:

        try:
            text = page.locator(
                "body"
            ).inner_text(
                timeout=self.timeout_ms
            )

            return self._clean_text(
                text,
                max_length=20_000,
            )

        except Exception:
            return ""

    # ========================================================
    # ELEMENT EXTRACTION
    # ========================================================

    def _extract_elements(self, page) -> List[UIElement]:

        selector = (
            "a,"
            "button,"
            "input,"
            "textarea,"
            "select,"
            "option,"
            "[role],"
            "[aria-label],"
            "[data-testid],"
            "[data-test],"
            "[data-test-id]"
        )

        locator = page.locator(selector)

        try:
            count = locator.count()
        except Exception:
            return []

        count = min(
            count,
            self.max_elements,
        )

        elements: List[UIElement] = []

        for index in range(count):

            item = locator.nth(index)

            try:
                if not item.is_visible():
                    continue
            except Exception:
                continue

            element = self._extract_single_element(
                item
            )

            if element:
                elements.append(element)

        return elements

    # ========================================================
    # SINGLE ELEMENT
    # ========================================================

    def _extract_single_element(
        self,
        locator,
    ) -> Optional[UIElement]:

        try:
            tag = locator.evaluate(
                "(el) => el.tagName.toLowerCase()"
            )
        except Exception:
            return None

        role = self._get_attribute(
            locator,
            "role",
        )

        aria_label = self._get_attribute(
            locator,
            "aria-label",
        )

        placeholder = self._get_attribute(
            locator,
            "placeholder",
        )

        element_id = self._get_attribute(
            locator,
            "id",
        )

        name = self._get_attribute(
            locator,
            "name",
        )

        test_id = (
            self._get_attribute(
                locator,
                "data-testid",
            )
            or self._get_attribute(
                locator,
                "data-test-id",
            )
            or self._get_attribute(
                locator,
                "data-test",
            )
        )

        href = self._get_attribute(
            locator,
            "href",
        )

        input_type = self._get_attribute(
            locator,
            "type",
        )

        text = self._safe_inner_text(
            locator
        )

        enabled = self._safe_enabled(
            locator
        )

        # Associated label extraction for inputs/selects/textareas
        label = None
        if tag in ("input", "select", "textarea", "button"):
            try:
                label = locator.evaluate(
                    """(el) => {
                        if (el.id) {
                            try {
                                const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                                if (lbl && lbl.innerText) return lbl.innerText.trim();
                            } catch (e) {}
                        }
                        const parent = el.closest('label');
                        if (parent && parent.innerText) return parent.innerText.trim();
                        let prev = el.previousElementSibling;
                        while (prev) {
                            if (prev.tagName && prev.tagName.toLowerCase() === 'label' && prev.innerText) {
                                return prev.innerText.trim();
                            }
                            prev = prev.previousElementSibling;
                        }
                        return null;
                    }"""
                )
            except Exception:
                label = None

        # If no explicit ARIA role exists,
        # infer a basic semantic role from HTML.
        if not role:
            role = self._infer_role(
                tag=tag,
                input_type=input_type,
            )

        locator_candidates = (
            self._build_locator_candidates(
                tag=tag,
                role=role,
                text=text,
                label=label,
                aria_label=aria_label,
                placeholder=placeholder,
                element_id=element_id,
                name=name,
                test_id=test_id,
            )
        )

        return UIElement(
            tag=tag,
            role=role,
            text=self._limit_text(text),
            label=self._limit_text(label) if label else None,
            aria_label=aria_label,
            placeholder=placeholder,
            element_id=element_id,
            name=name,
            test_id=test_id,
            href=href,
            input_type=input_type,
            visible=True,
            enabled=enabled,
            locator_candidates=locator_candidates,
        )

    # ========================================================
    # ROLE INFERENCE
    # ========================================================

    @staticmethod
    def _infer_role(
        tag: str,
        input_type: Optional[str],
    ) -> Optional[str]:

        tag = (tag or "").lower()

        if tag == "a":
            return "link"

        if tag == "button":
            return "button"

        if tag == "textarea":
            return "textbox"

        if tag == "select":
            return "combobox"

        if tag == "input":

            input_type = (
                input_type or "text"
            ).lower()

            if input_type in {
                "button",
                "submit",
                "reset",
            }:
                return "button"

            if input_type == "checkbox":
                return "checkbox"

            if input_type == "radio":
                return "radio"

            return "textbox"

        return None

    # ========================================================
    # LOCATOR CANDIDATES
    # ========================================================

    @staticmethod
    def _build_locator_candidates(
        tag: str,
        role: Optional[str],
        text: Optional[str],
        label: Optional[str] = None,
        aria_label: Optional[str] = None,
        placeholder: Optional[str] = None,
        element_id: Optional[str] = None,
        name: Optional[str] = None,
        test_id: Optional[str] = None,
    ) -> List[Dict[str, str]]:

        candidates: List[Dict[str, str]] = []

        # ----------------------------------------------------
        # Role
        # ----------------------------------------------------

        if role:
            candidates.append(
                {
                    "strategy": "role",
                    "value": role,
                }
            )

        # ----------------------------------------------------
        # Form Label
        # ----------------------------------------------------

        if label:
            clean_label = (
                ApplicationContextExtractor
                ._limit_text(label)
            )
            if clean_label:
                candidates.append(
                    {
                        "strategy": "label",
                        "value": clean_label,
                    }
                )

        # ----------------------------------------------------
        # Accessible label
        # ----------------------------------------------------

        if aria_label:
            candidates.append(
                {
                    "strategy": "aria_label",
                    "value": aria_label,
                }
            )

        # ----------------------------------------------------
        # Placeholder
        # ----------------------------------------------------

        if placeholder:
            candidates.append(
                {
                    "strategy": "placeholder",
                    "value": placeholder,
                }
            )

        # ----------------------------------------------------
        # Test ID
        # ----------------------------------------------------

        if test_id:
            candidates.append(
                {
                    "strategy": "test_id",
                    "value": test_id,
                }
            )

        # ----------------------------------------------------
        # Text
        # ----------------------------------------------------

        if text:
            clean_text = (
                ApplicationContextExtractor
                ._limit_text(text)
            )

            if clean_text:
                candidates.append(
                    {
                        "strategy": "text",
                        "value": clean_text,
                    }
                )

        # ----------------------------------------------------
        # ID
        # ----------------------------------------------------

        if element_id:
            candidates.append(
                {
                    "strategy": "id",
                    "value": element_id,
                }
            )

        # ----------------------------------------------------
        # Name
        # ----------------------------------------------------

        if name:
            candidates.append(
                {
                    "strategy": "name",
                    "value": name,
                }
            )

        return candidates

    # ========================================================
    # FORM EXTRACTION
    # ========================================================

    def _extract_forms(self, page) -> List[Dict[str, Any]]:

        forms: List[Dict[str, Any]] = []

        try:
            form_locator = page.locator(
                "form"
            )

            count = min(
                form_locator.count(),
                50,
            )

        except Exception:
            return forms

        for index in range(count):

            form = form_locator.nth(index)

            try:
                if not form.is_visible():
                    continue
            except Exception:
                continue

            form_data: Dict[str, Any] = {
                "index": index,
                "action": self._get_attribute(
                    form,
                    "action",
                ),
                "method": self._get_attribute(
                    form,
                    "method",
                ),
                "fields": [],
            }

            fields = form.locator(
                "input, textarea, select"
            )

            try:
                field_count = min(
                    fields.count(),
                    100,
                )
            except Exception:
                field_count = 0

            for field_index in range(field_count):

                field = fields.nth(
                    field_index
                )

                try:
                    if not field.is_visible():
                        continue
                except Exception:
                    continue

                field_data = {
                    "tag": self._safe_evaluate_tag(
                        field
                    ),
                    "name": self._get_attribute(
                        field,
                        "name",
                    ),
                    "id": self._get_attribute(
                        field,
                        "id",
                    ),
                    "placeholder": self._get_attribute(
                        field,
                        "placeholder",
                    ),
                    "type": self._get_attribute(
                        field,
                        "type",
                    ),
                    "aria_label": self._get_attribute(
                        field,
                        "aria-label",
                    ),
                }

                form_data["fields"].append(
                    field_data
                )

            forms.append(form_data)

        return forms

    # ========================================================
    # NAVIGATION EXTRACTION
    # ========================================================

    def _extract_navigation_items(
        self,
        page,
    ) -> List[Dict[str, Any]]:

        navigation_items: List[
            Dict[str, Any]
        ] = []

        selector = (
            "nav a,"
            "[role='navigation'] a,"
            "[role='menu'] a,"
            "[role='menubar'] a,"
            "aside a"
        )

        try:
            links = page.locator(
                selector
            )

            count = min(
                links.count(),
                100,
            )

        except Exception:
            return navigation_items

        seen = set()

        for index in range(count):

            link = links.nth(index)

            try:
                if not link.is_visible():
                    continue
            except Exception:
                continue

            text = self._safe_inner_text(
                link
            )

            href = self._get_attribute(
                link,
                "href",
            )

            aria_label = self._get_attribute(
                link,
                "aria-label",
            )

            key = (
                text,
                href,
                aria_label,
            )

            if key in seen:
                continue

            seen.add(key)

            navigation_items.append(
                {
                    "text": self._limit_text(text),
                    "aria_label": aria_label,
                    "href": href,
                }
            )

        return navigation_items

    # ========================================================
    # SAFE HELPERS
    # ========================================================

    @staticmethod
    def _get_attribute(
        locator,
        name: str,
    ) -> Optional[str]:

        try:
            value = locator.get_attribute(
                name
            )

            if value is None:
                return None

            value = value.strip()

            return value or None

        except Exception:
            return None

    @staticmethod
    def _safe_inner_text(
        locator,
    ) -> Optional[str]:

        try:
            text = locator.inner_text(
                timeout=2_000
            )

            return (
                text.strip()
                if text
                else None
            )

        except Exception:
            return None

    @staticmethod
    def _safe_enabled(
        locator,
    ) -> Optional[bool]:

        try:
            return locator.is_enabled()

        except Exception:
            return None

    @staticmethod
    def _safe_evaluate_tag(
        locator,
    ) -> Optional[str]:

        try:
            return locator.evaluate(
                "(el) => el.tagName.toLowerCase()"
            )

        except Exception:
            return None

    @staticmethod
    def _clean_text(
        value: str,
        max_length: int,
    ) -> str:

        value = re.sub(
            r"\s+",
            " ",
            value or "",
        ).strip()

        return value[:max_length]

    @staticmethod
    def _limit_text(
        value: Optional[str],
        max_length: int = DEFAULT_MAX_TEXT_LENGTH,
    ) -> Optional[str]:

        if not value:
            return None

        value = re.sub(
            r"\s+",
            " ",
            value,
        ).strip()

        if not value:
            return None

        return value[:max_length]


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def inspect_application(
    url: str,
    screenshot_path: Optional[str] = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
    headless: bool = True,
) -> ApplicationPageContext:
    """
    Convenience wrapper used by Stage 2 services.
    Includes in-memory cache to prevent repeated slow browser navigations.
    """
    normalized = (url or "").strip()
    now = time.time()

    if not screenshot_path and normalized in _INSPECT_CACHE:
        cached_time, cached_context = _INSPECT_CACHE[normalized]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_context

    extractor = ApplicationContextExtractor(
        timeout_ms=timeout_ms,
        max_elements=max_elements,
        headless=headless,
    )

    result = extractor.inspect(
        url=url,
        screenshot_path=screenshot_path,
    )

    if not screenshot_path and normalized:
        _INSPECT_CACHE[normalized] = (now, result)

    return result


# ============================================================
# JSON EXPORT
# ============================================================

def context_to_json(
    context: ApplicationPageContext,
) -> str:
    """
    Convert application context into JSON that can later be
    supplied to the Gemini automation planner.
    """

    return json.dumps(
        context.model_dump(
            mode="json"
        ),
        indent=2,
        ensure_ascii=False,
    )