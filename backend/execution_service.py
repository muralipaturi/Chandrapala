from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


# ============================================================
# TESTPILOT EXECUTION SERVICE
# ============================================================
#
# Executes generated automation code.
#
# Supported:
#
#   Playwright + Python
#   Selenium + Python
#   Cypress + JavaScript
#   Playwright + Java
#   Selenium + Java
#   Appium + Python
#   Appium + Java
#
# The service intentionally returns a structured response
# instead of allowing an execution exception to crash FastAPI.
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TIMEOUT_SECONDS = int(
    os.getenv(
        "TEST_EXECUTION_TIMEOUT",
        "120"
    )
)


MAX_OUTPUT_LENGTH = int(
    os.getenv(
        "MAX_TEST_OUTPUT_LENGTH",
        "50000"
    )
)


# ============================================================
# PROJECT PATHS
# ============================================================

BACKEND_DIR = Path(
    __file__
).resolve().parent


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(
    value: Any
) -> str:

    if value is None:
        return ""

    return str(value)


def truncate_output(
    value: str,
    max_length: int = MAX_OUTPUT_LENGTH
) -> str:

    value = clean_text(value)

    if len(value) <= max_length:
        return value

    return (
        value[:max_length]
        + "\n\n"
        + "[Output truncated by TestPilot]"
    )


def normalize_url(
    url: str
) -> str:

    url = clean_text(
        url
    ).strip()

    if not url:
        return ""

    if not re.match(
        r"^https?://",
        url,
        re.IGNORECASE
    ):

        url = "https://" + url

    return url


# ============================================================
# PYTHON EXECUTABLE
# ============================================================

def get_python_executable() -> str:
    """
    Always prefer the Python executable running the current
    TestPilot backend.

    This is important because your project uses:

        backend\\.venv\\Scripts\\python.exe

    and we don't want to accidentally execute generated tests
    using another Python installation.
    """

    current_python = Path(
        sys.executable
    )

    if current_python.exists():
        return str(
            current_python
        )

    return "python"


# ============================================================
# COMMAND DISCOVERY
# ============================================================

def find_command(
    *commands: str
) -> str | None:

    for command in commands:

        path = shutil.which(
            command
        )

        if path:
            return path

    return None


# ============================================================
# FRAMEWORK / LANGUAGE NORMALIZATION
# ============================================================

def normalize_framework(
    framework: str
) -> str:

    framework = clean_text(
        framework
    ).strip().lower()

    aliases = {

        "playwright":
            "playwright",

        "pw":
            "playwright",

        "selenium":
            "selenium",

        "appium":
            "appium",

        "cypress":
            "cypress"

    }

    return aliases.get(
        framework,
        framework
    )


def normalize_language(
    language: str
) -> str:

    language = clean_text(
        language
    ).strip().lower()

    aliases = {

        "py":
            "python",

        "python":
            "python",

        "java":
            "java",

        "js":
            "javascript",

        "javascript":
            "javascript"

    }

    return aliases.get(
        language,
        language
    )


# ============================================================
# FILE EXTENSION
# ============================================================

def expected_extension(
    framework: str,
    language: str
) -> str:

    framework = normalize_framework(
        framework
    )

    language = normalize_language(
        language
    )

    if framework == "cypress":

        return ".cy.js"

    if language == "java":

        return ".java"

    if language == "javascript":

        return ".js"

    return ".py"


# ============================================================
# FILENAME SANITIZATION
# ============================================================

def safe_filename(
    filename: str,
    framework: str,
    language: str
) -> str:

    filename = clean_text(
        filename
    ).strip()

    if not filename:

        filename = (
            "test_generated"
            + expected_extension(
                framework,
                language
            )
        )


    # Remove path traversal

    filename = Path(
        filename
    ).name


    # Replace unsafe characters

    filename = re.sub(
        r"[^a-zA-Z0-9_.-]",
        "_",
        filename
    )


    expected = expected_extension(
        framework,
        language
    )


    # Add extension if missing

    if not filename.lower().endswith(
        expected.lower()
    ):

        # Remove common incorrect extension

        filename = re.sub(
            r"\.(py|java|js|cy\.js)$",
            "",
            filename,
            flags=re.IGNORECASE
        )

        filename += expected


    return filename


# ============================================================
# PYTHON SYNTAX VALIDATION
# ============================================================

def validate_python_syntax(
    code: str
) -> tuple[bool, str]:

    try:

        compile(
            code,
            "<generated_test>",
            "exec"
        )

        return (
            True,
            ""
        )

    except SyntaxError as exc:

        message = (
            f"Python syntax error: "
            f"{exc.msg} "
            f"at line {exc.lineno}, "
            f"column {exc.offset}"
        )

        return (
            False,
            message
        )

    except Exception as exc:

        return (
            False,
            f"Python validation error: {exc}"
        )


# ============================================================
# NODE / CYPRESS DISCOVERY
# ============================================================

def get_node_command() -> str | None:

    return find_command(
        "node",
        "node.exe"
    )


def get_npx_command() -> str | None:

    return find_command(
        "npx",
        "npx.cmd",
        "npx.exe"
    )


# ============================================================
# JAVA DISCOVERY
# ============================================================

def get_java_command() -> str | None:

    return find_command(
        "java",
        "java.exe"
    )


def get_mvn_command() -> str | None:

    return find_command(
        "mvn",
        "mvn.cmd",
        "mvn.exe"
    )


# ============================================================
# BUILD ENVIRONMENT
# ============================================================

def build_environment(
    base_url: str = ""
) -> dict[str, str]:

    environment = os.environ.copy()


    normalized = normalize_url(
        base_url
    )


    if normalized:

        environment[
            "BASE_URL"
        ] = normalized


    # Do not hard-code credentials into the process if the
    # user has already supplied environment variables.

    environment.setdefault(
        "TEST_USERNAME",
        "Admin"
    )

    environment.setdefault(
        "TEST_PASSWORD",
        "admin123"
    )

    environment.setdefault(
        "INVALID_USERNAME",
        "invalid_user_999"
    )

    environment.setdefault(
        "INVALID_PASSWORD",
        "WrongPassword123!"
    )


    return environment


# ============================================================
# SUBPROCESS EXECUTION
# ============================================================

def run_subprocess(
    command: list[str],
    cwd: Path,
    environment: dict[str, str],
    timeout_seconds: int
) -> dict[str, Any]:

    started = time.perf_counter()


    try:

        process = subprocess.run(

            command,

            cwd=str(cwd),

            env=environment,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True,

            encoding="utf-8",

            errors="replace",

            timeout=timeout_seconds,

            shell=False

        )


        duration = (
            time.perf_counter()
            - started
        )


        stdout = truncate_output(
            process.stdout
        )

        stderr = truncate_output(
            process.stderr
        )


        return {

            "return_code":
                process.returncode,

            "stdout":
                stdout,

            "stderr":
                stderr,

            "duration":
                round(
                    duration,
                    2
                ),

            "timed_out":
                False

        }


    except subprocess.TimeoutExpired as exc:

        duration = (
            time.perf_counter()
            - started
        )


        stdout = (
            exc.stdout
            if isinstance(
                exc.stdout,
                str
            )
            else ""
        )


        stderr = (
            exc.stderr
            if isinstance(
                exc.stderr,
                str
            )
            else ""
        )


        return {

            "return_code":
                -1,

            "stdout":
                truncate_output(
                    stdout
                ),

            "stderr":
                truncate_output(
                    stderr
                ),

            "duration":
                round(
                    duration,
                    2
                ),

            "timed_out":
                True

        }


    except FileNotFoundError as exc:

        duration = (
            time.perf_counter()
            - started
        )


        return {

            "return_code":
                -1,

            "stdout":
                "",

            "stderr":
                str(exc),

            "duration":
                round(
                    duration,
                    2
                ),

            "timed_out":
                False,

            "command_not_found":
                True

        }


    except Exception as exc:

        duration = (
            time.perf_counter()
            - started
        )


        return {

            "return_code":
                -1,

            "stdout":
                "",

            "stderr":
                str(exc),

            "duration":
                round(
                    duration,
                    2
                ),

            "timed_out":
                False

        }


# ============================================================
# PYTEST EXECUTION
# ============================================================

def run_python_test(
    test_file: Path,
    work_dir: Path,
    environment: dict[str, str],
    timeout_seconds: int
) -> dict[str, Any]:

    python = get_python_executable()


    command = [

        python,

        "-m",

        "pytest",

        str(test_file),

        "-v",

        "-s"

    ]


    return run_subprocess(

        command=command,

        cwd=work_dir,

        environment=environment,

        timeout_seconds=timeout_seconds

    )


# ============================================================
# CYPRESS EXECUTION
# ============================================================

def run_cypress_test(
    test_file: Path,
    work_dir: Path,
    environment: dict[str, str],
    timeout_seconds: int
) -> dict[str, Any]:

    npx = get_npx_command()


    if not npx:

        return {

            "return_code":
                -1,

            "stdout":
                "",

            "stderr":
                (
                    "Node.js/npx is not installed "
                    "or is not available in PATH."
                ),

            "duration":
                0,

            "timed_out":
                False,

            "command_not_found":
                True

        }


    command = [

        npx,

        "cypress",

        "run",

        "--spec",

        str(test_file),

        "--headless"

    ]


    return run_subprocess(

        command=command,

        cwd=work_dir,

        environment=environment,

        timeout_seconds=timeout_seconds

    )


# ============================================================
# JAVA EXECUTION
# ============================================================

def run_java_test(
    test_file: Path,
    work_dir: Path,
    environment: dict[str, str],
    timeout_seconds: int
) -> dict[str, Any]:

    java = get_java_command()


    if not java:

        return {

            "return_code":
                -1,

            "stdout":
                "",

            "stderr":
                (
                    "Java is not installed or "
                    "JAVA_HOME/PATH is not configured."
                ),

            "duration":
                0,

            "timed_out":
                False,

            "command_not_found":
                True

        }


    mvn = get_mvn_command()


    if mvn:

        return run_subprocess(

            command=[
                mvn,
                "-q",
                "test"
            ],

            cwd=work_dir,

            environment=environment,

            timeout_seconds=timeout_seconds

        )


    return {

        "return_code":
            -1,

        "stdout":
            "",

        "stderr":
            (
                "Java is installed, but Maven is "
                "not installed/configured. "
                "Create a Maven project or "
                "configure Maven before executing "
                "Java automation."
            ),

        "duration":
            0,

        "timed_out":
            False,

        "command_not_found":
            True

    }


# ============================================================
# PREPARE WORK DIRECTORY
# ============================================================

def prepare_work_directory() -> Path:

    return Path(
        tempfile.mkdtemp(
            prefix="testpilot_"
        )
    )


# ============================================================
# WRITE GENERATED CODE
# ============================================================

def write_test_file(
    work_dir: Path,
    filename: str,
    code: str
) -> Path:

    test_dir = (
        work_dir /
        "test"
    )


    test_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    test_file = (
        test_dir /
        filename
    )


    test_file.write_text(

        code,

        encoding="utf-8"

    )


    return test_file


# ============================================================
# CREATE PYTEST CONFIGURATION
# ============================================================

def create_pytest_ini(
    work_dir: Path,
    base_url: str
) -> None:

    content = f"""[pytest]
testpaths = test
addopts = -ra
markers =
    automation: generated automation tests
base_url = {base_url}
"""

    (
        work_dir /
        "pytest.ini"
    ).write_text(

        content,

        encoding="utf-8"

    )


# ============================================================
# RESULT PARSING
# ============================================================

def determine_status(
    execution: dict[str, Any]
) -> str:

    if execution.get(
        "timed_out",
        False
    ):

        return "TIMEOUT"


    if execution.get(
        "command_not_found",
        False
    ):

        return "FAILED"


    return_code = execution.get(
        "return_code",
        -1
    )


    if return_code == 0:

        return "PASSED"


    return "FAILED"


# ============================================================
# ERROR EXPLANATION
# ============================================================

def explain_failure(
    status: str,
    execution: dict[str, Any],
    framework: str,
    language: str
) -> str:

    if status == "PASSED":

        return ""


    if status == "TIMEOUT":

        return (
            "Test execution exceeded the configured "
            "timeout. Check the application URL, "
            "network connectivity, browser startup, "
            "or application response time."
        )


    stderr = clean_text(
        execution.get(
            "stderr",
            ""
        )
    )


    stdout = clean_text(
        execution.get(
            "stdout",
            ""
        )
    )


    combined = (
        stderr +
        "\n" +
        stdout
    ).lower()


    if (
        "maven is not installed"
        in combined
    ):

        return (
            "Java automation was generated, but "
            "Maven is not installed/configured."
        )


    if (
        "java is not installed"
        in combined
    ):

        return (
            "Java automation was generated, but "
            "Java is not installed/configured."
        )


    if (
        "node.js"
        in combined
        and "not installed"
        in combined
    ):

        return (
            "Cypress automation was generated, "
            "but Node.js/npx is not installed "
            "or not available in PATH."
        )


    if (
        "invalid credentials"
        in combined
    ):

        return (
            "The application rejected the supplied "
            "credentials. Verify TEST_USERNAME and "
            "TEST_PASSWORD."
        )


    if (
        "cannot navigate to invalid url"
        in combined
    ):

        return (
            "The supplied application URL is invalid. "
            "Provide a complete URL beginning with "
            "http:// or https://."
        )


    if (
        "syntaxerror"
        in combined
        or "syntax error"
        in combined
    ):

        return (
            "The generated automation contains a "
            "syntax error. Edit the generated code "
            "before executing it."
        )


    if (
        "locator"
        in combined
        and "resolved"
        in combined
    ):

        return (
            "A generated locator did not resolve to "
            "the expected application element. "
            "Review the generated locator."
        )


    if (
        "timeout"
        in combined
    ):

        return (
            "A browser or application operation timed "
            "out. Check the URL, locator, application "
            "availability, and network connection."
        )


    if stderr:

        return stderr[-4000:]


    if stdout:

        return stdout[-4000:]


    return (
        f"{framework} {language} execution failed "
        "without a detailed error message."
    )


# ============================================================
# MAIN EXECUTION FUNCTION
# ============================================================

# ============================================================
# FAILURE CLASSIFICATION
# ============================================================

def classify_failure(
    status: str,
    execution: dict[str, Any],
) -> str:

    if status == "PASSED":
        return "NONE"

    if status == "TIMEOUT":
        return "TIMEOUT"

    combined = (
        clean_text(
            execution.get(
                "stderr",
                ""
            )
        )
        + "\n"
        + clean_text(
            execution.get(
                "stdout",
                ""
            )
        )
    ).lower()

    # --------------------------------------------------------
    # TEST DATA
    # --------------------------------------------------------

    if (
        "invalid credentials" in combined
        or "credentials" in combined
        and "rejected" in combined
    ):
        return "TEST_DATA_FAILURE"

    # --------------------------------------------------------
    # LOCATOR
    # --------------------------------------------------------

    if (
        "strict mode violation" in combined
        or "locator" in combined
        and (
            "resolved to" in combined
            or "not found" in combined
            or "timeout" in combined
        )
        or "no such element" in combined
    ):
        return "LOCATOR_FAILURE"

    # --------------------------------------------------------
    # ASSERTION
    # --------------------------------------------------------

    if (
        "assertionerror" in combined
        or "assertion error" in combined
        or "assertion failed" in combined
    ):
        return "ASSERTION_FAILURE"

    # --------------------------------------------------------
    # ENVIRONMENT
    # --------------------------------------------------------

    if (
        "maven is not installed" in combined
        or "java is not installed" in combined
        or (
            "node.js" in combined
            and "not installed" in combined
        )
    ):
        return "ENVIRONMENT_FAILURE"

    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------

    return "EXECUTION_FAILURE"


def execute_automation(
    code: str,
    filename: str = "test_generated.py",
    framework: str = "playwright",
    language: str = "python",
    base_url: str = "",
    timeout_seconds: int | None = None
) -> dict[str, Any]:
    """
    Main execution entry point used by FastAPI.

    Returns a stable JSON-compatible dictionary.
    """

    started = time.perf_counter()


    framework = normalize_framework(
        framework
    )


    language = normalize_language(
        language
    )


    base_url = normalize_url(
        base_url
    )


    code = clean_text(
        code
    )


    # ========================================================
    # BASIC VALIDATION
    # ========================================================

    if not code.strip():

        return {

            "status":
                "FAILED",

            "framework":
                framework,

            "language":
                language,

            "duration":
                0,

            "output":
                "",

            "errors":
                "Generated automation code is empty.",

            "filename":
                filename

        }


    if timeout_seconds is None:

        timeout_seconds = (
            DEFAULT_TIMEOUT_SECONDS
        )


    # ========================================================
    # SAFE FILENAME
    # ========================================================

    filename = safe_filename(

        filename,

        framework,

        language

    )


    # ========================================================
    # PYTHON SYNTAX CHECK
    # ========================================================

    if language == "python":

        syntax_ok, syntax_error = (
            validate_python_syntax(
                code
            )
        )


        if not syntax_ok:

            duration = (
                time.perf_counter()
                - started
            )


            return {

                "status":
                    "FAILED",

                "framework":
                    framework,

                "language":
                    language,

                "duration":
                    round(
                        duration,
                        2
                    ),

                "output":
                    "",

                "errors":
                    syntax_error,

                "filename":
                    filename

            }


    # ========================================================
    # CREATE TEMP DIRECTORY
    # ========================================================

    work_dir = prepare_work_directory()


    try:

        # ====================================================
        # ENVIRONMENT
        # ====================================================

        environment = build_environment(
            base_url
        )


        # ====================================================
        # WRITE TEST
        # ====================================================

        test_file = write_test_file(

            work_dir,

            filename,

            code

        )


        # ====================================================
        # PYTEST CONFIG
        # ====================================================

        if language == "python":

            create_pytest_ini(

                work_dir,

                base_url

            )


        # ====================================================
        # EXECUTE
        # ====================================================

        if language == "python":

            execution = run_python_test(

                test_file=test_file,

                work_dir=work_dir,

                environment=environment,

                timeout_seconds=timeout_seconds

            )


        elif framework == "cypress":

            execution = run_cypress_test(

                test_file=test_file,

                work_dir=work_dir,

                environment=environment,

                timeout_seconds=timeout_seconds

            )


        elif language == "java":

            execution = run_java_test(

                test_file=test_file,

                work_dir=work_dir,

                environment=environment,

                timeout_seconds=timeout_seconds

            )


        else:

            execution = {

                "return_code":
                    -1,

                "stdout":
                    "",

                "stderr":
                    (
                        f"Unsupported execution "
                        f"combination: "
                        f"{framework} + "
                        f"{language}"
                    ),

                "duration":
                    0,

                "timed_out":
                    False

            }


        # ====================================================
        # STATUS
        # ====================================================

        status = determine_status(
            execution
        )


        duration = (
            time.perf_counter()
            - started
        )


        output = truncate_output(
            execution.get(
                "stdout",
                ""
            )
        )


        errors = truncate_output(
            execution.get(
                "stderr",
                ""
            )
        )


        # ====================================================
        # FAILURE EXPLANATION
        # ====================================================

        explanation = explain_failure(

            status,

            execution,

            framework,

            language

        )


        if status != "PASSED":

            if explanation:

                if errors:

                    errors = (
                        explanation
                        + "\n\n"
                        + errors
                    )

                else:

                    errors = explanation


        # ====================================================
        # RESULT
        # ====================================================

        return {

            "status":
                status,

            "framework":
                framework,

            "language":
                language,

            "duration":
                round(
                    duration,
                    2
                ),

            "output":
                output,

            "errors":
                errors,

            "filename":
                filename,

            "base_url":
                base_url,

            "return_code":
                execution.get(
                    "return_code",
                    -1
                ),

            "timed_out":
                execution.get(
                    "timed_out",
                    False
                ),

            "failure_type":
                classify_failure(
                    status,
                    execution
                )

        }


    except Exception as exc:

        duration = (
            time.perf_counter()
            - started
        )


        return {

            "status":
                "FAILED",

            "framework":
                framework,

            "language":
                language,

            "duration":
                round(
                    duration,
                    2
                ),

            "output":
                "",

            "errors":
                (
                    "TestPilot execution error: "
                    + str(exc)
                ),

            "filename":
                filename,

            "base_url":
                base_url

        }


    finally:

        # ====================================================
        # CLEAN TEMP FILES
        # ====================================================
        #
        # The generated source is already returned to the UI,
        # so temporary execution files can safely be removed.
        #
        # ====================================================

        try:

            shutil.rmtree(
                work_dir,
                ignore_errors=True
            )

        except Exception:

            pass


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================
#
# Some earlier versions of TestPilot may call:
#
#     run_automation(...)
#
# Keep the alias so replacing this file does not break an
# existing main.py.
#
# ============================================================

def run_automation(
    code: str,
    filename: str = "test_generated.py",
    framework: str = "playwright",
    language: str = "python",
    base_url: str = "",
    timeout_seconds: int | None = None
) -> dict[str, Any]:

    return execute_automation(

        code=code,

        filename=filename,

        framework=framework,

        language=language,

        base_url=base_url,

        timeout_seconds=timeout_seconds

    )


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================

def execute_test(
    code: str,
    filename: str = "test_generated.py",
    framework: str = "playwright",
    language: str = "python",
    base_url: str = "",
    timeout_seconds: int | None = None
) -> dict[str, Any]:

    return execute_automation(

        code=code,

        filename=filename,

        framework=framework,

        language=language,

        base_url=base_url,

        timeout_seconds=timeout_seconds

    )

# ============================================================
# JAVA MAVEN FIX / OVERRIDES
# ============================================================
# These definitions intentionally appear at the end of the file.
# Python resolves the function names when execute_automation runs,
# so the improved Java implementation replaces the older one without
# changing the FastAPI-facing API.


def get_java_home() -> str | None:
    configured = os.getenv("JAVA_HOME", "").strip()
    if configured and Path(configured).exists():
        return configured

    java = get_java_command()
    if java:
        try:
            java_path = Path(java).resolve()
            if java_path.parent.name.lower() == "bin":
                candidate = java_path.parent.parent
                if candidate.exists():
                    return str(candidate)
        except Exception:
            pass

    return None


def java_dependency_xml(framework: str) -> str:
    framework = normalize_framework(framework)

    if framework == "playwright":
        return """        <dependency>
            <groupId>com.microsoft.playwright</groupId>
            <artifactId>playwright</artifactId>
            <version>1.55.0</version>
        </dependency>"""

    if framework == "appium":
        return """        <dependency>
            <groupId>io.appium</groupId>
            <artifactId>java-client</artifactId>
            <version>10.0.0</version>
        </dependency>"""

    return """        <dependency>
            <groupId>org.seleniumhq.selenium</groupId>
            <artifactId>selenium-java</artifactId>
            <version>4.35.0</version>
        </dependency>"""


def create_java_pom(work_dir: Path, framework: str) -> Path:
    dependency = java_dependency_xml(framework)

    pom = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.testpilot</groupId>
    <artifactId>testpilot-generated-test</artifactId>
    <version>1.0-SNAPSHOT</version>

    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <junit.version>5.13.4</junit.version>
    </properties>

    <dependencies>
{dependency}

        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>${{junit.version}}</version>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.14.0</version>
                <configuration>
                    <source>17</source>
                    <target>17</target>
                </configuration>
            </plugin>

            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.5.3</version>
                <configuration>
                    <useSystemClassLoader>true</useSystemClassLoader>
                    <redirectTestOutputToFile>false</redirectTestOutputToFile>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
"""

    pom_file = work_dir / "pom.xml"
    pom_file.write_text(pom, encoding="utf-8")
    return pom_file


def write_test_file(
    work_dir: Path,
    filename: str,
    code: str,
    language: str = "python",
) -> Path:
    # Maven standard layout for Java.
    if normalize_language(language) == "java":
        test_dir = work_dir / "src" / "test" / "java"
    else:
        test_dir = work_dir / "test"

    test_dir.mkdir(parents=True, exist_ok=True)

    test_file = test_dir / filename
    test_file.write_text(code, encoding="utf-8")

    return test_file


def run_java_test(
    test_file: Path,
    work_dir: Path,
    environment: dict[str, str],
    timeout_seconds: int,
    framework: str | None = None,
) -> dict[str, Any]:
    if framework is None:
        try:
            generated = test_file.read_text(encoding="utf-8")
        except Exception:
            generated = ""
        if "com.microsoft.playwright" in generated:
            framework = "playwright"
        elif "io.appium" in generated:
            framework = "appium"
        else:
            framework = "selenium"

    java = get_java_command()

    if not java:
        return {
            "return_code": -1,
            "stdout": "",
            "stderr": (
                "Java is not installed or JAVA_HOME/PATH "
                "is not configured."
            ),
            "duration": 0,
            "timed_out": False,
            "command_not_found": True,
        }

    mvn = get_mvn_command()

    if not mvn:
        return {
            "return_code": -1,
            "stdout": "",
            "stderr": (
                "Java was found, but Maven was not found. "
                "Install Maven or add Maven's bin directory "
                "to PATH."
            ),
            "duration": 0,
            "timed_out": False,
            "command_not_found": True,
        }

    # Ensure Maven receives a valid JDK environment.
    java_home = get_java_home()
    if java_home:
        environment["JAVA_HOME"] = java_home
        environment["PATH"] = (
            str(Path(java_home) / "bin")
            + os.pathsep
            + environment.get("PATH", "")
        )

    # CRITICAL FIX:
    # Create the Maven project before calling `mvn test`.
    # Maven must be executed from the directory containing pom.xml.
    pom_file = work_dir / "pom.xml"
    if not pom_file.exists():
        create_java_pom(work_dir, framework)

    if not pom_file.exists():
        return {
            "return_code": -1,
            "stdout": "",
            "stderr": (
                "Maven project setup failed: pom.xml was not "
                "created in the execution directory."
            ),
            "duration": 0,
            "timed_out": False,
        }

    command = [
        mvn,
        "-q",
        "-DskipTests=false",
        "test",
    ]

    # `cwd=work_dir` is the key fix for:
    # "The goal you specified requires a project to execute..."
    return run_subprocess(
        command=command,
        cwd=work_dir,
        environment=environment,
        timeout_seconds=timeout_seconds,
    )
