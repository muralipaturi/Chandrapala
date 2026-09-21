from __future__ import annotations

import asyncio
import base64
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import secrets

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
    HTMLResponse,
    JSONResponse,
)
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from pydantic import BaseModel, Field


# ============================================================
# TESTPILOT IMPORTS
# ============================================================

from models import (
    RequirementRequest,
    TestCase,
    TestCaseResponse,
    AutomationRequest,
    ExecutionRequest,
)

from ai_service import (
    generate_ai_test_cases,
)

from automation_service import (
    generate_automation,
)

from execution_service import (
    execute_automation,
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="QA Bot",
    description=(
        "AI Test Case Generator and "
        "Automation Generator"
    ),
    version="5.0.0",
)


# ============================================================
# AUTHENTICATION / SECURITY
# ============================================================

TESTPILOT_ADMIN_USERNAME = os.getenv(
    "TESTPILOT_ADMIN_USERNAME",
    "admin",
)

TESTPILOT_ADMIN_PASSWORD = os.getenv(
    "TESTPILOT_ADMIN_PASSWORD",
    "",
)

TESTPILOT_SECRET_KEY = os.getenv(
    "TESTPILOT_SECRET_KEY",
    "",
)


if not TESTPILOT_ADMIN_PASSWORD:
    raise RuntimeError(
        "TESTPILOT_ADMIN_PASSWORD is not configured. "
        "Set TESTPILOT_ADMIN_PASSWORD before starting TestPilot."
    )


if not TESTPILOT_SECRET_KEY:
    raise RuntimeError(
        "TESTPILOT_SECRET_KEY is not configured. "
        "Set TESTPILOT_SECRET_KEY before starting TestPilot."
    )


app.add_middleware(
    SessionMiddleware,
    secret_key=TESTPILOT_SECRET_KEY,
    session_cookie="testpilot_session",
    max_age=60 * 60 * 12,
    same_site="lax",
    https_only=False,
)


# ============================================================
# CORS
# ============================================================

TESTPILOT_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "TESTPILOT_ALLOWED_ORIGINS",
        "",
    ).split(",")
    if origin.strip()
]


if TESTPILOT_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=TESTPILOT_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
        allow_headers=[
            "Content-Type",
            "Authorization",
        ],
    )


# ============================================================
# AUTHENTICATION PATHS
# ============================================================

PUBLIC_PATHS = {
    "/login",
    "/logout",
    "/health",
    "/favicon.ico",
}


AUTHENTICATED_API_PREFIXES = (
    "/generate-test-cases",
    "/generate-automation",
    "/execute-automation",
    "/run-automation",
    "/save-code",
    "/saved-code/",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def is_authenticated(
    request: Request,
) -> bool:

    return (
        request.session.get(
            "authenticated"
        )
        is True
    )


# ============================================================
# LOGIN PAGE
# ============================================================

def login_page(
    error: str = "",
) -> str:

    error_html = (
        f'<div class="error">{error}</div>'
        if error
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>QA Bot - Login</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: Arial, sans-serif;
            background: #f5f7fb;
        }}

        .card {{
            width: min(
                420px,
                calc(100% - 32px)
            );

            background: white;
            padding: 32px;
            border-radius: 16px;
            box-shadow:
                0 12px 40px
                rgba(0,0,0,.10);
        }}

        h1 {{
            margin: 0 0 8px;
        }}

        p {{
            color: #667085;
            line-height: 1.5;
        }}

        label {{
            display: block;
            margin: 18px 0 7px;
            font-weight: 600;
        }}

        input {{
            width: 100%;
            padding: 12px;
            border: 1px solid #d0d5dd;
            border-radius: 8px;
            font-size: 15px;
        }}

        button {{
            width: 100%;
            margin-top: 22px;
            padding: 12px;
            border: 0;
            border-radius: 8px;
            background: #2563eb;
            color: white;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
        }}

        .error {{
            margin-top: 14px;
            color: #b42318;
            background: #fef3f2;
            padding: 10px;
            border-radius: 8px;
        }}
    </style>
</head>

<body>

    <main class="card">

        <h1>QA Bot</h1>

        <p>
            Sign in to access test generation
            and automation.
        </p>

        <form
            method="post"
            action="/login"
        >

            <label for="username">
                Username
            </label>

            <input
                id="username"
                name="username"
                type="text"
                autocomplete="username"
                required
                autofocus
            >

            <label for="password">
                Password
            </label>

            <input
                id="password"
                name="password"
                type="password"
                autocomplete="current-password"
                required
            >

            <button type="submit">
                Sign In
            </button>

            {error_html}

        </form>

    </main>

</body>
</html>"""


# ============================================================
# AUTHENTICATION MIDDLEWARE
# ============================================================

@app.middleware("http")
async def authentication_middleware(
    request: Request,
    call_next,
):

    path = request.url.path

    if path in PUBLIC_PATHS:
        return await call_next(request)

    if path == "/":
        return await call_next(request)

    if is_authenticated(request):
        return await call_next(request)

    accept = request.headers.get(
        "accept",
        "",
    )

    wants_html = (
        "text/html" in accept
    )

    if path.startswith(
        AUTHENTICATED_API_PREFIXES
    ) or not wants_html:

        return JSONResponse(
            status_code=401,
            content={
                "detail":
                    "Authentication required.",
                "login":
                    "/login",
            },
            headers={
                "WWW-Authenticate":
                    "Session",
            },
        )

    return RedirectResponse(
        url="/login",
        status_code=303,
    )


# ============================================================
# LOGIN
# ============================================================

@app.get(
    "/login",
    response_class=HTMLResponse,
)
async def login_get(
    request: Request,
):

    if is_authenticated(request):

        return RedirectResponse(
            url="/",
            status_code=303,
        )

    return HTMLResponse(
        login_page()
    )


@app.post(
    "/login",
    response_class=HTMLResponse,
)
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):

    username_ok = secrets.compare_digest(
        username,
        TESTPILOT_ADMIN_USERNAME,
    )

    password_ok = secrets.compare_digest(
        password,
        TESTPILOT_ADMIN_PASSWORD,
    )

    if not (
        username_ok
        and password_ok
    ):

        return HTMLResponse(
            login_page(
                "Invalid username or password."
            ),
            status_code=401,
        )

    request.session.clear()

    request.session[
        "authenticated"
    ] = True

    request.session[
        "username"
    ] = TESTPILOT_ADMIN_USERNAME

    return RedirectResponse(
        url="/",
        status_code=303,
    )


@app.post("/logout")
async def logout(
    request: Request,
):

    request.session.clear()

    return {
        "status":
            "success",
        "message":
            "Logged out successfully.",
    }


@app.get("/auth/status")
async def auth_status(
    request: Request,
):

    return {
        "authenticated":
            is_authenticated(request),
        "username":
            request.session.get(
                "username"
            ),
    }


# ============================================================
# PATHS
# ============================================================

BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

PROJECT_DIR = (
    BACKEND_DIR.parent
)


# ============================================================
# FRONTEND DIRECTORIES
# ============================================================

FRONTEND_CANDIDATES = [
    PROJECT_DIR / "frontend",
    BACKEND_DIR / "frontend",
    PROJECT_DIR,
    BACKEND_DIR,
]


def find_frontend_directory() -> Path | None:

    for directory in FRONTEND_CANDIDATES:

        if not directory.exists():
            continue

        index_file = (
            directory / "index.html"
        )

        if index_file.exists():
            return directory

    return None


FRONTEND_DIR = (
    find_frontend_directory()
)


# ============================================================
# UPLOAD DIRECTORY
# ============================================================

UPLOAD_DIR = (
    BACKEND_DIR / "uploads"
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# OPTIONAL OCR
# ============================================================

try:

    from PIL import Image

except ImportError:

    Image = None


try:

    import pytesseract

except ImportError:

    pytesseract = None


# ============================================================
# STATIC FILES
# ============================================================

if FRONTEND_DIR is not None:

    STATIC_DIR = FRONTEND_DIR

else:

    STATIC_DIR = BACKEND_DIR


# ============================================================
# RESPONSE MODELS
# ============================================================

class HealthResponse(BaseModel):

    status: str
    service: str
    version: str


class ScreenshotInfo(BaseModel):

    filename: str
    content_type: str
    size: int
    ocr_text: str = ""


class ContextGenerationResponse(BaseModel):

    status: str
    requirement: str
    base_url: str
    screenshots: list[
        ScreenshotInfo
    ]

    screenshot_context: str

    test_cases: list[TestCase]


class AutomationResponse(BaseModel):

    status: str

    test_case_id: str | None = None

    test_case_type: str | None = None

    framework: str

    language: str

    filename: str

    base_url: str

    code: str

    automation_analysis: dict[
        str,
        Any
    ] = Field(
        default_factory=dict
    )


class ExecutionResponse(BaseModel):

    status: str

    framework: str

    language: str

    duration: float

    output: str

    errors: str

    filename: str

    base_url: str = ""

    return_code: int | None = None

    timed_out: bool = False


# ============================================================
# URL NORMALIZATION
# ============================================================

def normalize_url(
    url: str,
) -> str:

    url = str(
        url or ""
    ).strip()

    if not url:
        return ""

    if not re.match(
        r"^https?://",
        url,
        re.IGNORECASE,
    ):

        url = (
            "https://"
            + url
        )

    return url


# ============================================================
# SCREENSHOT OCR
# ============================================================

def extract_ocr_text(
    image_path: Path,
) -> str:

    if (
        Image is None
        or pytesseract is None
    ):

        return ""

    try:

        image = Image.open(
            image_path
        )

        text = (
            pytesseract
            .image_to_string(
                image
            )
        )

        return (
            text or ""
        ).strip()

    except Exception:

        return ""


# ============================================================
# SAVE SCREENSHOT
# ============================================================

async def save_screenshot(
    upload: UploadFile,
) -> tuple[Path, int]:

    filename = Path(
        upload.filename
        or "screenshot.png"
    ).name

    allowed_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
    }

    extension = Path(
        filename
    ).suffix.lower()

    if extension not in (
        allowed_extensions
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported screenshot "
                f"format: {extension}. "
                "Allowed formats: "
                + ", ".join(
                    sorted(
                        allowed_extensions
                    )
                )
            ),
        )

    upload_directory = Path(
        tempfile.mkdtemp(
            prefix="testpilot_upload_",
            dir=str(
                UPLOAD_DIR
            ),
        )
    )

    file_path = (
        upload_directory
        / filename
    )

    content = await upload.read()

    if not content:

        shutil.rmtree(
            upload_directory,
            ignore_errors=True,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Screenshot '{filename}' "
                "is empty."
            ),
        )

    max_size = (
        10 * 1024 * 1024
    )

    if len(content) > max_size:

        shutil.rmtree(
            upload_directory,
            ignore_errors=True,
        )

        raise HTTPException(
            status_code=413,
            detail=(
                f"Screenshot '{filename}' "
                "is larger than 10 MB."
            ),
        )

    file_path.write_bytes(
        content
    )

    return (
        file_path,
        len(content),
    )


# ============================================================
# SCREENSHOT CONTEXT
# ============================================================

def build_screenshot_context(
    screenshots: list[
        ScreenshotInfo
    ],
) -> str:

    if not screenshots:

        return (
            "No screenshots were provided."
        )

    sections = []

    for screenshot in screenshots:

        if screenshot.ocr_text:

            sections.append(
                (
                    "SCREENSHOT: "
                    f"{screenshot.filename}\n"
                    "VISIBLE UI TEXT:\n"
                    f"{screenshot.ocr_text}"
                )
            )

        else:

            sections.append(
                (
                    "SCREENSHOT: "
                    f"{screenshot.filename}\n"
                    "Image uploaded successfully. "
                    "OCR text was unavailable."
                )
            )

    return "\n\n".join(
        sections
    )


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/health",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:

    return HealthResponse(
        status="ok",
        service="TestPilot AI",
        version="5.0.0",
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    frontend = (
        find_frontend_directory()
    )

    if frontend is None:

        return {
            "status":
                "ok",
            "service":
                "TestPilot AI",
            "message":
                (
                    "Backend is running, "
                    "but frontend index.html "
                    "was not found."
                ),
            "docs":
                "/docs",
        }

    index_file = (
        frontend / "index.html"
    )

    return FileResponse(
        index_file
    )


# ============================================================
# FAVICON
# ============================================================

@app.get("/favicon.ico")
async def favicon():

    frontend = (
        find_frontend_directory()
    )

    if frontend is not None:

        favicon = (
            frontend / "favicon.ico"
        )

        if favicon.exists():

            return FileResponse(
                favicon
            )

    raise HTTPException(
        status_code=404,
        detail="Favicon not found",
    )


# ============================================================
# STATIC FILE ROUTES
# ============================================================

@app.get("/{filename:path}")
async def frontend_file(
    filename: str,
):

    if filename.startswith(
        "generate"
    ):

        raise HTTPException(
            status_code=404,
            detail="API endpoint not found",
        )

    if filename.startswith(
        "execute"
    ):

        raise HTTPException(
            status_code=404,
            detail="API endpoint not found",
        )

    if filename.startswith(
        "health"
    ):

        raise HTTPException(
            status_code=404,
            detail="API endpoint not found",
        )

    frontend = (
        find_frontend_directory()
    )

    if frontend is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Frontend index.html "
                "was not found."
            ),
        )

    requested_file = (
        frontend / filename
    )

    try:

        requested_file.resolve().relative_to(
            frontend.resolve()
        )

    except ValueError:

        raise HTTPException(
            status_code=403,
            detail="Invalid file path.",
        )

    if requested_file.is_file():

        return FileResponse(
            requested_file
        )

    index_file = (
        frontend / "index.html"
    )

    if index_file.exists():

        return FileResponse(
            index_file
        )

    raise HTTPException(
        status_code=404,
        detail=(
            "Frontend index.html "
            "was not found."
        ),
    )


# ============================================================
# BASIC TEST CASE GENERATION
# ============================================================

@app.post(
    "/generate-test-cases",
    response_model=TestCaseResponse,
)
async def generate_test_cases(
    request: RequirementRequest,
) -> TestCaseResponse:

    try:

        test_cases = (
            generate_ai_test_cases(
                requirement=
                    request.requirement,

                base_url=
                    normalize_url(
                        request.base_url
                    ),

                screenshot_context=
                    request.screenshot_context,
            )
        )

        return TestCaseResponse(
            test_cases=test_cases
        )

    
        raise HTTPException(
            status_code=500,
            detail=(
                "Test case generation failed: "
                + str(exc)
            ),
        )


# ============================================================
# REQUIREMENT + URL + SCREENSHOTS
# ============================================================

@app.post(
    "/generate-test-cases-with-context",
    response_model=ContextGenerationResponse,
)
async def generate_test_cases_with_context(
    requirement: str = Form(...),
    base_url: str = Form(...),
    screenshots: list[
        UploadFile
    ] | None = File(
        default=None
    ),
) -> ContextGenerationResponse:

    requirement = (
        requirement or ""
    ).strip()

    base_url = normalize_url(
        base_url
    )

    if not reexcept Exception as exc:
quirement:

        raise HTTPException(
            status_code=400,
            detail=(
                "Requirement cannot be empty."
            ),
        )

    if not base_url:

        raise HTTPException(
            status_code=400,
            detail=(
                "Application URL cannot be empty."
            ),
        )

    screenshot_infos: list[
        ScreenshotInfo
    ] = []

    saved_files: list[
        Path
    ] = []

    try:

        if screenshots is None:

            screenshots = []

        if len(screenshots) > 5:

            raise HTTPException(
                status_code=400,
                detail=(
                    "A maximum of 5 screenshots "
                    "can be uploaded."
                ),
            )

        for screenshot in screenshots:

            (
                file_path,
                file_size,
            ) = await save_screenshot(
                screenshot
            )

            saved_files.append(
                file_path
            )

            ocr_text = (
                extract_ocr_text(
                    file_path
                )
            )

            screenshot_infos.append(
                ScreenshotInfo(
                    filename=(
                        screenshot.filename
                        or "screenshot.png"
                    ),

                    content_type=(
                        screenshot.content_type
                        or "image/*"
                    ),

                    size=file_size,

                    ocr_text=ocr_text,
                )
            )

        screenshot_context = (
            build_screenshot_context(
                screenshot_infos
            )
        )

        test_cases = (
            generate_ai_test_cases(
                requirement=
                    requirement,

                base_url=
                    base_url,

                screenshot_context=
                    screenshot_context,
            )
        )

        return ContextGenerationResponse(
            status="success",
            requirement=requirement,
            base_url=base_url,
            screenshots=screenshot_infos,
            screenshot_context=
                screenshot_context,
            test_cases=test_cases,
        )

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Context-aware test generation "
                "failed: "
                + str(exc)
            ),
        )

    finally:

        directories = set()

        for file_path in saved_files:

            try:

                directories.add(
                    file_path.parent
                )

            except Exception:

                pass

        for directory in directories:

            shutil.rmtree(
                directory,
                ignore_errors=True,
            )


# ============================================================
# AUTOMATION GENERATION
# ============================================================

@app.post(
    "/generate-automation",
    response_model=AutomationResponse,
)
async def generate_automation_endpoint(
    request: AutomationRequest,
) -> AutomationResponse:

    """
    Generate automation code.

    IMPORTANT:

    The automation pipeline currently uses
    synchronous Playwright APIs.

    FastAPI endpoints are asynchronous.

    Therefore the synchronous automation
    pipeline must run inside a worker thread.

    This prevents:

        Playwright Sync API inside asyncio loop

    errors.
    """

    try:

        # ----------------------------------------------------
        # Normalize URL
        # ----------------------------------------------------

        normalized_base_url = (
            normalize_url(
                request.base_url
            )
        )

        # ----------------------------------------------------
        # Convert Pydantic TestCase
        # to dictionary
        # ----------------------------------------------------

        test_case_data = (
            request.test_case.model_dump()
        )

        # ----------------------------------------------------
        # IMPORTANT
        #
        # Run the complete synchronous
        # automation pipeline in a
        # worker thread.
        # ----------------------------------------------------

        result = await asyncio.to_thread(
            generate_automation,
            test_case_data,
            request.framework,
            request.language,
            normalized_base_url,
        )

        # ----------------------------------------------------
        # Return API response
        # ----------------------------------------------------

        return AutomationResponse(
            **result
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

    import traceback

    traceback.print_exc()

    raise HTTPException(
        status_code=500,
        detail=(
            "Automation generation failed: "
            + str(exc)
        ),
    )


# ============================================================
# EXECUTION
# ============================================================

@app.post(
    "/execute-automation",
    response_model=ExecutionResponse,
)
async def execute_automation_endpoint(
    request: ExecutionRequest,
) -> ExecutionResponse:

    try:

        result = execute_automation(
            code=
                request.code,

            filename=
                request.filename,

            framework=
                request.framework,

            language=
                request.language,

            base_url=
                normalize_url(
                    request.base_url
                ),
        )

        return ExecutionResponse(
            **result
        )

    except Exception as exc:

        return ExecutionResponse(
            status="FAILED",

            framework=
                request.framework,

            language=
                request.language,

            duration=0,

            output="",

            errors=(
                "Execution endpoint error: "
                + str(exc)
            ),

            filename=
                request.filename,

            base_url=
                request.base_url,

            return_code=-1,

            timed_out=False,
        )


# ============================================================
# BACKWARD-COMPATIBLE EXECUTION ENDPOINT
# ============================================================

@app.post(
    "/run-automation",
    response_model=ExecutionResponse,
)
async def run_automation_endpoint(
    request: ExecutionRequest,
) -> ExecutionResponse:

    return await (
        execute_automation_endpoint(
            request
        )
    )


# ============================================================
# SAVE CODE
# ============================================================

class SaveCodeRequest(BaseModel):

    filename: str
    code: str


class SaveCodeResponse(BaseModel):

    status: str
    filename: str
    message: str


@app.post(
    "/save-code",
    response_model=SaveCodeResponse,
)
async def save_code(
    request: SaveCodeRequest,
) -> SaveCodeResponse:

    filename = Path(
        request.filename
    ).name

    if not filename:

        raise HTTPException(
            status_code=400,
            detail=(
                "Filename cannot be empty."
            ),
        )

    saved_directory = (
        BACKEND_DIR
        / "generated_tests"
    )

    saved_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = (
        saved_directory
        / filename
    )

    try:

        file_path.resolve().relative_to(
            saved_directory.resolve()
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    file_path.write_text(
        request.code,
        encoding="utf-8",
    )

    return SaveCodeResponse(
        status="success",
        filename=filename,
        message=(
            "Code saved successfully to "
            f"{file_path}"
        ),
    )


# ============================================================
# GET SAVED CODE
# ============================================================

@app.get(
    "/saved-code/{filename}"
)
async def get_saved_code(
    filename: str,
):

    filename = Path(
        filename
    ).name

    saved_directory = (
        BACKEND_DIR
        / "generated_tests"
    )

    file_path = (
        saved_directory
        / filename
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Saved code not found.",
        )

    return {
        "status":
            "success",

        "filename":
            filename,

        "code":
            file_path.read_text(
                encoding="utf-8"
            ),
    }


# ============================================================
# DELETE SAVED CODE
# ============================================================

@app.delete(
    "/saved-code/{filename}"
)
async def delete_saved_code(
    filename: str,
):

    filename = Path(
        filename
    ).name

    saved_directory = (
        BACKEND_DIR
        / "generated_tests"
    )

    file_path = (
        saved_directory
        / filename
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Saved code not found.",
        )

    file_path.unlink()

    return {
        "status":
            "success",

        "message":
            (
                f"{filename} "
                "deleted successfully."
            ),
    }


# ============================================================
# APPLICATION STARTUP
# ============================================================

@app.on_event(
    "startup"
)
async def startup_event():

    print()

    print(
        "=" * 60
    )

    print(
        "QA Bot STARTED"
    )

    print(
        "=" * 60
    )

    print(
        f"Backend: {BACKEND_DIR}"
    )

    if FRONTEND_DIR:

        print(
            f"Frontend: {FRONTEND_DIR}"
        )

    else:

        print(
            "Frontend: NOT FOUND"
        )

    print(
        "Login: "
        "http://127.0.0.1:8000/login"
    )

    print(
        "Swagger: "
        "http://127.0.0.1:8000/docs "
        "(authenticated)"
    )

    print(
        "Application: "
        "http://127.0.0.1:8000"
    )

    print(
        "=" * 60
    )

    print()


# ============================================================
# LOCAL EXECUTION
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
