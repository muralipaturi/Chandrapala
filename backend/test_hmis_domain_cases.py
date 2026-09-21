"""
HMIS Domain & Clinical Workflow Test Suite

Validates:
1. HMIS Project & Application Pre-seeding in Database (proj-hmis-001, app-hmis-001, app-hmis-002)
2. 10 Core MVP Modules Test Case Generation (Patient/UHID, OPD, EMR, Pharmacy, IPD, Emergency, Lab, Radiology, Billing, RBAC)
3. Healthcare Semantic Locator Resolution (UHID, Bed, ICD-10, Barcode, Batch, Dispense, Triage)
4. Multi-Framework Automation Dispatching (Playwright Python/JS, Selenium Python, Cypress JS) for HMIS scenarios
5. End-to-End API Persistence for HMIS Project
"""

import os
import sys
from pathlib import Path

# Ensure admin env vars
os.environ["TESTPILOT_ADMIN_USERNAME"] = "admin"
os.environ["TESTPILOT_ADMIN_PASSWORD"] = "admin123"
os.environ["TESTPILOT_SECRET_KEY"] = "testpilot_secret_key_2026"

from fastapi.testclient import TestClient
from main import app
import database
from test_case_generator import generate_generic_test_cases
from automation_service import build_heuristic_fallback_resolution

client = TestClient(app)

HMIS_MODULE_PROMPTS = {
    "patient": "Patient registration and unique health identifier (UHID) generation with duplicate checking based on national ID and phone number.",
    "opd": "Outpatient appointment scheduling, token generation, and doctor consultation queue status management.",
    "emr": "Doctor electronic medical records consultation with vitals recording, ICD-10 clinical diagnosis, and prescription authoring.",
    "pharmacy": "Pharmacy prescription dispensing, inventory stock deduction, and expired medicine batch blocking.",
    "ipd": "Inpatient admission, ward and bed allocation, and bed status transition from Available to Occupied and Cleaning.",
    "emergency": "Emergency patient intake and triage acuity assignment with Red, Yellow, and Green priority levels.",
    "lab": "Laboratory diagnostic investigation ordering, sample specimen barcode accessioning, and critical value panic alerts.",
    "radiology": "Radiology imaging request scheduling for X-ray and CT scan with DICOM accession linking.",
    "billing": "Itemized patient billing calculation, advance deposit ledger balance, and immutable final invoice generation.",
    "rbac": "Role-based access control and separation of duties between doctor, nurse, pharmacist, billing clerk, and administrator."
}


def test_hmis_domain_full():
    print("=" * 80, flush=True)
    print("HMIS CLINICAL MODULES & DOMAIN AUTOMATION VALIDATION SUITE", flush=True)
    print("=" * 80, flush=True)

    passed_tests = 0
    failed_tests = 0

    def assert_test(name: str, condition: bool, details: str = ""):
        nonlocal passed_tests, failed_tests
        if condition:
            passed_tests += 1
            print(f"[PASS] {name:<55} | {details}", flush=True)
        else:
            failed_tests += 1
            print(f"[FAIL] {name:<55} | {details}", flush=True)

    # -------------------------------------------------------------
    # 0. Admin Authentication
    # -------------------------------------------------------------
    login_resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    assert_test("0. Admin Authentication Flow", login_resp.status_code in (200, 303), f"Status: {login_resp.status_code}")

    # -------------------------------------------------------------
    # 1. Database Initialization & Seed Verification
    # -------------------------------------------------------------
    database.init_db()
    projects = database.list_projects()
    hmis_proj = next((p for p in projects if p["id"] == "proj-hmis-001"), None)
    assert_test("1. Verify Seeded HMIS Project Exists", hmis_proj is not None, f"Found: {hmis_proj['name'] if hmis_proj else 'None'}")

    apps = database.list_applications("proj-hmis-001")
    assert_test("2. Verify HMIS Web & Mobile Applications", len(apps) >= 2, f"Found {len(apps)} apps for proj-hmis-001")

    seeded_tcs = database.list_test_cases("proj-hmis-001")
    assert_test("3. Verify Baseline HMIS Test Cases (10 Modules)", len(seeded_tcs) >= 10, f"Found {len(seeded_tcs)} test cases")

    # -------------------------------------------------------------
    # 2. Test Case Generator for all 10 HMIS Clinical Modules
    # -------------------------------------------------------------
    for mod_key, prompt in HMIS_MODULE_PROMPTS.items():
        generated = generate_generic_test_cases(prompt)
        has_cases = len(generated) >= 3
        # Check if steps or expected results contain clinical domain context
        clinical_kw = any(
            any(k in tc["title"].lower() or any(k in s.lower() for s in tc["steps"]) for k in [
                "uhid", "queue", "token", "icd", "vitals", "prescription", "batch", "expiry", 
                "ward", "bed", "triage", "emergency", "barcode", "lab", "invoice", "deposit", 
                "rbac", "role", "access", "doctor", "pharmacy", "patient", "specimen"
            ])
            for tc in generated
        )
        assert_test(f"4.{mod_key.upper()} Generation ({mod_key})", has_cases and clinical_kw, f"{len(generated)} cases generated")

    # -------------------------------------------------------------
    # 3. Healthcare Semantic Locator Resolution Heuristics
    # -------------------------------------------------------------
    healthcare_locators_to_test = [
        ("UHID", ["uhid", "UHID"]),
        ("Doctor", ["Doctor", "doctor"]),
        ("ICD-10 Diagnosis", ["Icd-10 Diagnosis", "Diagnosis"]),
        ("Medicine Batch", ["Medicine Batch", "batch"]),
        ("Dispense", ["Dispense", "button"]),
        ("Bed", ["Bed", "bed"]),
        ("Admit Patient", ["Admit", "button"]),
        ("Triage Category", ["Triage Category", "triage_category", "triage"]),
        ("Specimen Barcode", ["Specimen Barcode", "barcode", "Scan Specimen Barcode"]),
        ("Collect Deposit", ["Collect Deposit", "Deposit", "button", "Pay"])
    ]

    for target_name, expected_terms in healthcare_locators_to_test:
        resolved = build_heuristic_fallback_resolution(target_name)
        values = [resolved.locator.value] if resolved.locator else []
        for c in resolved.candidates:
            values.append(c.value)
        has_match = any(any(term.lower() in str(val).lower() for term in expected_terms) for val in values)
        assert_test(f"5. Locator: {target_name}", resolved.found and has_match, f"Strategy: {resolved.locator.strategy if resolved.locator else ''}, Val: {resolved.locator.value if resolved.locator else ''}")

    # -------------------------------------------------------------
    # 4. Multi-Framework Automation Generation for HMIS Case
    # -------------------------------------------------------------
    hmis_sample_tc = {
        "id": "TC-HMIS-TEST-EMR",
        "type": "functional",
        "title": "Verify ICD-10 Clinical Diagnosis and Prescription Authoring",
        "priority": "Critical",
        "preconditions": ["Doctor is logged in with clinical credentials", "Patient UHID-2026-8801 is loaded"],
        "test_data": ["ICD-10: J06.9 (Acute upper respiratory infection)", "Rx: Amoxicillin 500mg TID"],
        "steps": [
            "Enter diagnosis code J06.9 into ICD-10 Diagnosis field",
            "Select diagnosis Acute upper respiratory infection from dropdown",
            "Enter medicine Amoxicillin 500mg into Prescription field",
            "Click Authorize Prescription button",
            "Assert Prescription status is Authorized"
        ],
        "expected_result": "Prescription status is Authorized and added to patient clinical timeline",
        "automation_candidate": True
    }

    frameworks = [
        ("playwright", "python"),
        ("playwright", "javascript"),
        ("selenium", "python"),
        ("cypress", "javascript")
    ]

    for fw, lang in frameworks:
        resp = client.post("/generate-automation", json={
            "test_case": hmis_sample_tc,
            "framework": fw,
            "language": lang,
            "base_url": "https://hospital.example.com/emr",
            "project_id": "proj-hmis-001"
        })
        code = resp.json().get("code", "") if resp.status_code == 200 else ""
        ok = resp.status_code == 200 and len(code) > 100
        has_domain_term = "J06.9" in code or "Amoxicillin" in code or "Prescription" in code
        assert_test(f"6. Automation Script: {fw.upper()} + {lang.upper()}", ok and has_domain_term, f"Length: {len(code)} chars")

    # -------------------------------------------------------------
    # 5. HMIS Test Case API Generation & Persistence
    # -------------------------------------------------------------
    gen_api_resp = client.post("/generate-test-cases", json={
        "requirement": "Hospital Emergency Triage Red Bay Assignment: Nurse inputs vital signs, heart rate 145 bpm, SpO2 88%. System flags Red Acuity and assigns immediate Resuscitation Bay.",
        "base_url": "https://hospital.example.com/emergency",
        "project_id": "proj-hmis-001"
    })
    api_ok = gen_api_resp.status_code == 200 and len(gen_api_resp.json().get("test_cases", [])) > 0
    assert_test("7. HMIS API Test Generation & Auto-Persistence", api_ok, f"Generated {len(gen_api_resp.json().get('test_cases', [])) if api_ok else 0} cases")

    # Verify project dashboard stats update
    stats_resp = client.get("/api/dashboard/stats?project_id=proj-hmis-001")
    stats_ok = stats_resp.status_code == 200 and stats_resp.json().get("test_cases", 0) >= 10
    assert_test("8. HMIS Dashboard Metrics Aggregation", stats_ok, f"Total Cases in HMIS: {stats_resp.json().get('test_cases')}")

    print("=" * 80, flush=True)
    print(f"HMIS SUITE SUMMARY: {passed_tests + failed_tests} TESTS | {passed_tests} PASSED | {failed_tests} FAILED", flush=True)
    print("=" * 80, flush=True)

    if failed_tests > 0:
        sys.exit(1)


if __name__ == "__main__":
    test_hmis_domain_full()
