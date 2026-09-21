"""
Stage 2.5 - Locator Resolution

Converts real Application Context evidence into the strongest
framework-independent locator.

IMPORTANT:
    - Never invent locators.
    - Never create XPath/CSS from guesswork.
    - Only use evidence extracted from the application.
    - Prefer specific locators over generic role-only locators.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from application_context import (
    ApplicationPageContext,
    UIElement,
)

from automation_models import (
    Locator,
    LocatorStrategy,
)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_CANDIDATES = 10

# Higher score = stronger/more specific locator.
#
# Generic role-only locators intentionally receive a lower
# score because:
#
#     role=textbox
#
# may match multiple elements on the same page.
LOCATOR_SCORES = {
    "test_id": 100,
    "accessibility_id": 98,
    "aria_label": 96,
    "label": 94,
    "placeholder": 92,
    "id": 90,
    "name": 85,
    "role": 65,
    "text": 55,
    "css": 40,
    "xpath": 30,
}


# ============================================================
# RESULT MODEL
# ============================================================

class LocatorResolution(BaseModel):
    """
    Result of locator resolution for a business target.
    """

    model_config = ConfigDict(extra="forbid")

    target: str

    found: bool = False

    locator: Optional[Locator] = None

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    matched_element: Optional[UIElement] = None

    candidates: List[Locator] = Field(
        default_factory=list
    )

    reason: str = ""


# ============================================================
# TARGET VALIDATION
# ============================================================

def is_valid_ui_target(target: Optional[str]) -> bool:
    """
    Validates whether a string represents a real UI element target.

    Rejects:
    - Precondition strings (e.g. "PRECONDITION: ...", "User is logged in as...")
    - Full prose sentences or expected result descriptions (> 5 words or > 45 chars, or containing outcome verbs)
    - Test data input values (e.g. emails, dates)
    """
    if not target or not target.strip():
        return False

    t = target.strip()
    low = t.lower()

    if any(low.startswith(p) for p in ["and ", "or ", "with ", "for ", "to ", "of ", "in ", "by ", "as "]):
        return False

    if any(phrase in low for phrase in [
        "deployed with", "server running", "database initialized",
        "logged in as", "should be displayed",
        "creation and query readiness", "unique patient identity",
        "redirected to", "patient record created successfully",
        "user can view", "workflow with valid", "query readiness",
        "identity creation", "created successfully"
    ]):
        return False

    # Check for long sentence/prose structure
    words = t.split()
    if len(words) > 5 or len(t) > 45:
        return False

    # Check for test data patterns (email, ISO date)
    if re.match(r"^[^@]+@[^@]+\.[^@]+$", t):
        return False
    if re.match(r"^\d{4}-\d{2}-\d{2}$", t):
        return False

    return True


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(
    value: Optional[str],
) -> str:
    """
    Normalize text for semantic matching.
    """

    if not value:
        return ""

    value = value.lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    value = re.sub(
        r"[^a-z0-9\s_-]",
        "",
        value,
    )

    return value.strip()


# ============================================================
# TOKENIZATION
# ============================================================

def tokenize(
    value: str,
) -> set[str]:

    normalized = normalize_text(
        value
    )

    if not normalized:
        return set()

    return {
        token
        for token in normalized.split()
        if len(token) > 1
    }


# ============================================================
# TEXT SIMILARITY
# ============================================================

def calculate_text_similarity(
    target: str,
    candidate: str,
) -> float:
    """
    Calculate semantic similarity between the business target
    and an observed UI value.
    """

    target_normalized = normalize_text(
        target
    )

    candidate_normalized = normalize_text(
        candidate
    )

    if not target_normalized:
        return 0.0

    if not candidate_normalized:
        return 0.0

    # Exact match.
    if target_normalized == candidate_normalized:
        return 1.0

    # Candidate contains target.
    if target_normalized in candidate_normalized:
        return 0.90

    # Target contains candidate.
    if candidate_normalized in target_normalized:
        return 0.80

    target_tokens = tokenize(
        target_normalized
    )

    candidate_tokens = tokenize(
        candidate_normalized
    )

    if not target_tokens or not candidate_tokens:
        return 0.0

    intersection = (
        target_tokens & candidate_tokens
    )

    if not intersection:
        return 0.0

    union = (
        target_tokens | candidate_tokens
    )

    return len(intersection) / len(union)


# ============================================================
# ELEMENT VALUES
# ============================================================

def _element_values(
    element: UIElement,
) -> List[Tuple[str, str]]:
    """
    Return actual observed values that can be used for
    semantic matching.
    """

    values: List[
        Tuple[str, str]
    ] = []

    fields = [
        ("label", getattr(element, "label", None)),
        ("text", element.text),
        ("aria_label", element.aria_label),
        ("placeholder", element.placeholder),
        ("element_id", element.element_id),
        ("name", element.name),
        ("test_id", element.test_id),
        ("href", element.href),
    ]

    for field_name, value in fields:

        if value:
            values.append(
                (
                    field_name,
                    value,
                )
            )

    return values


# ============================================================
# ELEMENT SCORING
# ============================================================

def score_element(
    target: str,
    element: UIElement,
) -> float:
    """
    Find the strongest semantic match between the target and
    the observed UI element.
    """

    best_similarity = 0.0

    for _, value in _element_values(
        element
    ):

        similarity = (
            calculate_text_similarity(
                target,
                value,
            )
        )

        best_similarity = max(
            best_similarity,
            similarity,
        )

    return best_similarity


# ============================================================
# STRATEGY CONVERSION
# ============================================================

def convert_strategy(
    strategy: str,
) -> Optional[LocatorStrategy]:

    mapping = {
        "test_id": LocatorStrategy.TEST_ID,

        "accessibility_id":
            LocatorStrategy.ACCESSIBILITY_ID,

        "aria_label":
            LocatorStrategy.LABEL,

        "role":
            LocatorStrategy.ROLE,

        "label":
            LocatorStrategy.LABEL,

        "placeholder":
            LocatorStrategy.PLACEHOLDER,

        "id":
            LocatorStrategy.ID,

        "name":
            LocatorStrategy.NAME,

        "text":
            LocatorStrategy.TEXT,

        "css":
            LocatorStrategy.CSS,

        "xpath":
            LocatorStrategy.XPATH,
    }

    return mapping.get(
        strategy
    )


# ============================================================
# UNSAFE LOCATOR DETECTION
# ============================================================

def _looks_unsafe(
    value: str,
) -> bool:
    """
    Reject obvious placeholder/fabricated locator values.

    We only want evidence extracted from the application.
    """

    normalized = value.lower().strip()

    unsafe_tokens = (
        "generated",
        "example-selector",
        "some-selector",
        "placeholder-selector",
        "random-selector",
        "unknown-selector",
    )

    return any(
        token in normalized
        for token in unsafe_tokens
    )


# ============================================================
# BUILD LOCATOR CANDIDATES
# ============================================================

def build_candidates(
    element: UIElement,
    similarity: float,
) -> List[Locator]:
    """
    Build locator candidates exclusively from observed
    application evidence.

    Specific locators are preferred.

    Generic role-only locators are added only when no more
    specific evidence exists.
    """

    candidates: List[Locator] = []

    # --------------------------------------------------------
    # TEST ID
    # --------------------------------------------------------

    if element.test_id:

        value = element.test_id.strip()

        if value and not _looks_unsafe(value):

            candidates.append(
                Locator(
                    strategy=LocatorStrategy.TEST_ID,
                    value=value,
                    description=(
                        "Observed data-testid/data-test-id "
                        "from application UI."
                    ),
                )
            )

    # --------------------------------------------------------
    # ARIA LABEL
    # --------------------------------------------------------

    if element.aria_label:

        value = element.aria_label.strip()

        if value:

            candidates.append(
                Locator(
                    strategy=LocatorStrategy.LABEL,
                    value=value,
                    description=(
                        "Observed aria-label from "
                        "application UI."
                    ),
                )
            )

    # --------------------------------------------------------
    # PLACEHOLDER
    # --------------------------------------------------------

    if element.placeholder:

        value = element.placeholder.strip()

        if value:

            candidates.append(
                Locator(
                    strategy=LocatorStrategy.PLACEHOLDER,
                    value=value,
                    description=(
                        "Observed placeholder from "
                        "application UI."
                    ),
                )
            )

    # --------------------------------------------------------
    # DOM ID
    # --------------------------------------------------------

    if element.element_id:

        value = element.element_id.strip()

        if value and not _looks_unsafe(value):

            candidates.append(
                Locator(
                    strategy=LocatorStrategy.ID,
                    value=value,
                    description=(
                        "Observed DOM id from "
                        "application UI."
                    ),
                )
            )

    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    if element.name:

        value = element.name.strip()

        if value:

            candidates.append(
                Locator(
                    strategy=LocatorStrategy.NAME,
                    value=value,
                    description=(
                        "Observed name attribute from "
                        "application UI."
                    ),
                )
            )

    # --------------------------------------------------------
    # VISIBLE TEXT
    # --------------------------------------------------------

    if element.text:

        value = element.text.strip()

        if value:

            candidates.append(
                Locator(
                    strategy=LocatorStrategy.TEXT,
                    value=value,
                    description=(
                        "Observed visible text from "
                        "application UI."
                    ),
                )
            )
    # --------------------------------------------------------
    # SEMANTIC ROLE
    #
    # For interactive elements such as buttons and links,
    # preserve both the semantic role and visible/accessibility
    # name. This allows Playwright to generate:
    #
    #     page.get_by_role("button", name="Login")
    #
    # instead of the ambiguous:
    #
    #     page.get_by_text("Login")
    # --------------------------------------------------------

    if element.role:

        semantic_name = (
            element.aria_label
            or element.text
        )

        interactive_roles = {
            "button",
            "link",
            "checkbox",
            "radio",
            "tab",
            "menuitem",
            "option",
            "combobox",
        }

        if (
            element.role.casefold()
            in interactive_roles
            and semantic_name
        ):

            candidates.append(
                Locator(
                    strategy=LocatorStrategy.ROLE,
                    value=element.role,
                    name=semantic_name.strip(),
                    description=(
                        "Observed semantic role and "
                        "accessible name from application UI."
                    ),
                )
            )

        else:

            has_specific_locator = any(
                [
                    element.test_id,
                    element.aria_label,
                    element.placeholder,
                    element.element_id,
                    element.name,
                    element.text,
                ]
            )

            if not has_specific_locator:

                candidates.append(
                    Locator(
                        strategy=LocatorStrategy.ROLE,
                        value=element.role,
                        description=(
                            "Observed semantic role from "
                            "application UI; no more specific "
                            "locator evidence was available."
                        ),
                    )
                )

    return candidates


# ============================================================
# CANDIDATE RANKING
# ============================================================

def rank_candidates(
    candidates: List[Locator],
) -> List[Locator]:
    """
    Rank locator candidates from strongest to weakest.
    """

    def score(
        locator: Locator,
    ) -> int:

        return LOCATOR_SCORES.get(
            locator.strategy.value,
            0,
        )

    return sorted(
        candidates,
        key=score,
        reverse=True,
    )


# ============================================================
# LOCATOR RESOLVER
# ============================================================

class LocatorResolver:

    def __init__(
        self,
        minimum_similarity: float = 0.50,
    ):
        self.minimum_similarity = (
            minimum_similarity
        )

    # ========================================================
    # RESOLVE
    # ========================================================

    def resolve(
        self,
        target: str,
        context: ApplicationPageContext,
    ) -> LocatorResolution:
        """
        Resolve a business target to the strongest locator
        supported by the actual application context.
        """

        target = (
            target or ""
        ).strip()

        if not target:

            return LocatorResolution(
                target=target,
                found=False,
                reason=(
                    "Empty target supplied."
                ),
            )

        if not is_valid_ui_target(target):

            return LocatorResolution(
                target=target,
                found=False,
                reason=(
                    "Target is not a valid UI element name."
                ),
            )

        scored_elements: List[
            Tuple[float, UIElement]
        ] = []

        # ----------------------------------------------------
        # Find matching elements.
        # ----------------------------------------------------

        for element in context.elements:

            similarity = score_element(
                target,
                element,
            )

            if similarity >= (
                self.minimum_similarity
            ):

                scored_elements.append(
                    (
                        similarity,
                        element,
                    )
                )

        if not scored_elements:

            return LocatorResolution(
                target=target,
                found=False,
                reason=(
                    "No UI element in the supplied "
                    "application context matched "
                    "the target."
                ),
            )

        # ----------------------------------------------------
        # Highest semantic match first.
        # ----------------------------------------------------

        scored_elements.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        all_candidates: List[
            Tuple[float, Locator]
        ] = []

        # ----------------------------------------------------
        # Build candidates for every matching element.
        # ----------------------------------------------------

        for similarity, element in (
            scored_elements
        ):

            candidates = build_candidates(
                element=element,
                similarity=similarity,
            )

            for candidate in candidates:

                all_candidates.append(
                    (
                        similarity,
                        candidate,
                    )
                )

        # ----------------------------------------------------
        # Matching element exists, but no safe locator.
        # ----------------------------------------------------

        if not all_candidates:

            best_similarity, best_element = (
                scored_elements[0]
            )

            return LocatorResolution(
                target=target,
                found=False,
                confidence=best_similarity,
                matched_element=best_element,
                reason=(
                    "A matching UI element was found, "
                    "but no safe locator candidate was "
                    "available."
                ),
            )

        # ----------------------------------------------------
        # Rank:
        #
        # 1. semantic similarity
        # 2. locator specificity
        # ----------------------------------------------------

        all_candidates.sort(
            key=lambda item: (
                item[0],
                LOCATOR_SCORES.get(
                    item[1].strategy.value,
                    0,
                ),
            ),
            reverse=True,
        )

        best_similarity, best_locator = (
            all_candidates[0]
        )

        # ----------------------------------------------------
        # Identify the element associated with the selected
        # locator.
        # ----------------------------------------------------

        best_element: Optional[
            UIElement
        ] = None

        for similarity, element in (
            scored_elements
        ):

            element_candidates = (
                build_candidates(
                    element=element,
                    similarity=similarity,
                )
            )

            if any(
                candidate.strategy
                == best_locator.strategy
                and candidate.value
                == best_locator.value
                for candidate
                in element_candidates
            ):

                best_element = element

                break

        # ----------------------------------------------------
        # Confidence.
        # ----------------------------------------------------

        confidence = (
            self._calculate_confidence(
                similarity=best_similarity,
                locator=best_locator,
            )
        )

        # ----------------------------------------------------
        # Candidate list.
        # ----------------------------------------------------

        candidate_locators = [
            locator
            for _, locator
            in all_candidates[
                :MAX_CANDIDATES
            ]
        ]

        return LocatorResolution(
            target=target,
            found=True,
            locator=best_locator,
            confidence=confidence,
            matched_element=best_element,
            candidates=candidate_locators,
            reason=(
                "Locator resolved from actual "
                "application UI evidence."
            ),
        )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    @staticmethod
    def _calculate_confidence(
        similarity: float,
        locator: Locator,
    ) -> float:
        """
        Combine semantic matching confidence with locator
        specificity.
        """

        strategy_score = LOCATOR_SCORES.get(
            locator.strategy.value,
            0,
        )

        strategy_confidence = (
            strategy_score / 100.0
        )

        confidence = (
            similarity * 0.65
            + strategy_confidence * 0.35
        )

        return round(
            min(
                max(
                    confidence,
                    0.0,
                ),
                1.0,
            ),
            3,
        )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def resolve_locator(
    target: str,
    context: ApplicationPageContext,
    minimum_similarity: float = 0.50,
) -> LocatorResolution:
    """
    Convenience wrapper.
    """

    resolver = LocatorResolver(
        minimum_similarity=minimum_similarity
    )

    return resolver.resolve(
        target=target,
        context=context,
    )
