import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(__file__))

from automation_service import generate_automation

PATIENT_REGISTRATION_TEST_CASE = {
    "id": "TC-REG-001",
    "type": "functional",
    "title": "Patient Registration and Record Verification Flow",
    "priority": "High",
    "preconditions": [
        "Deployed With Recent Code Build",
        "User is logged in as Registration Staff"
    ],
    "test_data": [
        "patient_name: John Doe",
        "dob: 1990-01-01",
        "gender: Male"
    ],
    "steps": [
        "Open app",
        "Login as Registration Staff",
        "Click Patient Registration link",
        "Enter patient details into Patient Details form",
        "Click Register button",
        "Verify success notification",
        "Capture Patient ID from Patient ID label",
        "Search Patient ID in Search input",
        "Verify record row"
    ],
    "expected_result": "Patient record created successfully with unique identity creation and query readiness",
    "automation_candidate": True
}

def test_patient_registration_flow_playwright_python():
    res = generate_automation(
        test_case=PATIENT_REGISTRATION_TEST_CASE,
        framework="playwright",
        language="python",
        base_url="https://hospital-app.example.com"
    )
    code = res["code"]
    print("--- PLAYWRIGHT PYTHON CODE ---")
    print(code)
    
    # 1. Precondition must NOT become a locator
    assert "Logged in as Registration Staff" not in code, "Precondition string should not be converted to a locator"
    assert "Deployed With Recent Code Build" not in code, "Environment precondition should not be converted to a locator"
    
    # 2. Expected result prose must NOT become a locator
    assert "unique identity creation and query readiness" not in code, "Expected result prose should not be converted to a locator"
    
    # 3. Capture step must produce variable assignment
    assert "patient_id =" in code, "Capture action should produce patient_id variable assignment"
    
    # 4. Search step must pass patient_id variable (not string literal)
    assert ".fill(patient_id)" in code, "Search action should pass patient_id variable to fill"

def test_patient_registration_flow_selenium_python():
    res = generate_automation(
        test_case=PATIENT_REGISTRATION_TEST_CASE,
        framework="selenium",
        language="python",
        base_url="https://hospital-app.example.com"
    )
    code = res["code"]
    print("--- SELENIUM PYTHON CODE ---")
    print(code)
    
    # 1. Precondition check
    assert "Logged in as Registration Staff" not in code
    
    # 2. Expected result check
    assert "unique identity creation and query readiness" not in code
    
    # 3. Capture check
    assert "patient_id =" in code
    
    # 4. Search check
    assert "send_keys(patient_id)" in code

def test_patient_registration_flow_playwright_javascript():
    res = generate_automation(
        test_case=PATIENT_REGISTRATION_TEST_CASE,
        framework="playwright",
        language="javascript",
        base_url="https://hospital-app.example.com"
    )
    code = res["code"]
    print("--- PLAYWRIGHT JAVASCRIPT CODE ---")
    print(code)
    
    assert "Logged in as Registration Staff" not in code
    assert "patientId" in code

def test_apply_updated_contact_detail_and_save_changes():
    tc = {
        "id": "TC-CONTACT-001",
        "type": "functional",
        "title": "Update Contact Detail Test",
        "priority": "Medium",
        "steps": [
            "Open app",
            "Login as Admin",
            "Apply updated contact detail and save changes"
        ],
        "expected_result": "Contact details updated successfully",
        "automation_candidate": True
    }
    res = generate_automation(
        test_case=tc,
        framework="playwright",
        language="python",
        base_url="https://example.com"
    )
    code = res["code"]
    print("--- COMPOUND STEP CODE ---")
    print(code)
    assert "no safe locator was resolved" not in code
    assert "save" in code.lower()

def test_restore_network_connectivity_and_retry_action():
    tc = {
        "id": "TC-RETRY-001",
        "type": "functional",
        "title": "Network Error Recovery Test",
        "priority": "Medium",
        "steps": [
            "Open app",
            "Login as Admin",
            "Submit form",
            "Restore network connectivity and retry action"
        ],
        "expected_result": "Action completed successfully after retry",
        "automation_candidate": True
    }
    res = generate_automation(
        test_case=tc,
        framework="playwright",
        language="python",
        base_url="https://example.com"
    )
    code = res["code"]
    print("--- RETRY STEP CODE ---")
    print(code)
    assert "no safe locator was resolved" not in code
    assert "retry" in code.lower()

def test_execute_search_and_review_returned_list():
    tc = {
        "id": "TC-SEARCH-001",
        "type": "functional",
        "title": "Execute Search Test",
        "priority": "High",
        "steps": [
            "Open app",
            "Login as Admin",
            "Search Patient ID in Search input",
            "Execute search and review returned list"
        ],
        "expected_result": "Search results displayed with matching patient record",
        "automation_candidate": True
    }
    res = generate_automation(
        test_case=tc,
        framework="playwright",
        language="python",
        base_url="https://example.com"
    )
    code = res["code"]
    print("--- EXECUTE SEARCH CODE ---")
    print(code)
    assert "no safe locator was resolved" not in code
    assert "search" in code.lower()
    assert "returned list" in code.lower() or "returned_list" in code.lower()

def test_patient_registration_flow_selenium_java():
    tc = {
        "id": "TC-REG-002",
        "type": "functional",
        "title": "Patient Registration and Record Verification Flow",
        "priority": "High",
        "preconditions": [
            "User is logged in as Registration Staff"
        ],
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
    res = generate_automation(
        test_case=tc,
        framework="selenium",
        language="java",
        base_url="https://hospital-app.example.com"
    )
    code = res["code"]
    print("--- SELENIUM JAVA CODE ---")
    print(code)

    # 1. Package declaration
    assert "package com.hospital.tests;" in code, "Package header should be present"

    # 2. JUnit 5 Assertions
    assert "assertTrue(" in code, "JUnit 5 assertTrue assertions should be used"

    # 3. Real input literals (not System.getenv for test data literals)
    assert '"Murali"' in code, "First name literal should be present"
    assert '"Paturi"' in code, "Last name literal should be present"
    assert '"1995-01-15"' in code, "DOB literal should be present"
    assert '"Male"' in code, "Gender literal should be present"
    assert 'System.getenv("MURALI")' not in code, "Should not emit broken env vars for literals"

    # 4. JavascriptExecutor for date
    assert "JavascriptExecutor" in code, "Date input should use JavascriptExecutor"
    assert "dispatchEvent(new Event('change'" in code, "Date input should trigger change event"

    # 5. Production Locators
    assert 'By.id("firstName")' in code, "First name should resolve to By.id('firstName')"
    assert 'By.id("lastName")' in code, "Last name should resolve to By.id('lastName')"
    assert 'By.id("dob")' in code, "DOB should resolve to By.id('dob')"
    assert 'By.id("gender")' in code, "Gender should resolve to By.id('gender')"
    assert 'By.linkText("Patient Registration")' in code, "Registration link should use By.linkText"
    assert 'Register Patient' in code, "Register button should target Register Patient"

    # 6. Dropdown handling
    assert "new Select(element)" in code, "Dropdown select should instantiate Select"
    assert '.selectByVisibleText("Male")' in code, "Dropdown select should select Male by visible text"

    # 7. Step logging and comments
    assert "System.out.println(" in code, "Step logging should be present"

    # 8. Try-catch block
    assert "try {" in code, "Try block should wrap test steps"
    assert "catch (Exception e)" in code, "Catch block should catch and log exception"

    # 9. Variable reference for captured patient id
    assert "patient_id = element.getText()" in code or "capturedText = element.getText()" in code
    assert "element.sendKeys(patient_id)" in code, "Search step should send patient_id variable"

def test_patient_registration_flow_playwright_java():
    tc = {
        "id": "TC-REG-003",
        "type": "functional",
        "title": "Patient Registration Playwright Java Flow",
        "priority": "High",
        "steps": [
            "Open app",
            "Login as Registration Staff",
            "Click Patient Registration link",
            "Enter first name into First Name field",
            "Click Register Patient button"
        ],
        "test_data": [
            "first_name: Murali"
        ],
        "expected_result": "Patient record created successfully",
        "automation_candidate": True
    }
    res = generate_automation(
        test_case=tc,
        framework="playwright",
        language="java",
        base_url="https://hospital-app.example.com"
    )
    code = res["code"]
    print("--- PLAYWRIGHT JAVA CODE ---")
    print(code)
    assert '"Murali"' in code
    assert 'System.getenv("MURALI")' not in code

if __name__ == "__main__":
    test_patient_registration_flow_playwright_python()
    test_patient_registration_flow_selenium_python()
    test_patient_registration_flow_playwright_javascript()
    test_patient_registration_flow_selenium_java()
    test_patient_registration_flow_playwright_java()
    test_apply_updated_contact_detail_and_save_changes()
    test_restore_network_connectivity_and_retry_action()
    test_execute_search_and_review_returned_list()
    print("\nALL PATIENT REGISTRATION, COMPOUND STEP, RETRY & SEARCH TESTS PASSED SUCCESSFULLY!")
