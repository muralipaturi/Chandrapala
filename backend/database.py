"""
TestPilot AI - SQLite Database Layer

Provides thread-safe persistent storage using Python's stdlib sqlite3.
Stores Projects, Applications, Requirements, Test Cases, Automation Scripts,
Execution History, and Users so that all application data survives backend
restarts and browser refreshes.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Database path
DB_DIR = Path(__file__).resolve().parent
DB_FILE = DB_DIR / "testpilot.db"


def get_connection() -> sqlite3.Connection:
    """Returns a thread-safe connection to the SQLite database with WAL enabled."""
    conn = sqlite3.connect(str(DB_FILE), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db() -> None:
    """Initializes database tables and default seed data if database is new."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Projects Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )

        # Applications Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                base_url TEXT DEFAULT '',
                environment TEXT DEFAULT 'QA',
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )

        # Requirements Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS requirements (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                application_id TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )

        # Test Cases Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_cases (
                id TEXT PRIMARY KEY,
                tc_code TEXT NOT NULL,
                project_id TEXT NOT NULL,
                requirement_id TEXT,
                type TEXT DEFAULT 'functional',
                title TEXT NOT NULL,
                priority TEXT DEFAULT 'Medium',
                preconditions_json TEXT DEFAULT '[]',
                test_data_json TEXT DEFAULT '[]',
                steps_json TEXT DEFAULT '[]',
                expected_result TEXT DEFAULT '',
                automation_candidate INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )

        # Automation Scripts Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_scripts (
                id TEXT PRIMARY KEY,
                test_case_id TEXT,
                project_id TEXT NOT NULL,
                framework TEXT NOT NULL,
                language TEXT NOT NULL,
                filename TEXT NOT NULL,
                code TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )

        # Execution History Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_history (
                id TEXT PRIMARY KEY,
                script_id TEXT,
                test_case_id TEXT,
                project_id TEXT,
                framework TEXT NOT NULL,
                language TEXT NOT NULL,
                filename TEXT NOT NULL,
                base_url TEXT DEFAULT '',
                duration REAL DEFAULT 0.0,
                return_code INTEGER DEFAULT 0,
                output TEXT DEFAULT '',
                errors TEXT DEFAULT '',
                failure_type TEXT DEFAULT 'NONE',
                status TEXT NOT NULL,
                report_json TEXT DEFAULT '{}',
                executed_at TEXT NOT NULL
            );
            """
        )

        # Users Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'admin',
                created_at TEXT NOT NULL
            );
            """
        )

        conn.commit()

        # Seed default project if empty
        cursor.execute("SELECT COUNT(*) as count FROM projects")
        if cursor.fetchone()["count"] == 0:
            now = datetime.now(timezone.utc).isoformat()
            default_proj_id = "proj-default-001"
            cursor.execute(
                "INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (default_proj_id, "E-Commerce QA Automation", "Default QA Platform Project for Web and Mobile Testing", now)
            )

            default_app_id = "app-default-001"
            cursor.execute(
                "INSERT INTO applications (id, project_id, name, base_url, environment, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (default_app_id, default_proj_id, "Customer Portal", "https://opensource-demo.orangehrmlive.com/web/index.php/auth/login", "QA", now)
            )

            cursor.execute(
                "INSERT INTO users (id, username, role, created_at) VALUES (?, ?, ?, ?)",
                ("usr-admin-001", "admin", "admin", now)
            )

            conn.commit()

        # Seed Hospital Management Information System (HMIS) project & baseline test cases
        cursor.execute("SELECT id FROM projects WHERE id = 'proj-hmis-001'")
        if not cursor.fetchone():
            now = datetime.now(timezone.utc).isoformat()
            hmis_proj_id = "proj-hmis-001"
            cursor.execute(
                "INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (
                    hmis_proj_id,
                    "Hospital Management Information System (HMIS)",
                    "Enterprise Multi-Branch Hospital Platform (CRD Baseline v1.0, August 2026)",
                    now,
                ),
            )
            cursor.execute(
                "INSERT INTO applications (id, project_id, name, base_url, environment, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("app-hmis-001", hmis_proj_id, "HMIS Clinical & Operations Web Portal", "https://opensource-demo.orangehrmlive.com", "QA", now),
            )
            cursor.execute(
                "INSERT INTO applications (id, project_id, name, base_url, environment, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("app-hmis-002", hmis_proj_id, "HMIS Patient Portal & Mobile App", "https://opensource-demo.orangehrmlive.com", "QA", now),
            )
            conn.commit()
            _seed_hmis_baseline_test_cases(conn, hmis_proj_id, now)


def _seed_hmis_baseline_test_cases(conn: sqlite3.Connection, project_id: str, now: str) -> None:
    """Seeds baseline enterprise test cases for the 10 HMIS MVP modules into SQLite."""
    baseline_cases = [
        (
            "TC-HMIS-001",
            "TC-HMIS-001",
            project_id,
            "CRD-PAT-08-01",
            "Functional",
            "Patient Registration & Unique UHID Generation with Duplicate Detection",
            "Critical",
            json.dumps(["Receptionist is authenticated in Front Desk Portal", "Existing database has active patient directory"]),
            json.dumps(["first_name: John", "last_name: Doe", "dob: 1988-04-12", "gender: Male", "blood_group: O+", "phone: +1-555-019-2834", "allergies: Penicillin"]),
            json.dumps([
                "Navigate to Patient Registration module",
                "Enter First Name with John",
                "Enter Last Name with Doe",
                "Enter Date of Birth with 1988-04-12",
                "Select Gender with Male",
                "Select Blood Group with O+",
                "Enter Phone Number with +1-555-019-2834",
                "Enter Allergies with Penicillin",
                "Click Save Patient Registration button"
            ]),
            "Patient record created with unique permanent UHID (UHID-2026-XXXX) and duplicate phone check passes",
            1,
            now
        ),
        (
            "TC-HMIS-002",
            "TC-HMIS-002",
            project_id,
            "CRD-OPD-09-01",
            "Workflow",
            "OPD Appointment Booking, Slot Reservation and Queue Token Generation",
            "High",
            json.dumps(["Patient registered with valid UHID", "Dr. Robert Smith has active OPD schedule"]),
            json.dumps(["uhid: UHID-2026-1044", "department: Cardiology", "doctor: Dr. Robert Smith", "appointment_date: 2026-09-15", "slot: 10:30 AM"]),
            json.dumps([
                "Navigate to OPD Appointment Booking module",
                "Enter Patient UHID with UHID-2026-1044",
                "Select Department with Cardiology",
                "Select Doctor with Dr. Robert Smith",
                "Select Appointment Date with 2026-09-15",
                "Select Available Slot with 10:30 AM",
                "Click Confirm Appointment button"
            ]),
            "Appointment confirmed with queue Token #14 issued and status marked as Confirmed",
            1,
            now
        ),
        (
            "TC-HMIS-003",
            "TC-HMIS-003",
            project_id,
            "CRD-EMR-12-01",
            "Functional",
            "Doctor Clinical Consultation, Vitals Tracking and ICD-10 Diagnosis Entry",
            "Critical",
            json.dumps(["Physician is authenticated", "Patient checked in to active OPD consultation queue"]),
            json.dumps(["blood_pressure: 120/80", "pulse: 72", "temperature: 98.6", "chief_complaint: Chest tightness", "icd10: I20.9 (Angina pectoris)"]),
            json.dumps([
                "Open patient consultation encounter from OPD Queue",
                "Enter Blood Pressure with 120/80",
                "Enter Pulse Rate with 72",
                "Enter Temperature with 98.6",
                "Enter Chief Complaint with Chest tightness for 2 days",
                "Select ICD-10 Diagnosis with I20.9",
                "Click Save and Finalize Consultation button"
            ]),
            "Consultation saved to patient longitudinal medical record with immutable version timestamp",
            1,
            now
        ),
        (
            "TC-HMIS-004",
            "TC-HMIS-004",
            project_id,
            "CRD-PHARM-13-01",
            "Functional",
            "Pharmacy Prescription Review, Batch Expiry Verification and Stock Deduction",
            "Critical",
            json.dumps(["Electronic prescription issued by doctor", "Pharmacy has active stock for Amoxicillin 500mg"]),
            json.dumps(["prescription_id: RX-2026-8812", "medicine: Amoxicillin 500mg", "quantity: 20", "batch: BATCH-AMX-901"]),
            json.dumps([
                "Navigate to Pharmacy Dispensing module",
                "Search Prescription with RX-2026-8812",
                "Select Medicine Item with Amoxicillin 500mg",
                "Select Batch with BATCH-AMX-901",
                "Enter Dispensed Quantity with 20",
                "Click Dispense and Update Inventory button"
            ]),
            "Prescription status updated to Dispensed, pharmacy stock decremented by 20, and stock movement logged",
            1,
            now
        ),
        (
            "TC-HMIS-005",
            "TC-HMIS-005",
            project_id,
            "CRD-IPD-10-01",
            "Workflow",
            "IPD Patient Admission, Ward/Bed Allocation and Bed Status Transitions",
            "High",
            json.dumps(["Patient has doctor admission order", "General Ward A has Bed-GW-102 Available"]),
            json.dumps(["uhid: UHID-2026-1044", "ward: General Ward A", "bed: Bed-GW-102", "attending_physician: Dr. Sarah Connor"]),
            json.dumps([
                "Navigate to IPD Inpatient Admission module",
                "Enter Patient UHID with UHID-2026-1044",
                "Select Ward with General Ward A",
                "Select Bed with Bed-GW-102",
                "Select Attending Physician with Dr. Sarah Connor",
                "Click Confirm Admission button"
            ]),
            "IPD Admission record created, bed status transitions from Available to Occupied",
            1,
            now
        ),
        (
            "TC-HMIS-006",
            "TC-HMIS-006",
            project_id,
            "CRD-EMERG-11-01",
            "Functional",
            "Emergency Rapid Triage Categorization (Red/Immediate) and Bay Assignment",
            "Critical",
            json.dumps(["Emergency workstation active"]),
            json.dumps(["triage_color: Red (Immediate)", "chief_complaint: Severe trauma / unconscious", "spO2: 85%", "pulse: 130"]),
            json.dumps([
                "Open Emergency Admission Quick Entry module",
                "Select Triage Category with Red (Immediate)",
                "Enter Chief Complaint with Severe trauma",
                "Enter SpO2 with 85",
                "Enter Pulse with 130",
                "Click Assign Trauma Bay button"
            ]),
            "Emergency encounter generated, trauma resuscitation alert triggered, patient assigned to Trauma Bay 1",
            1,
            now
        ),
        (
            "TC-HMIS-007",
            "TC-HMIS-007",
            project_id,
            "CRD-LAB-14-01",
            "Functional",
            "Laboratory Investigation Ordering, Specimen Barcoding and Critical Result Alert",
            "High",
            json.dumps(["Lab test ordered by doctor", "Specimen collected"]),
            json.dumps(["test_name: Serum Potassium", "barcode: BAR-POT-1102", "potassium_result: 6.8 mEq/L (Critical High)"]),
            json.dumps([
                "Navigate to Laboratory Sample Collection module",
                "Scan Specimen Barcode with BAR-POT-1102",
                "Enter Potassium Result with 6.8",
                "Click Save Result button"
            ]),
            "System flags result in Red as Critical and sends immediate notification alert to attending doctor",
            1,
            now
        ),
        (
            "TC-HMIS-008",
            "TC-HMIS-008",
            project_id,
            "CRD-BILL-17-01",
            "Functional",
            "Hospital Itemized Billing, Payment Receipt and Financial Audit Immutability",
            "Critical",
            json.dumps(["Patient has unbilled consultation and pharmacy charges"]),
            json.dumps(["uhid: UHID-2026-1044", "consultation_charge: 150.00", "pharmacy_charge: 45.50", "total: 195.50", "mode: Credit Card"]),
            json.dumps([
                "Navigate to Hospital Billing and Invoices module",
                "Enter Patient UHID with UHID-2026-1044",
                "Click Generate Consolidated Invoice button",
                "Verify itemized charges include Consultation ($150) and Pharmacy ($45.50)",
                "Select Payment Mode with Credit Card",
                "Enter Payment Amount with 195.50",
                "Click Process Payment and Print Receipt button"
            ]),
            "Invoice marked Paid, receipt generated, outstanding balance zero, record locked against direct edits",
            1,
            now
        ),
        (
            "TC-HMIS-009",
            "TC-HMIS-009",
            project_id,
            "CRD-SEC-05-01",
            "Security",
            "Role-Based Access Control: Pharmacist Restricted from Editing Clinical Diagnoses",
            "Critical",
            json.dumps(["Active user with role 'Pharmacist'"]),
            json.dumps(["username: pharmacist_mike", "target_url: /doctor/clinical-notes"]),
            json.dumps([
                "Login as pharmacist with credentials pharmacist_mike",
                "Attempt to access Doctor Consultation Clinical Notes page",
                "Verify edit buttons are disabled or access returns 403 Forbidden"
            ]),
            "Access denied, pharmacist prevented from altering clinical diagnosis, audit violation logged",
            1,
            now
        ),
        (
            "TC-HMIS-010",
            "TC-HMIS-010",
            project_id,
            "CRD-NOTIF-21-01",
            "Integration",
            "Automated Appointment Confirmation and Reminder Dispatch via SMS/Email",
            "Medium",
            json.dumps(["Patient has verified mobile phone and email address"]),
            json.dumps(["phone: +1-555-019-2834", "channel: SMS"]),
            json.dumps([
                "Trigger automated appointment reminder dispatch",
                "Verify SMS payload contains patient name, doctor, clinic room, and appointment time",
                "Verify delivery status confirmed in notification history log"
            ]),
            "Reminder SMS successfully queued and marked Sent in notification audit log",
            1,
            now
        ),
    ]

    for item in baseline_cases:
        conn.execute(
            """
            INSERT OR IGNORE INTO test_cases (
                id, tc_code, project_id, requirement_id, type, title, priority,
                preconditions_json, test_data_json, steps_json, expected_result,
                automation_candidate, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            item
        )
    conn.commit()


def ensure_valid_project_id(conn: sqlite3.Connection, project_id: str | None) -> str:
    """
    Ensures that the given project_id exists in the projects table.
    If empty, missing, or deleted, returns a valid existing project_id (or recreates default project).
    """
    if project_id:
        row = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row:
            return row["id"]

    row = conn.execute("SELECT id FROM projects ORDER BY created_at ASC LIMIT 1").fetchone()
    if row:
        return row["id"]

    default_proj_id = "proj-default-001"
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
        (default_proj_id, "E-Commerce QA Automation", "Default QA Platform Project", now),
    )
    conn.commit()
    return default_proj_id


# ============================================================
# PROJECTS & APPLICATIONS CRUD
# ============================================================

def list_projects() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]


def create_project(name: str, description: str = "") -> dict[str, Any]:
    proj_id = f"proj-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (proj_id, name.strip(), description.strip(), now),
        )
        conn.commit()
    return {"id": proj_id, "name": name.strip(), "description": description.strip(), "created_at": now}


def delete_project(project_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        return cursor.rowcount > 0


def list_applications(project_id: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if project_id:
            rows = conn.execute("SELECT * FROM applications WHERE project_id = ? ORDER BY created_at DESC", (project_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM applications ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]


def create_application(project_id: str, name: str, base_url: str, environment: str = "QA") -> dict[str, Any]:
    app_id = f"app-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        valid_proj_id = ensure_valid_project_id(conn, project_id)
        conn.execute(
            "INSERT INTO applications (id, project_id, name, base_url, environment, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (app_id, valid_proj_id, name.strip(), base_url.strip(), environment.strip(), now),
        )
        conn.commit()
    return {"id": app_id, "project_id": valid_proj_id, "name": name.strip(), "base_url": base_url.strip(), "environment": environment.strip(), "created_at": now}


def delete_application(application_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM applications WHERE id = ?", (application_id,))
        conn.commit()
        return cursor.rowcount > 0


# ============================================================
# TEST CASES CRUD
# ============================================================

def list_test_cases(project_id: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if project_id:
            rows = conn.execute("SELECT * FROM test_cases WHERE project_id = ? ORDER BY created_at DESC", (project_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM test_cases ORDER BY created_at DESC").fetchall()

        result = []
        for r in rows:
            d = dict(r)
            d["preconditions"] = json.loads(d.pop("preconditions_json", "[]") or "[]")
            d["test_data"] = json.loads(d.pop("test_data_json", "[]") or "[]")
            d["steps"] = json.loads(d.pop("steps_json", "[]") or "[]")
            d["automation_candidate"] = bool(d["automation_candidate"])
            result.append(d)
        return result


def save_test_case(tc_data: dict[str, Any], project_id: str = "proj-default-001", requirement_id: str | None = None) -> dict[str, Any]:
    tc_id = tc_data.get("id") or f"TC-{uuid.uuid4().hex[:6].upper()}"
    tc_code = tc_data.get("tc_code") or tc_id
    now = datetime.now(timezone.utc).isoformat()

    preconditions_json = json.dumps(tc_data.get("preconditions") or [])
    test_data_json = json.dumps(tc_data.get("test_data") or [])
    steps_json = json.dumps(tc_data.get("steps") or [])
    auto_cand = 1 if tc_data.get("automation_candidate", True) else 0

    with get_connection() as conn:
        valid_proj_id = ensure_valid_project_id(conn, project_id)
        cursor = conn.execute("SELECT id FROM test_cases WHERE id = ?", (tc_id,))
        if cursor.fetchone():
            conn.execute(
                """
                UPDATE test_cases SET
                    type = ?, title = ?, priority = ?, preconditions_json = ?,
                    test_data_json = ?, steps_json = ?, expected_result = ?,
                    automation_candidate = ?, project_id = ?
                WHERE id = ?
                """,
                (
                    tc_data.get("type", "functional"),
                    tc_data.get("title", "Untitled Test Case"),
                    tc_data.get("priority", "Medium"),
                    preconditions_json,
                    test_data_json,
                    steps_json,
                    tc_data.get("expected_result", ""),
                    auto_cand,
                    valid_proj_id,
                    tc_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO test_cases (
                    id, tc_code, project_id, requirement_id, type, title, priority,
                    preconditions_json, test_data_json, steps_json, expected_result,
                    automation_candidate, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tc_id,
                    tc_code,
                    valid_proj_id,
                    requirement_id,
                    tc_data.get("type", "functional"),
                    tc_data.get("title", "Untitled Test Case"),
                    tc_data.get("priority", "Medium"),
                    preconditions_json,
                    test_data_json,
                    steps_json,
                    tc_data.get("expected_result", ""),
                    auto_cand,
                    now,
                ),
            )
        conn.commit()

    return {
        "id": tc_id,
        "tc_code": tc_code,
        "project_id": valid_proj_id,
        "requirement_id": requirement_id,
        "type": tc_data.get("type", "functional"),
        "title": tc_data.get("title", "Untitled Test Case"),
        "priority": tc_data.get("priority", "Medium"),
        "preconditions": tc_data.get("preconditions") or [],
        "test_data": tc_data.get("test_data") or [],
        "steps": tc_data.get("steps") or [],
        "expected_result": tc_data.get("expected_result", ""),
        "automation_candidate": bool(auto_cand),
        "created_at": now,
    }


def delete_test_case(tc_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM test_cases WHERE id = ?", (tc_id,))
        conn.commit()
        return cursor.rowcount > 0


def purge_test_cases(project_id: str) -> int:
    with get_connection() as conn:
        valid_proj_id = ensure_valid_project_id(conn, project_id)
        cursor = conn.execute("DELETE FROM test_cases WHERE project_id = ?", (valid_proj_id,))
        conn.commit()
        return cursor.rowcount


# ============================================================
# AUTOMATION SCRIPTS CRUD
# ============================================================

def list_automation_scripts(project_id: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if project_id:
            rows = conn.execute("SELECT * FROM automation_scripts WHERE project_id = ? ORDER BY updated_at DESC", (project_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM automation_scripts ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]


def save_automation_script(
    filename: str,
    code: str,
    framework: str = "playwright",
    language: str = "python",
    test_case_id: str | None = None,
    project_id: str = "proj-default-001",
) -> dict[str, Any]:
    script_id = f"script-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        valid_proj_id = ensure_valid_project_id(conn, project_id)
        cursor = conn.execute("SELECT id FROM automation_scripts WHERE filename = ? AND project_id = ?", (filename, valid_proj_id))
        row = cursor.fetchone()
        if row:
            script_id = row["id"]
            conn.execute(
                """
                UPDATE automation_scripts SET
                    code = ?, framework = ?, language = ?, test_case_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (code, framework, language, test_case_id, now, script_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO automation_scripts (
                    id, test_case_id, project_id, framework, language, filename, code, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (script_id, test_case_id, valid_proj_id, framework, language, filename, code, now, now),
            )
        conn.commit()

    return {
        "id": script_id,
        "filename": filename,
        "framework": framework,
        "language": language,
        "test_case_id": test_case_id,
        "project_id": valid_proj_id,
        "updated_at": now,
    }


def get_automation_script(filename: str, project_id: str | None = None) -> dict[str, Any] | None:
    with get_connection() as conn:
        if project_id:
            row = conn.execute("SELECT * FROM automation_scripts WHERE filename = ? AND project_id = ?", (filename, project_id)).fetchone()
        else:
            row = conn.execute("SELECT * FROM automation_scripts WHERE filename = ?", (filename,)).fetchone()
        return dict(row) if row else None


# ============================================================
# EXECUTION HISTORY CRUD
# ============================================================

def record_execution(
    framework: str,
    language: str,
    filename: str,
    status: str,
    duration: float,
    return_code: int,
    output: str,
    errors: str,
    failure_type: str = "NONE",
    base_url: str = "",
    test_case_id: str | None = None,
    script_id: str | None = None,
    project_id: str = "proj-default-001",
    report_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    exec_id = f"exec-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    report_json = json.dumps(report_meta or {})

    with get_connection() as conn:
        valid_proj_id = ensure_valid_project_id(conn, project_id)
        conn.execute(
            """
            INSERT INTO execution_history (
                id, script_id, test_case_id, project_id, framework, language, filename,
                base_url, duration, return_code, output, errors, failure_type, status,
                report_json, executed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exec_id,
                script_id,
                test_case_id,
                valid_proj_id,
                framework,
                language,
                filename,
                base_url,
                duration,
                return_code,
                output,
                errors,
                failure_type,
                status,
                report_json,
                now,
            ),
        )
        conn.commit()

    return {
        "id": exec_id,
        "framework": framework,
        "language": language,
        "filename": filename,
        "status": status,
        "duration": duration,
        "return_code": return_code,
        "failure_type": failure_type,
        "executed_at": now,
    }


def list_execution_history(project_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if project_id:
            rows = conn.execute("SELECT * FROM execution_history WHERE project_id = ? ORDER BY executed_at DESC LIMIT ?", (project_id, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM execution_history ORDER BY executed_at DESC LIMIT ?", (limit,)).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            d["report"] = json.loads(d.pop("report_json", "{}") or "{}")
            results.append(d)
        return results


def delete_execution_history(exec_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM execution_history WHERE id = ?", (exec_id,))
        conn.commit()
        return cursor.rowcount > 0


# ============================================================
# DASHBOARD STATS AGGREGATION
# ============================================================

def get_dashboard_stats(project_id: str | None = None) -> dict[str, Any]:
    with get_connection() as conn:
        valid_proj_id = ensure_valid_project_id(conn, project_id) if project_id else None
        if valid_proj_id:
            tc_count = conn.execute("SELECT COUNT(*) FROM test_cases WHERE project_id = ?", (valid_proj_id,)).fetchone()[0]
            auto_count = conn.execute("SELECT COUNT(*) FROM automation_scripts WHERE project_id = ?", (valid_proj_id,)).fetchone()[0]
            exec_rows = conn.execute("SELECT status FROM execution_history WHERE project_id = ?", (valid_proj_id,)).fetchall()
            recent_execs = conn.execute("SELECT * FROM execution_history WHERE project_id = ? ORDER BY executed_at DESC LIMIT 5", (valid_proj_id,)).fetchall()
            app_row = conn.execute("SELECT name, base_url, environment FROM applications WHERE project_id = ? LIMIT 1", (valid_proj_id,)).fetchone()
        else:
            tc_count = conn.execute("SELECT COUNT(*) FROM test_cases").fetchone()[0]
            auto_count = conn.execute("SELECT COUNT(*) FROM automation_scripts").fetchone()[0]
            exec_rows = conn.execute("SELECT status FROM execution_history").fetchall()
            recent_execs = conn.execute("SELECT * FROM execution_history ORDER BY executed_at DESC LIMIT 5").fetchall()
            app_row = conn.execute("SELECT name, base_url, environment FROM applications LIMIT 1").fetchone()

        total_execs = len(exec_rows)
        passed_count = sum(1 for r in exec_rows if r["status"] == "PASSED")
        failed_count = sum(1 for r in exec_rows if r["status"] in ("FAILED", "TIMEOUT", "ERROR"))
        pass_rate = round((passed_count / total_execs * 100), 1) if total_execs > 0 else 0.0

        recent_list = []
        for r in recent_execs:
            d = dict(r)
            d["report"] = json.loads(d.pop("report_json", "{}") or "{}")
            recent_list.append(d)

        return {
            "test_cases": tc_count,
            "automations": auto_count,
            "executions": total_execs,
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": f"{pass_rate}%",
            "application": app_row["name"] if app_row else "Not Configured",
            "base_url": app_row["base_url"] if app_row else "",
            "environment": app_row["environment"] if app_row else "QA",
            "recent_executions": recent_list,
        }
