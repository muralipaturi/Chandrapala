import os
import sys
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

# Ensure admin password and secret key env vars are set for main import
os.environ["TESTPILOT_ADMIN_PASSWORD"] = os.environ.get("TESTPILOT_ADMIN_PASSWORD", "admin123")
os.environ["TESTPILOT_SECRET_KEY"] = os.environ.get("TESTPILOT_SECRET_KEY", "secretkey123")

from main import app

client = TestClient(app)

URL = "https://opensource-demo.orangehrmlive.com/web/index.php/auth/login"

SAMPLE_TEST_CASE = {
    "id": "TC-API-TEST-001",
    "type": "functional",
    "title": "Verify Login Page Elements",
    "priority": "High",
    "preconditions": ["User navigates to login page"],
    "test_data": ["username: Admin", "password: admin123"],
    "steps": [
        "Enter username into Username field",
        "Enter password into Password field",
        "Click Login button",
        "Assert Password field is visible"
    ],
    "expected_result": "Password field is visible",
    "automation_candidate": True
}

ROUTES = [
    ("selenium", "python", True),
    ("selenium", "java", True),
    ("selenium", "javascript", True),
    ("playwright", "python", True),
    ("playwright", "java", True),
    ("playwright", "javascript", True),
    ("appium", "python", True),
    ("appium", "java", True),
    ("appium", "javascript", True),
    ("cypress", "javascript", True),
    ("cypress", "python", False), # Rejected combination
    ("cypress", "java", False),   # Rejected combination
]

def test_api_generate_automation_routes():
    print("=" * 75)
    print("FASTAPI /generate-automation ENDPOINT END-TO-END VALIDATION")
    # Authenticate admin session
    login_resp = client.post("/login", data={"username": "admin", "password": os.environ["TESTPILOT_ADMIN_PASSWORD"]})
    print(f"AUTHENTICATION STATUS: {login_resp.status_code}")

    passed = 0
    failed = 0

    for framework, language, expected_success in ROUTES:
        route_name = f"{framework.upper()} + {language.upper()}"
        
        payload = {
            "test_case": SAMPLE_TEST_CASE,
            "framework": framework,
            "language": language,
            "base_url": URL
        }

        try:
            response = client.post("/generate-automation", json=payload)

            if expected_success:
                if response.status_code == 200:
                    data = response.json()
                    code = data.get("code", "")
                    generator = data.get("generator_name", "")
                    if code.strip():
                        print(f"[{route_name:<30}] STATUS: 200 OK | GENERATOR: {generator:<30} | SUCCESS")
                        passed += 1
                    else:
                        print(f"[{route_name:<30}] FAIL: Code output was empty")
                        failed += 1
                else:
                    print(f"[{route_name:<30}] FAIL: HTTP {response.status_code} - {response.text}")
                    failed += 1
            else:
                if response.status_code in [400, 422, 500]:
                    print(f"[{route_name:<30}] EXPECTED REJECTION: HTTP {response.status_code} | SUCCESS")
                    passed += 1
                else:
                    print(f"[{route_name:<30}] FAIL: Expected rejection, but got HTTP {response.status_code}")
                    failed += 1

        except Exception as exc:
            print(f"[{route_name:<30}] EXCEPTION: {exc}")
            failed += 1

    print("=" * 75)
    print(f"TOTAL TESTED: {len(ROUTES)} | PASSED: {passed} | FAILED: {failed}")
    print("=" * 75)

    if failed > 0:
        sys.exit(1)
    else:
        print("FASTAPI_GENERATE_AUTOMATION_ENDPOINT_VALIDATED_OK")

if __name__ == "__main__":
    test_api_generate_automation_routes()
