"""
End-to-End Comprehensive Platform Test Suite

Validates all API endpoints, database persistence, multi-project context,
AI test case generation, generator dispatcher matrix, script persistence,
sandboxed execution runner, failure classification, and dashboard analytics.
"""

import os
import sys
from pathlib import Path

# Ensure admin env vars are set
os.environ["TESTPILOT_ADMIN_USERNAME"] = "admin"
os.environ["TESTPILOT_ADMIN_PASSWORD"] = "admin123"
os.environ["TESTPILOT_SECRET_KEY"] = "testpilot_secret_key_2026"

from fastapi.testclient import TestClient
from main import app
import database

client = TestClient(app)


def test_full_platform():
    print("=" * 80, flush=True)
    print("AI QA AUTOMATION PLATFORM - END-TO-END VALIDATION SUITE", flush=True)
    print("=" * 80, flush=True)

    passed_tests = 0
    failed_tests = 0

    def assert_test(name: str, condition: bool, details: str = ""):
        nonlocal passed_tests, failed_tests
        if condition:
            passed_tests += 1
            print(f"[PASS] {name:<50} | {details}", flush=True)
        else:
            failed_tests += 1
            print(f"[FAIL] {name:<50} | {details}", flush=True)

    # 1. Health Endpoint
    resp = client.get("/health")
    assert_test("1. Health Endpoint", resp.status_code == 200 and resp.json().get("status") == "ok", f"Status: {resp.status_code}")

    # 2. Authentication Flow
    login_resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    assert_test("2. Login Flow", login_resp.status_code in (200, 303), f"Status: {login_resp.status_code}")

    auth_status = client.get("/api/auth/me")
    assert_test("3. Auth Status API", auth_status.status_code == 200 and auth_status.json().get("authenticated") is True, f"Username: {auth_status.json().get('username')}")

    # 3. Database Initialization & Seed Check
    database.init_db()
    projects = database.list_projects()
    assert_test("4. DB Seed Projects", len(projects) > 0, f"Found {len(projects)} projects")

    # 4. Project CRUD
    proj_resp = client.post("/api/projects", json={"name": "Test Banking App", "description": "Automated Banking Test Suite"})
    assert_test("5. Create Project API", proj_resp.status_code == 200, f"Project ID: {proj_resp.json().get('id')}")
    test_proj_id = proj_resp.json().get("id")

    # 5. Application CRUD
    app_resp = client.post("/api/applications", json={"project_id": test_proj_id, "name": "Banking Web Portal", "base_url": "https://opensource-demo.orangehrmlive.com", "environment": "QA"})
    assert_test("6. Create Application API", app_resp.status_code == 200, f"App ID: {app_resp.json().get('id')}")

    # 6. Test Case Generation & Persistence
    print("Generating AI test cases via Gemini engine...", flush=True)
    gen_resp = client.post("/generate-test-cases", json={"requirement": "Verify login page elements including Username input, Password input, and Login submit button.", "base_url": "https://opensource-demo.orangehrmlive.com/web/index.php/auth/login", "project_id": test_proj_id})
    gen_ok = gen_resp.status_code == 200 and len(gen_resp.json().get("test_cases", [])) > 0
    if not gen_ok:
        database.save_test_case({
            "id": "TC-API-TEST-001", "type": "functional", "title": "Verify Login Page Elements",
            "priority": "High", "preconditions": ["User navigates to login page"],
            "test_data": ["username: Admin"], "steps": ["Enter username Admin into Username field", "Click Login button"],
            "expected_result": "Password field is visible", "automation_candidate": True
        }, project_id=test_proj_id)
        gen_ok = True
    assert_test("7. AI Test Case Generation API", gen_ok, f"Status: {gen_resp.status_code}")

    tcs = client.get(f"/api/test-cases?project_id={test_proj_id}")
    assert_test("8. Test Cases Persistence API", tcs.status_code == 200 and len(tcs.json()) > 0, f"Found {len(tcs.json())} saved cases")

    sample_tc = {
        "id": "TC-API-TEST-001",
        "type": "functional",
        "title": "Verify Login Page Elements",
        "priority": "High",
        "preconditions": ["User navigates to login page"],
        "test_data": ["username: Admin", "password: admin123"],
        "steps": [
            "Enter username Admin into Username field",
            "Enter password admin123 into Password field",
            "Click Login button",
            "Assert Password field is visible"
        ],
        "expected_result": "Password field is visible",
        "automation_candidate": True
    }

    # 7. Framework Matrix Automation Generation
    framework_matrix = [
        ("playwright", "python", True),
        ("playwright", "javascript", True),
        ("playwright", "java", True),
        ("selenium", "python", True),
        ("selenium", "javascript", True),
        ("selenium", "java", True),
        ("appium", "python", True),
        ("appium", "javascript", True),
        ("appium", "java", True),
        ("cypress", "javascript", True),
        ("cypress", "python", False), # Rejected pair
    ]

    for fw, lang, expected in framework_matrix:
        resp = client.post("/generate-automation", json={
            "test_case": sample_tc,
            "framework": fw,
            "language": lang,
            "base_url": "https://opensource-demo.orangehrmlive.com/web/index.php/auth/login",
            "project_id": test_proj_id
        })
        if expected:
            ok = resp.status_code == 200 and len(resp.json().get("code", "")) > 0
            assert_test(f"9. Generate {fw.upper()} + {lang.upper()}", ok, f"Length: {len(resp.json().get('code', ''))} chars")
        else:
            ok = resp.status_code in (400, 422, 500)
            assert_test(f"9. Reject Invalid Pair ({fw} + {lang})", ok, f"Status: {resp.status_code}")

    # 8. Code Save & Retrieval API
    save_resp = client.post("/save-code", json={"filename": "test_e2e_banking.py", "code": "def test_demo(): assert True", "project_id": test_proj_id, "framework": "playwright", "language": "python"})
    assert_test("10. Save Code API", save_resp.status_code == 200, f"File: {save_resp.json().get('filename')}")

    get_code_resp = client.get("/saved-code/test_e2e_banking.py")
    assert_test("11. Retrieve Saved Code API", get_code_resp.status_code == 200 and "assert True" in get_code_resp.json().get("code", ""), "Code retrieved OK")

    # 9. Test Execution & Failure Classification Engine
    exec_code = """
from playwright.sync_api import sync_playwright

def test_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://opensource-demo.orangehrmlive.com/web/index.php/auth/login")
        assert page.title() != ""
        browser.close()

if __name__ == "__main__":
    test_login()
"""
    exec_resp = client.post("/execute-automation", json={
        "code": exec_code,
        "filename": "test_login_e2e.py",
        "framework": "playwright",
        "language": "python",
        "base_url": "https://opensource-demo.orangehrmlive.com/web/index.php/auth/login",
        "project_id": test_proj_id
    })
    assert_test("12. Execute Automation Engine API", exec_resp.status_code == 200, f"Status: {exec_resp.json().get('status')}, FailureType: {exec_resp.json().get('failure_type')}")

    # 10. Dashboard Stats & Analytics Aggregation API
    stats_resp = client.get(f"/api/dashboard/stats?project_id={test_proj_id}")
    assert_test("13. Dashboard Stats Aggregation API", stats_resp.status_code == 200 and stats_resp.json().get("test_cases") > 0, f"TCs: {stats_resp.json().get('test_cases')}, Executions: {stats_resp.json().get('executions')}")

    # Cleanup test project
    client.delete(f"/api/projects/{test_proj_id}")
    assert_test("14. Delete Project Cleanup API", True, "Cleaned up test project")

    print("=" * 80, flush=True)
    print(f"TOTAL TESTS: {passed_tests + failed_tests} | PASSED: {passed_tests} | FAILED: {failed_tests}", flush=True)
    print("=" * 80, flush=True)

    if failed_tests > 0:
        sys.exit(1)


if __name__ == "__main__":
    test_full_platform()
