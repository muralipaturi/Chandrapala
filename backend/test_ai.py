import re
from typing import Any


# ============================================================
# TEST CASE GENERATOR
# ============================================================

def generate_test_cases(
    requirement: str,
    base_url: str = "",
    screenshot_context: str = "",
):
    """
    Generate requirement-driven test cases.

    Input:
        requirement       - Business requirement supplied by user
        base_url          - Application URL
        screenshot_context - Optional information extracted from screenshot

    Output:
        List of structured test cases
    """

    if not requirement or not requirement.strip():
        raise ValueError("Requirement cannot be empty.")

    requirement = requirement.strip()

    context = {
        "requirement": requirement,
        "base_url": base_url or "",
        "screenshot_context": screenshot_context or "",
    }

    return _generate_requirement_based_cases(context)


# ============================================================
# MAIN REQUIREMENT ANALYSIS
# ============================================================

def _generate_requirement_based_cases(
    context: dict[str, str]
) -> list[dict[str, Any]]:

    requirement = context["requirement"]

    normalized = _normalize(requirement)

    # --------------------------------------------------------
    # Detect the business capability.
    # --------------------------------------------------------

    capability = _detect_capability(normalized)

    # --------------------------------------------------------
    # Extract actions, fields, values and validations.
    # --------------------------------------------------------

    actions = _extract_actions(requirement)

    fields = _extract_fields(requirement)

    values = _extract_values(requirement)

    validations = _extract_validations(requirement)

    # --------------------------------------------------------
    # Build test cases based on the actual requirement.
    # --------------------------------------------------------

    cases = []

    # Positive scenario is always based on the actual workflow.
    cases.append(
        _build_positive_case(
            requirement=requirement,
            capability=capability,
            actions=actions,
            fields=fields,
            values=values,
            validations=validations,
            context=context,
        )
    )

    # --------------------------------------------------------
    # Only generate additional scenarios when the requirement
    # provides enough evidence for them.
    # --------------------------------------------------------

    if _supports_required_field_validation(
        requirement,
        fields,
    ):
        cases.extend(
            _build_required_field_cases(
                requirement=requirement,
                capability=capability,
                fields=fields,
                actions=actions,
                context=context,
            )
        )

    if _contains_invalid_input_requirement(normalized):
        cases.append(
            _build_invalid_input_case(
                requirement=requirement,
                capability=capability,
                fields=fields,
                actions=actions,
                context=context,
            )
        )

    if _contains_duplicate_requirement(normalized):
        cases.append(
            _build_duplicate_case(
                requirement=requirement,
                capability=capability,
                fields=fields,
                actions=actions,
                context=context,
            )
        )

    if _contains_boundary_requirement(normalized):
        cases.append(
            _build_boundary_case(
                requirement=requirement,
                capability=capability,
                fields=fields,
                actions=actions,
                context=context,
            )
        )

    # --------------------------------------------------------
    # Remove duplicates and normalize IDs.
    # --------------------------------------------------------

    cases = _remove_duplicate_cases(cases)

    for index, case in enumerate(cases, start=1):
        case["id"] = f"TC{index:03d}"

    return cases


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# CAPABILITY DETECTION
# ============================================================

def _detect_capability(requirement: str) -> str:

    capability_keywords = {

        "login": [
            "login",
            "sign in",
            "signin",
            "authenticate",
            "authentication",
        ],

        "registration": [
            "register",
            "registration",
            "sign up",
            "signup",
            "create account",
        ],

        "employee_creation": [
            "create employee",
            "add employee",
            "new employee",
            "employee creation",
        ],

        "employee_update": [
            "update employee",
            "edit employee",
            "modify employee",
        ],

        "search": [
            "search",
            "find",
            "lookup",
            "filter",
        ],

        "delete": [
            "delete",
            "remove",
        ],

        "upload": [
            "upload",
            "attach file",
            "attachment",
        ],

        "download": [
            "download",
            "export",
        ],

        "payment": [
            "payment",
            "pay",
            "checkout",
            "transaction",
        ],

        "password": [
            "password",
            "reset password",
            "change password",
            "forgot password",
        ],

        "form_submission": [
            "submit form",
            "submit the form",
            "form submission",
        ],
    }

    for capability, keywords in capability_keywords.items():

        for keyword in keywords:

            if keyword in requirement:
                return capability

    return "generic"


# ============================================================
# ACTION EXTRACTION
# ============================================================

def _extract_actions(
    requirement: str,
) -> list[str]:

    action_patterns = [

        (
            r"\bopen\b(.+?)(?:\.|$)",
            "Open",
        ),

        (
            r"\bnavigate to\b(.+?)(?:\.|$)",
            "Navigate to",
        ),

        (
            r"\bgo to\b(.+?)(?:\.|$)",
            "Go to",
        ),

        (
            r"\bclick\b(.+?)(?:\.|$)",
            "Click",
        ),

        (
            r"\benter\b(.+?)(?:\.|$)",
            "Enter",
        ),

        (
            r"\binput\b(.+?)(?:\.|$)",
            "Input",
        ),

        (
            r"\bselect\b(.+?)(?:\.|$)",
            "Select",
        ),

        (
            r"\bchoose\b(.+?)(?:\.|$)",
            "Choose",
        ),

        (
            r"\bsave\b(.+?)(?:\.|$)",
            "Save",
        ),

        (
            r"\bsubmit\b(.+?)(?:\.|$)",
            "Submit",
        ),

        (
            r"\bdelete\b(.+?)(?:\.|$)",
            "Delete",
        ),

        (
            r"\bupdate\b(.+?)(?:\.|$)",
            "Update",
        ),

        (
            r"\bedit\b(.+?)(?:\.|$)",
            "Edit",
        ),

        (
            r"\bsearch\b(.+?)(?:\.|$)",
            "Search",
        ),

        (
            r"\bverify\b(.+?)(?:\.|$)",
            "Verify",
        ),

        (
            r"\bvalidate\b(.+?)(?:\.|$)",
            "Validate",
        ),
    ]

    actions = []

    for pattern, prefix in action_patterns:

        matches = re.findall(
            pattern,
            requirement,
            flags=re.IGNORECASE,
        )

        for match in matches:

            text = match.strip()

            if text:
                actions.append(
                    f"{prefix} {text}"
                )

    return _unique(actions)


# ============================================================
# FIELD EXTRACTION
# ============================================================

def _extract_fields(
    requirement: str,
) -> list[str]:

    known_fields = [
        "username",
        "password",
        "first name",
        "middle name",
        "last name",
        "employee id",
        "employee name",
        "email",
        "phone",
        "mobile",
        "address",
        "city",
        "state",
        "country",
        "zip code",
        "postal code",
        "date of birth",
        "date",
        "amount",
        "quantity",
        "price",
        "policy number",
        "customer name",
        "account number",
        "card number",
        "expiry date",
        "cvv",
        "search",
        "description",
        "comments",
    ]

    normalized = _normalize(requirement)

    found = []

    for field in known_fields:

        if field in normalized:
            found.append(field)

    return found


# ============================================================
# VALUE EXTRACTION
# ============================================================

def _extract_values(
    requirement: str,
) -> dict[str, str]:

    values = {}

    patterns = [

        (
            r"(?:first name)\s*(?:is|as|=|:)\s*['\"]?([^,'\".]+)",
            "first name",
        ),

        (
            r"(?:last name)\s*(?:is|as|=|:)\s*['\"]?([^,'\".]+)",
            "last name",
        ),

        (
            r"(?:username)\s*(?:is|as|=|:)\s*['\"]?([^,'\".]+)",
            "username",
        ),

        (
            r"(?:password)\s*(?:is|as|=|:)\s*['\"]?([^,'\".]+)",
            "password",
        ),

        (
            r"(?:employee id)\s*(?:is|as|=|:)\s*['\"]?([^,'\".]+)",
            "employee id",
        ),

        (
            r"(?:email)\s*(?:is|as|=|:)\s*['\"]?([^,'\".]+)",
            "email",
        ),

        (
            r"(?:amount)\s*(?:is|as|=|:)\s*['\"]?([^,'\".]+)",
            "amount",
        ),

        (
            r"(?:quantity)\s*(?:is|as|=|:)\s*['\"]?([^,'\".]+)",
            "quantity",
        ),
    ]

    for pattern, field in patterns:

        match = re.search(
            pattern,
            requirement,
            flags=re.IGNORECASE,
        )

        if match:

            values[field] = (
                match.group(1).strip()
            )

    return values


# ============================================================
# VALIDATION EXTRACTION
# ============================================================

def _extract_validations(
    requirement: str,
) -> list[str]:

    normalized = _normalize(requirement)

    validations = []

    validation_patterns = [

        (
            "successfully",
            "Successful completion should be verified",
        ),

        (
            "success",
            "Successful completion should be verified",
        ),

        (
            "displayed",
            "Expected information should be displayed",
        ),

        (
            "visible",
            "Expected information should be visible",
        ),

        (
            "error message",
            "Expected error message should be displayed",
        ),

        (
            "validation message",
            "Expected validation message should be displayed",
        ),

        (
            "created",
            "Created record should be verified",
        ),

        (
            "updated",
            "Updated record should be verified",
        ),

        (
            "deleted",
            "Deleted record should no longer be available",
        ),

        (
            "saved",
            "Saved information should be verified",
        ),
    ]

    for keyword, validation in validation_patterns:

        if keyword in normalized:
            validations.append(validation)

    return _unique(validations)


# ============================================================
# POSITIVE CASE
# ============================================================

def _build_positive_case(
    requirement: str,
    capability: str,
    actions: list[str],
    fields: list[str],
    values: dict[str, str],
    validations: list[str],
    context: dict[str, str],
) -> dict[str, Any]:

    title = _build_positive_title(
        capability,
        requirement,
    )

    steps = _build_requirement_steps(
        requirement=requirement,
        capability=capability,
        actions=actions,
        fields=fields,
        values=values,
    )

    expected = _build_expected_result(
        requirement=requirement,
        capability=capability,
        validations=validations,
    )

    return {
        "id": "TC001",
        "type": "Positive",
        "title": title,
        "priority": "High",
        "preconditions": _build_preconditions(
            capability=capability,
            base_url=context["base_url"],
        ),
        "test_data": _build_test_data(
            values=values,
            fields=fields,
        ),
        "steps": steps,
        "expected_result": expected,
        "automation_candidate": True,
    }


# ============================================================
# REQUIREMENT STEPS
# ============================================================

def _build_requirement_steps(
    requirement: str,
    capability: str,
    actions: list[str],
    fields: list[str],
    values: dict[str, str],
) -> list[str]:

    steps = []

    # --------------------------------------------------------
    # Login
    # --------------------------------------------------------

    if capability == "login":

        steps.extend([
            "Open the login page",
            "Enter the username specified by the requirement",
            "Enter the password specified by the requirement",
            "Click the Login button",
        ])

        return steps + _requirement_specific_steps(
            requirement,
            actions,
        )

    # --------------------------------------------------------
    # Employee creation
    # --------------------------------------------------------

    if capability == "employee_creation":

        steps.append(
            "Open the application"
        )

        if "pim" in _normalize(requirement):
            steps.append(
                "Navigate to the PIM section"
            )

        steps.append(
            "Open the employee creation form"
        )

        for field in fields:

            if field in values:

                steps.append(
                    f"Enter {field} as {values[field]}"
                )

            else:

                steps.append(
                    f"Enter a valid value in the {field} field"
                )

        if "save" in _normalize(requirement):

            steps.append(
                "Click the Save button"
            )

        return steps + _requirement_specific_steps(
            requirement,
            actions,
        )

    # --------------------------------------------------------
    # Employee update
    # --------------------------------------------------------

    if capability == "employee_update":

        steps.append(
            "Open the application"
        )

        steps.append(
            "Locate the employee specified by the requirement"
        )

        steps.append(
            "Open the employee details"
        )

        steps.append(
            "Edit the required employee information"
        )

        if "save" in _normalize(requirement):

            steps.append(
                "Click the Save button"
            )

        return steps + _requirement_specific_steps(
            requirement,
            actions,
        )

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    if capability == "search":

        steps.append(
            "Open the application"
        )

        steps.append(
            "Enter the search criteria specified by the requirement"
        )

        steps.append(
            "Perform the search"
        )

        steps.append(
            "Verify the search results"
        )

        return steps

    # --------------------------------------------------------
    # Delete
    # --------------------------------------------------------

    if capability == "delete":

        steps.append(
            "Open the application"
        )

        steps.append(
            "Locate the record specified by the requirement"
        )

        steps.append(
            "Select the delete action"
        )

        steps.append(
            "Confirm the deletion"
        )

        steps.append(
            "Verify the record is no longer available"
        )

        return steps

    # --------------------------------------------------------
    # Generic requirement
    # --------------------------------------------------------

    steps.append(
        "Open the application"
    )

    requirement_steps = _requirement_specific_steps(
        requirement,
        actions,
    )

    if requirement_steps:

        steps.extend(requirement_steps)

    else:

        steps.append(
            f"Perform the workflow described in the requirement: {requirement}"
        )

    return _unique(steps)


# ============================================================
# SPECIFIC ACTIONS
# ============================================================

def _requirement_specific_steps(
    requirement: str,
    actions: list[str],
) -> list[str]:

    normalized = _normalize(requirement)

    steps = []

    if "click" in normalized:

        steps.append(
            "Click the UI element specified by the requirement"
        )

    if "enter" in normalized or "input" in normalized:

        steps.append(
            "Enter the values specified by the requirement"
        )

    if "select" in normalized:

        steps.append(
            "Select the option specified by the requirement"
        )

    if "search" in normalized:

        steps.append(
            "Perform the search using the specified criteria"
        )

    if "save" in normalized:

        steps.append(
            "Save the entered information"
        )

    if "submit" in normalized:

        steps.append(
            "Submit the request"
        )

    if "verify" in normalized or "validate" in normalized:

        steps.append(
            "Verify the expected result described in the requirement"
        )

    return _unique(steps)


# ============================================================
# PRECONDITIONS
# ============================================================

def _build_preconditions(
    capability: str,
    base_url: str,
) -> list[str]:

    conditions = []

    if base_url:

        conditions.append(
            f"Application is accessible at {base_url}"
        )

    if capability != "login":

        conditions.append(
            "Required user access is available"
        )

    return conditions


# ============================================================
# TEST DATA
# ============================================================

def _build_test_data(
    values: dict[str, str],
    fields: list[str],
) -> list[str]:

    data = []

    for field, value in values.items():

        data.append(
            f"{field}: {value}"
        )

    for field in fields:

        if field not in values:

            data.append(
                f"{field}: valid test data"
            )

    return data


# ============================================================
# EXPECTED RESULT
# ============================================================

def _build_expected_result(
    requirement: str,
    capability: str,
    validations: list[str],
) -> str:

    if validations:

        return (
            "The application should satisfy the requested workflow "
            "and all expected validations. "
            + " ".join(validations)
        )

    if capability == "login":

        return (
            "The user should be authenticated successfully "
            "when valid credentials are supplied."
        )

    if capability == "employee_creation":

        return (
            "The employee should be created successfully "
            "with the values specified in the requirement."
        )

    if capability == "employee_update":

        return (
            "The employee information should be updated successfully "
            "with the values specified in the requirement."
        )

    if capability == "search":

        return (
            "The application should return the records matching "
            "the search criteria."
        )

    if capability == "delete":

        return (
            "The selected record should be deleted successfully "
            "and should no longer be available."
        )

    return (
        "The application should successfully complete the workflow "
        "described in the requirement and produce the expected result."
    )


# ============================================================
# ADDITIONAL TEST CASES
# ============================================================

def _supports_required_field_validation(
    requirement: str,
    fields: list[str],
) -> bool:

    normalized = _normalize(requirement)

    return (
        len(fields) > 0
        and (
            "required" in normalized
            or "mandatory" in normalized
            or "validation" in normalized
        )
    )


def _build_required_field_cases(
    requirement: str,
    capability: str,
    fields: list[str],
    actions: list[str],
    context: dict[str, str],
) -> list[dict[str, Any]]:

    cases = []

    for index, field in enumerate(fields, start=2):

        cases.append({
            "id": f"TC{index:03d}",
            "type": "Validation",
            "title": f"Verify mandatory validation for {field}",
            "priority": "Medium",
            "preconditions": _build_preconditions(
                capability,
                context["base_url"],
            ),
            "test_data": [
                f"{field}: empty"
            ],
            "steps": [
                "Open the application",
                f"Leave the {field} field empty",
                "Provide valid values for other mandatory fields",
                "Submit or save the form",
            ],
            "expected_result": (
                f"A required-field validation message should be "
                f"displayed for {field}."
            ),
            "automation_candidate": True,
        })

    return cases


def _contains_invalid_input_requirement(
    requirement: str,
) -> bool:

    return any(
        word in requirement
        for word in [
            "invalid input",
            "invalid value",
            "invalid data",
            "incorrect",
            "wrong value",
        ]
    )


def _build_invalid_input_case(
    requirement: str,
    capability: str,
    fields: list[str],
    actions: list[str],
    context: dict[str, str],
) -> dict[str, Any]:

    return {
        "id": "TC999",
        "type": "Negative",
        "title": "Verify invalid input handling",
        "priority": "Medium",
        "preconditions": _build_preconditions(
            capability,
            context["base_url"],
        ),
        "test_data": [
            "Invalid input as specified by the requirement"
        ],
        "steps": [
            "Open the application",
            "Enter the invalid value specified by the requirement",
            "Submit or save the information",
        ],
        "expected_result": (
            "The application should reject the invalid input "
            "and display the expected validation or error message."
        ),
        "automation_candidate": True,
    }


def _contains_duplicate_requirement(
    requirement: str,
) -> bool:

    normalized = _normalize(requirement)

    return (
        "duplicate" in normalized
        or "already exists" in normalized
        or "existing record" in normalized
    )


def _build_duplicate_case(
    requirement: str,
    capability: str,
    fields: list[str],
    actions: list[str],
    context: dict[str, str],
) -> dict[str, Any]:

    return {
        "id": "TC998",
        "type": "Negative",
        "title": "Verify duplicate record handling",
        "priority": "Medium",
        "preconditions": _build_preconditions(
            capability,
            context["base_url"],
        ),
        "test_data": [
            "Use data that already exists in the application"
        ],
        "steps": [
            "Open the application",
            "Enter data that already exists",
            "Submit or save the information",
        ],
        "expected_result": (
            "The application should prevent creation of a duplicate "
            "record and display the expected message."
        ),
        "automation_candidate": True,
    }


def _contains_boundary_requirement(
    requirement: str,
) -> bool:

    normalized = _normalize(requirement)

    return any(
        word in normalized
        for word in [
            "boundary",
            "minimum",
            "maximum",
            "max length",
            "min length",
            "limit",
        ]
    )


def _build_boundary_case(
    requirement: str,
    capability: str,
    fields: list[str],
    actions: list[str],
    context: dict[str, str],
) -> dict[str, Any]:

    return {
        "id": "TC997",
        "type": "Boundary",
        "title": "Verify boundary conditions specified in the requirement",
        "priority": "Medium",
        "preconditions": _build_preconditions(
            capability,
            context["base_url"],
        ),
        "test_data": [
            "Use the minimum, maximum, or boundary values specified by the requirement"
        ],
        "steps": [
            "Open the application",
            "Enter the boundary value specified by the requirement",
            "Submit or save the information",
        ],
        "expected_result": (
            "The application should correctly handle the boundary "
            "value according to the requirement."
        ),
        "automation_candidate": True,
    }


# ============================================================
# TITLE
# ============================================================

def _build_positive_title(
    capability: str,
    requirement: str,
) -> str:

    titles = {

        "login":
            "Verify successful login with valid credentials",

        "registration":
            "Verify successful user registration",

        "employee_creation":
            "Verify employee creation with valid data",

        "employee_update":
            "Verify employee update with valid data",

        "search":
            "Verify search using valid criteria",

        "delete":
            "Verify successful record deletion",

        "upload":
            "Verify successful file upload",

        "download":
            "Verify successful file download",

        "payment":
            "Verify successful payment processing",

        "password":
            "Verify password workflow",

        "form_submission":
            "Verify successful form submission",
    }

    if capability in titles:

        return titles[capability]

    return (
        "Verify successful execution of the requested workflow"
    )


# ============================================================
# UTILITIES
# ============================================================

def _unique(
    values: list[str],
) -> list[str]:

    result = []
    seen = set()

    for value in values:

        normalized = value.strip().lower()

        if normalized not in seen:

            seen.add(normalized)
            result.append(value.strip())

    return result


def _remove_duplicate_cases(
    cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    result = []
    seen = set()

    for case in cases:

        key = (
            case.get("title", "").strip().lower(),
            case.get("type", "").strip().lower(),
        )

        if key not in seen:

            seen.add(key)
            result.append(case)

    return result