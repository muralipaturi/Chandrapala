from __future__ import annotations

import asyncio
import base64
import os
import re
import shutil
import tempfile
import secrets
from pathlib import Path
from typing import Any

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
# DATABASE & MODEL IMPORTS
# ============================================================

import database

from models import (
    RequirementRequest,
    RequirementCreate,
    TestCase,
    TestCaseResponse,
    TestCaseSaveRequest,
    AutomationRequest,
    ExecutionRequest,
    ProjectCreate,
    ApplicationCreate,
    DashboardStatsResponse,
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
    title="QA Bot Platform",
    description="AI-Powered Test Case & Automation Engineering Platform",
    version="5.0.0",
)


# ============================================================
# AUTHENTICATION / SECURITY CONFIGURATION
# ============================================================

TESTPILOT_ADMIN_USERNAME = os.getenv(
    "TESTPILOT_ADMIN_USERNAME",
    "admin",
)

TESTPILOT_ADMIN_PASSWORD = os.getenv(
    "TESTPILOT_ADMIN_PASSWORD",
    "admin123",
)

TESTPILOT_SECRET_KEY = os.getenv(
    "TESTPILOT_SECRET_KEY",
    "testpilot_secret_key_2026",
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

TESTPILOT_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "TESTPILOT_ALLOWED_ORIGINS",
        "*",
    ).split(",")
    if origin.strip()
]

if TESTPILOT_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=TESTPILOT_ALLOWED_ORIGINS if TESTPILOT_ALLOWED_ORIGINS != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )


# ============================================================
# AUTHENTICATION PATHS
# ============================================================

PUBLIC_PATHS = {
    "/login",
    "/logout",
    "/health",
    "/favicon.ico",
    "/style.css",
    "/script.js",
    "/api/auth/login",
    "/api/auth/status",
}

AUTHENTICATED_API_PREFIXES = (
    "/generate-test-cases",
    "/generate-automation",
    "/execute-automation",
    "/run-automation",
    "/save-code",
    "/saved-code/",
    "/api/",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated") is True


# ============================================================
# AUTHENTICATION MIDDLEWARE
# ============================================================

@app.middleware("http")
async def authentication_middleware(request: Request, call_next):
    path = request.url.path

    if path in PUBLIC_PATHS or path == "/":
        return await call_next(request)

    # Allow static asset files
    if any(path.endswith(ext) for ext in (".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".map")):
        return await call_next(request)

    if is_authenticated(request):
        return await call_next(request)

    accept = request.headers.get("accept", "")
    wants_html = "text/html" in accept

    if path.startswith(AUTHENTICATED_API_PREFIXES) or not wants_html:
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Authentication required.",
                "login": "/login",
            },
            headers={"WWW-Authenticate": "Session"},
        )

    return RedirectResponse(url="/login", status_code=303)


app.add_middleware(
    SessionMiddleware,
    secret_key=TESTPILOT_SECRET_KEY,
    session_cookie="testpilot_session",
    max_age=60 * 60 * 24,
    same_site="lax",
    https_only=False,
)


# ============================================================
# LOGIN PAGE & API AUTH
# ============================================================

def login_page(error: str = "") -> str:
    error_html = f'<div class="error">{error}</div>' if error else ""
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>QA Bot - Login</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc;
        }}
        .card {{
            width: min(420px, calc(100% - 32px)); background: #1e293b; padding: 36px; border-radius: 16px;
            box-shadow: 0 20px 50px rgba(0,0,0,.5); border: 1px solid #334155;
        }}
        h1 {{ margin: 0 0 8px; font-size: 26px; color: #38bdf8; display: flex; align-items: center; gap: 10px; }}
        p {{ color: #94a3b8; line-height: 1.5; font-size: 14px; margin-bottom: 24px; }}
        label {{ display: block; margin: 16px 0 6px; font-weight: 600; font-size: 14px; color: #cbd5e1; }}
        input {{
            width: 100%; padding: 12px 14px; border: 1px solid #475569; border-radius: 8px;
            font-size: 15px; background: #0f172a; color: #fff; outline: none; transition: border 0.2s;
        }}
        input:focus {{ border-color: #38bdf8; }}
        button {{
            width: 100%; margin-top: 24px; padding: 12px; border: 0; border-radius: 8px;
            background: linear-gradient(135deg, #0284c7, #2563eb); color: white; font-size: 15px; font-weight: 700; cursor: pointer;
        }}
        button:hover {{ opacity: 0.95; }}
        .error {{ margin-top: 14px; color: #f87171; background: rgba(239, 68, 68, 0.1); padding: 10px; border-radius: 8px; border: 1px solid rgba(239, 68, 68, 0.2); font-size: 14px; }}
    </style>
</head>
<body>
    <main class="card">
        <h1><span>⚡</span> QA Bot</h1>
        <p>Sign in to access AI Test Generation, Automation & Analytics.</p>
        <form method="post" action="/login">
            <label for="username">Username</label>
            <input id="username" name="username" type="text" autocomplete="username" required autofocus placeholder="admin">
            <label for="password">Password</label>
            <input id="password" name="password" type="password" autocomplete="current-password" required placeholder="••••••••">
            <button type="submit">Sign In</button>
            {error_html}
        </form>
    </main>
</body>
</html>"""


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(login_page())


@app.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    username_ok = secrets.compare_digest(username.strip(), TESTPILOT_ADMIN_USERNAME)
    password_ok = secrets.compare_digest(password.strip(), TESTPILOT_ADMIN_PASSWORD)

    if not (username_ok and password_ok):
        return HTMLResponse(login_page("Invalid username or password."), status_code=401)

    request.session.clear()
    request.session["authenticated"] = True
    request.session["username"] = TESTPILOT_ADMIN_USERNAME
    return RedirectResponse(url="/", status_code=303)


@app.post("/logout")
@app.post("/api/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "success", "message": "Logged out successfully."}


@app.get("/auth/status")
@app.get("/api/auth/status")
@app.get("/api/auth/me")
async def auth_status(request: Request):
    return {
        "authenticated": is_authenticated(request),
        "username": request.session.get("username", "admin"),
        "role": "admin",
    }


# ============================================================
# PATHS & DIRECTORIES
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

FRONTEND_CANDIDATES = [
    PROJECT_DIR / "frontend",
    BACKEND_DIR / "frontend",
    PROJECT_DIR,
    BACKEND_DIR,
]


def find_frontend_directory() -> Path | None:
    for directory in FRONTEND_CANDIDATES:
        if directory.exists() and (directory / "index.html").exists():
            return directory
    return None


FRONTEND_DIR = find_frontend_directory()

UPLOAD_DIR = BACKEND_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


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
    screenshots: list[ScreenshotInfo]
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
    automation_analysis: dict[str, Any] = Field(default_factory=dict)


class ExecutionReport(BaseModel):
    test_case_id: str = ""
    steps: int = 0
    assertions: int = 0
    browser: str = ""


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
    failure_type: str = "NONE"
    report: ExecutionReport = ExecutionReport()


# ============================================================
# URL NORMALIZATION & OCR
# ============================================================

def normalize_url(url: str) -> str:
    url = str(url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    return url


def extract_ocr_text(image_path: Path) -> str:
    if Image is None or pytesseract is None:
        return ""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return (text or "").strip()
    except Exception:
        return ""


async def save_screenshot(upload: UploadFile) -> tuple[Path, int]:
    filename = Path(upload.filename or "screenshot.png").name
    allowed_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    extension = Path(filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported screenshot format: {extension}. Allowed formats: " + ", ".join(sorted(allowed_extensions)),
        )

    upload_directory = Path(tempfile.mkdtemp(prefix="testpilot_upload_", dir=str(UPLOAD_DIR)))
    file_path = upload_directory / filename
    content = await upload.read()

    if not content:
        shutil.rmtree(upload_directory, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Screenshot '{filename}' is empty.")

    max_size = 10 * 1024 * 1024
    if len(content) > max_size:
        shutil.rmtree(upload_directory, ignore_errors=True)
        raise HTTPException(status_code=413, detail=f"Screenshot '{filename}' is larger than 10 MB.")

    file_path.write_bytes(content)
    return file_path, len(content)


def build_screenshot_context(screenshots: list[ScreenshotInfo]) -> str:
    if not screenshots:
        return "No screenshots were provided."
    sections = []
    for screenshot in screenshots:
        if screenshot.ocr_text:
            sections.append(f"SCREENSHOT: {screenshot.filename}\nVISIBLE UI TEXT:\n{screenshot.ocr_text}")
        else:
            sections.append(f"SCREENSHOT: {screenshot.filename}\nImage uploaded successfully. OCR text was unavailable.")
    return "\n\n".join(sections)


# ============================================================
# PROJECT & APPLICATION API ENDPOINTS
# ============================================================

@app.get("/api/projects")
async def get_projects():
    return database.list_projects()


@app.post("/api/projects")
async def create_project(req: ProjectCreate):
    return database.create_project(name=req.name, description=req.description)


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    success = database.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success", "message": "Project deleted"}


@app.get("/api/applications")
async def get_applications(project_id: str | None = None):
    return database.list_applications(project_id)


@app.post("/api/applications")
async def create_application(req: ApplicationCreate):
    return database.create_application(
        project_id=req.project_id,
        name=req.name,
        base_url=normalize_url(req.base_url),
        environment=req.environment,
    )


@app.delete("/api/applications/{app_id}")
async def delete_application(app_id: str):
    success = database.delete_application(app_id)
    if not success:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"status": "success", "message": "Application deleted"}


# ============================================================
# DASHBOARD STATS API
# ============================================================

@app.get("/api/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(project_id: str | None = None):
    stats = database.get_dashboard_stats(project_id)
    return DashboardStatsResponse(**stats)


# ============================================================
# TEST CASES MANAGEMENT API
# ============================================================

@app.get("/api/test-cases")
async def get_test_cases(project_id: str | None = None):
    return database.list_test_cases(project_id)


@app.post("/api/test-cases")
async def save_test_case_endpoint(req: TestCaseSaveRequest):
    tc_dict = req.test_case.model_dump()
    return database.save_test_case(tc_dict, project_id=req.project_id)


@app.delete("/api/test-cases/{tc_id}")
async def delete_test_case(tc_id: str):
    success = database.delete_test_case(tc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test case not found")
    return {"status": "success", "message": "Test case deleted"}


@app.delete("/api/test-cases-purge")
async def purge_test_cases_endpoint(project_id: str = "proj-default-001"):
    deleted_count = database.purge_test_cases(project_id)
    return {"status": "success", "deleted_count": deleted_count}


# ============================================================
# EXECUTION HISTORY API
# ============================================================

@app.get("/api/executions")
async def get_execution_history(project_id: str | None = None, limit: int = 50):
    return database.list_execution_history(project_id=project_id, limit=limit)


@app.delete("/api/executions/{exec_id}")
async def delete_execution_record(exec_id: str):
    success = database.delete_execution_history(exec_id)
    if not success:
        raise HTTPException(status_code=404, detail="Execution record not found")
    return {"status": "success", "message": "Execution record deleted"}


# ============================================================
# BASIC TEST CASE GENERATION
# ============================================================

@app.post("/generate-test-cases", response_model=TestCaseResponse)
async def generate_test_cases_endpoint(request: RequirementRequest) -> TestCaseResponse:
    try:
        test_cases = await asyncio.to_thread(
            generate_ai_test_cases,
            requirement=request.requirement,
            base_url=normalize_url(request.base_url),
            screenshot_context=request.screenshot_context,
        )
        # Automatically persist generated test cases into SQLite database
        for tc in test_cases:
            database.save_test_case(tc.model_dump(), project_id=request.project_id)

        return TestCaseResponse(test_cases=test_cases)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Test case generation failed: " + str(exc),
        )


# ============================================================
# REQUIREMENT + URL + SCREENSHOTS GENERATION
# ============================================================

@app.post("/generate-test-cases-with-context", response_model=ContextGenerationResponse)
async def generate_test_cases_with_context(
    requirement: str = Form(...),
    base_url: str = Form(default=""),
    project_id: str = Form(default="proj-default-001"),
    screenshots: list[UploadFile] | None = File(default=None),
) -> ContextGenerationResponse:

    requirement = (requirement or "").strip()
    base_url = normalize_url(base_url) if base_url and base_url.strip() else ""

    if not requirement:
        raise HTTPException(status_code=400, detail="Requirement cannot be empty.")

    screenshot_infos: list[ScreenshotInfo] = []
    saved_files: list[Path] = []

    try:
        if screenshots is None:
            screenshots = []

        if len(screenshots) > 5:
            raise HTTPException(status_code=400, detail="A maximum of 5 screenshots can be uploaded.")

        for screenshot in screenshots:
            file_path, file_size = await save_screenshot(screenshot)
            saved_files.append(file_path)
            ocr_text = extract_ocr_text(file_path)
            screenshot_infos.append(
                ScreenshotInfo(
                    filename=screenshot.filename or "screenshot.png",
                    content_type=screenshot.content_type or "image/*",
                    size=file_size,
                    ocr_text=ocr_text,
                )
            )

        screenshot_context = build_screenshot_context(screenshot_infos)

        test_cases = await asyncio.to_thread(
            generate_ai_test_cases,
            requirement=requirement,
            base_url=base_url,
            screenshot_context=screenshot_context,
        )

        # Automatically persist generated test cases into database
        for tc in test_cases:
            database.save_test_case(tc.model_dump(), project_id=project_id)

        return ContextGenerationResponse(
            status="success",
            requirement=requirement,
            base_url=base_url,
            screenshots=screenshot_infos,
            screenshot_context=screenshot_context,
            test_cases=test_cases,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Context-aware test generation failed: " + str(exc),
        )
    finally:
        directories = set()
        for file_path in saved_files:
            try:
                directories.add(file_path.parent)
            except Exception:
                pass
        for directory in directories:
            shutil.rmtree(directory, ignore_errors=True)


# ============================================================
# AUTOMATION GENERATION ENDPOINT
# ============================================================

@app.post("/generate-automation", response_model=AutomationResponse)
async def generate_automation_endpoint(request: AutomationRequest) -> AutomationResponse:
    try:
        normalized_base_url = normalize_url(request.base_url)
        test_case_data = request.test_case.model_dump()

        result = await asyncio.to_thread(
            generate_automation,
            test_case_data,
            request.framework,
            request.language,
            normalized_base_url,
        )

        # Save generated code into persistent DB
        filename = result.get("filename", "test_generated.py")
        code = result.get("code", "")
        if code:
            database.save_automation_script(
                filename=filename,
                code=code,
                framework=request.framework,
                language=request.language,
                test_case_id=request.test_case.id,
                project_id=request.project_id,
            )

        return AutomationResponse(**result)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Automation generation failed: " + str(exc))


# ============================================================
# AUTOMATION EXECUTION ENDPOINT
# ============================================================

@app.post("/execute-automation", response_model=ExecutionResponse)
@app.post("/run-automation", response_model=ExecutionResponse)
async def execute_automation_endpoint(request: ExecutionRequest) -> ExecutionResponse:
    try:
        normalized_base_url = normalize_url(request.base_url)

        result = execute_automation(
            code=request.code,
            filename=request.filename,
            framework=request.framework,
            language=request.language,
            base_url=normalized_base_url,
        )

        report = ExecutionReport(
            test_case_id=request.test_case_id,
            steps=request.steps,
            assertions=request.assertions,
            browser=request.browser,
        )

        result["report"] = report

        # Record execution in persistent SQLite DB
        database.record_execution(
            framework=request.framework,
            language=request.language,
            filename=request.filename,
            status=result.get("status", "FAILED"),
            duration=result.get("duration", 0.0),
            return_code=result.get("return_code", -1),
            output=result.get("output", ""),
            errors=result.get("errors", ""),
            failure_type=result.get("failure_type", "NONE"),
            base_url=normalized_base_url,
            test_case_id=request.test_case_id,
            script_id=request.script_id or None,
            project_id=request.project_id,
            report_meta=report.model_dump(),
        )

        return ExecutionResponse(**result)

    except Exception as exc:
        error_msg = "Execution endpoint error: " + str(exc)
        database.record_execution(
            framework=request.framework,
            language=request.language,
            filename=request.filename,
            status="FAILED",
            duration=0.0,
            return_code=-1,
            output="",
            errors=error_msg,
            failure_type="ENVIRONMENT_FAILURE",
            base_url=request.base_url,
            test_case_id=request.test_case_id,
            project_id=request.project_id,
        )
        return ExecutionResponse(
            status="FAILED",
            framework=request.framework,
            language=request.language,
            duration=0.0,
            output="",
            errors=error_msg,
            filename=request.filename,
            base_url=request.base_url,
            return_code=-1,
            timed_out=False,
            failure_type="ENVIRONMENT_FAILURE",
        )


# ============================================================
# SAVE & RETRIEVE CODE ENDPOINTS
# ============================================================

class SaveCodeRequest(BaseModel):
    filename: str
    code: str
    project_id: str = "proj-default-001"
    framework: str = "playwright"
    language: str = "python"
    test_case_id: str | None = None


class SaveCodeResponse(BaseModel):
    status: str
    filename: str
    message: str


@app.post("/save-code", response_model=SaveCodeResponse)
async def save_code(request: SaveCodeRequest) -> SaveCodeResponse:
    filename = Path(request.filename).name
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    # Save to disk directory
    saved_directory = BACKEND_DIR / "generated_tests"
    saved_directory.mkdir(parents=True, exist_ok=True)
    file_path = saved_directory / filename

    try:
        file_path.resolve().relative_to(saved_directory.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_path.write_text(request.code, encoding="utf-8")

    # Save to persistent database
    database.save_automation_script(
        filename=filename,
        code=request.code,
        framework=request.framework,
        language=request.language,
        test_case_id=request.test_case_id,
        project_id=request.project_id,
    )

    return SaveCodeResponse(
        status="success",
        filename=filename,
        message=f"Code saved successfully to database and {file_path}",
    )


@app.get("/saved-code/{filename}")
async def get_saved_code(filename: str):
    filename = Path(filename).name
    script = database.get_automation_script(filename)
    if script:
        return {"status": "success", "filename": filename, "code": script["code"]}

    saved_directory = BACKEND_DIR / "generated_tests"
    file_path = saved_directory / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Saved code not found.")

    return {"status": "success", "filename": filename, "code": file_path.read_text(encoding="utf-8")}


@app.delete("/saved-code/{filename}")
async def delete_saved_code(filename: str):
    filename = Path(filename).name
    saved_directory = BACKEND_DIR / "generated_tests"
    file_path = saved_directory / filename
    if file_path.exists():
        file_path.unlink()
    return {"status": "success", "message": f"{filename} deleted successfully."}


# ============================================================
# HEALTH & ROUTING
# ============================================================

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="QA Bot Platform",
        version="5.0.0",
    )


@app.get("/")
async def root():
    frontend = find_frontend_directory()
    if frontend is None:
        return {
            "status": "ok",
            "service": "QA Bot Platform",
            "message": "Backend is running, but frontend index.html was not found.",
            "docs": "/docs",
        }
    NO_CACHE_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    return FileResponse(frontend / "index.html", headers=NO_CACHE_HEADERS)


@app.get("/favicon.ico")
async def favicon():
    frontend = find_frontend_directory()
    if frontend is not None:
        fav = frontend / "favicon.ico"
        if fav.exists():
            return FileResponse(fav)
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/{filename:path}")
async def frontend_file(filename: str):
    if any(filename.startswith(p) for p in ("generate", "execute", "run", "health", "api", "save")):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    frontend = find_frontend_directory()
    if frontend is None:
        raise HTTPException(status_code=404, detail="Frontend index.html was not found.")

    requested_file = frontend / filename
    try:
        requested_file.resolve().relative_to(frontend.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid file path.")

    NO_CACHE_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    if requested_file.is_file():
        return FileResponse(requested_file, headers=NO_CACHE_HEADERS)

    index_file = frontend / "index.html"
    if index_file.exists():
        return FileResponse(index_file, headers=NO_CACHE_HEADERS)

    raise HTTPException(status_code=404, detail="Frontend index.html was not found.")


# ============================================================
# STARTUP & LOCAL EXECUTION
# ============================================================

@app.on_event("startup")
async def startup_event():
    database.init_db()
    print("\n" + "=" * 60)
    print("=== QA BOT PLATFORM STARTED ===")
    print("=" * 60)
    print(f"Backend: {BACKEND_DIR}")
    print(f"Database: {database.DB_FILE}")
    if FRONTEND_DIR:
        print(f"Frontend: {FRONTEND_DIR}")
    print("Application: http://127.0.0.1:8000")
    print("Login: http://127.0.0.1:8000/login")
    print("Swagger: http://127.0.0.1:8000/docs")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
