import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from automation_service import generate_automation

tc = {
    "id": "TC-VERIFY-001",
    "type": "functional",
    "title": "Hospital Patient Registration Realistic Grounding",
    "priority": "High",
    "preconditions": ["User is logged in as Registration Staff"],
    "test_data": [
        "first_name: Murali",
        "last_name: Paturi",
        "dob: 1995-01-15",
        "gender: Male"
    ],
    "steps": [
        "Open app",
        "Login as Registration Staff",
        "Click Patient Registration link",
        "Enter patient details into Patient Details form",
        "Click Register Patient button",
        "Verify success notification",
        "Capture Patient ID from Patient ID label",
        "Search Patient ID in Search input",
        "Verify record row"
    ],
    "expected_result": "Patient record created successfully",
    "automation_candidate": True
}

def test_grounding_verification():
    # 1. Selenium Java Verification
    sel_res = generate_automation(tc, framework="selenium", language="java", base_url="https://hospital-app.example.com")
    sel_code = sel_res["code"]
    print("=== SELENIUM JAVA GENERATION ===")
    print(sel_code)

    assert "package com.hospital.tests;" in sel_code, "Missing package declaration"
    assert 'System.out.println("Launching Chrome Browser...");' in sel_code, "Missing chrome launch log"
    assert "try {" in sel_code and "finally {" in sel_code and "driver.quit();" in sel_code, "Missing try-finally cleanup"
    assert '"Murali"' in sel_code, "Missing Murali literal"
    assert '"Paturi"' in sel_code, "Missing Paturi literal"
    assert '"1995-01-15"' in sel_code, "Missing 1995-01-15 literal"
    assert '"Male"' in sel_code, "Missing Male literal"
    assert 'System.getenv("MURALI")' not in sel_code, "Emitted broken env var for literal"
    assert 'By.id("firstName")' in sel_code, "Missing By.id firstName"
    assert 'By.id("lastName")' in sel_code, "Missing By.id lastName"
    assert 'By.id("dob")' in sel_code, "Missing By.id dob"
    assert 'By.id("gender")' in sel_code, "Missing By.id gender"
    assert 'By.linkText("Patient Registration")' in sel_code, "Missing By.linkText"
    assert 'Register Patient' in sel_code, "Missing Register Patient button"
    assert 'JavascriptExecutor' in sel_code and 'dispatchEvent' in sel_code, "Missing JavascriptExecutor date script"
    assert 'new Select(element)' in sel_code and '.selectByVisibleText("Male");' in sel_code, "Missing Select dropdown"
    assert 'assertTrue(' in sel_code, "Missing assertTrue"
    assert 'patient_id' in sel_code, "Missing patient_id variable"

    # 2. Playwright Java Verification
    pw_res = generate_automation(tc, framework="playwright", language="java", base_url="https://hospital-app.example.com")
    pw_code = pw_res["code"]
    print("=== PLAYWRIGHT JAVA GENERATION ===")
    print(pw_code)

    assert "package com.hospital.tests;" in pw_code, "Missing package declaration in Playwright Java"
    assert '"Murali"' in pw_code, "Missing Murali literal in Playwright Java"
    assert 'System.getenv("MURALI")' not in pw_code, "Emitted broken env var in Playwright Java"

    print("\nALL GROUNDING VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_grounding_verification()
