from automation_models import (
    AutomationFramework,
    AutomationLanguage,
    validate_framework_language,
)


SUPPORTED = [
    (
        AutomationFramework.SELENIUM,
        AutomationLanguage.PYTHON,
        True,
    ),
    (
        AutomationFramework.SELENIUM,
        AutomationLanguage.JAVA,
        True,
    ),
    (
        AutomationFramework.SELENIUM,
        AutomationLanguage.JAVASCRIPT,
        True,
    ),
    (
        AutomationFramework.PLAYWRIGHT,
        AutomationLanguage.PYTHON,
        True,
    ),
    (
        AutomationFramework.PLAYWRIGHT,
        AutomationLanguage.JAVA,
        True,
    ),
    (
        AutomationFramework.PLAYWRIGHT,
        AutomationLanguage.JAVASCRIPT,
        True,
    ),
    (
        AutomationFramework.APPIUM,
        AutomationLanguage.PYTHON,
        True,
    ),
    (
        AutomationFramework.APPIUM,
        AutomationLanguage.JAVA,
        True,
    ),
    (
        AutomationFramework.APPIUM,
        AutomationLanguage.JAVASCRIPT,
        True,
    ),
    (
        AutomationFramework.CYPRESS,
        AutomationLanguage.PYTHON,
        False,
    ),
    (
        AutomationFramework.CYPRESS,
        AutomationLanguage.JAVA,
        False,
    ),
    (
        AutomationFramework.CYPRESS,
        AutomationLanguage.JAVASCRIPT,
        True,
    ),
]


def main():
    passed = 0
    failed = 0

    print("=" * 60)
    print("FRAMEWORK / LANGUAGE VALIDATION")
    print("=" * 60)

    for framework, language, should_pass in SUPPORTED:

        combination = (
            f"{framework.value} + {language.value}"
        )

        try:
            validate_framework_language(
                framework,
                language,
            )

            actual_pass = True

        except ValueError as exc:
            actual_pass = False

            print(
                f"{combination:<40} "
                f"REJECTED: {exc}"
            )

        expected = should_pass

        if actual_pass == expected:
            print(
                f"{combination:<40} "
                f"PASS"
            )
            passed += 1
        else:
            print(
                f"{combination:<40} "
                f"FAIL"
            )
            failed += 1

    print("=" * 60)
    print(f"PASSED = {passed}")
    print(f"FAILED = {failed}")
    print("=" * 60)

    if failed:
        raise SystemExit(1)

    print("FRAMEWORK_LANGUAGE_VALIDATION_OK")


if __name__ == "__main__":
    main()