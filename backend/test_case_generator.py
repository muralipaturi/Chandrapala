def generate_test_cases(requirement: str):

    requirement_lower = requirement.lower()

    if "login" in requirement_lower:
        return generate_login_test_cases()

    return generate_generic_test_cases(requirement)


def generate_login_test_cases():

    test_cases = []

    test_cases.extend(generate_login_positive_cases())
    test_cases.extend(generate_login_negative_cases())
    test_cases.extend(generate_login_validation_cases())
    test_cases.extend(generate_login_security_cases())

    return test_cases


def generate_login_positive_cases():

    return [
        {
            "id": "TC001",
            "type": "Positive",
            "title": "Login with valid username and password",
            "steps": [
                "Open the login page",
                "Enter a valid username",
                "Enter a valid password",
                "Click the Login button"
            ],
            "expected_result": "User should be successfully logged in"
        }
    ]


def generate_login_negative_cases():

    return [
        {
            "id": "TC002",
            "type": "Negative",
            "title": "Login with invalid username and valid password",
            "steps": [
                "Open the login page",
                "Enter an invalid username",
                "Enter a valid password",
                "Click the Login button"
            ],
            "expected_result": "Login should fail and an appropriate error message should be displayed"
        },
        {
            "id": "TC003",
            "type": "Negative",
            "title": "Login with valid username and invalid password",
            "steps": [
                "Open the login page",
                "Enter a valid username",
                "Enter an invalid password",
                "Click the Login button"
            ],
            "expected_result": "Login should fail and an appropriate error message should be displayed"
        },
        {
            "id": "TC004",
            "type": "Negative",
            "title": "Login with invalid username and invalid password",
            "steps": [
                "Open the login page",
                "Enter an invalid username",
                "Enter an invalid password",
                "Click the Login button"
            ],
            "expected_result": "Login should fail"
        }
    ]


def generate_login_validation_cases():

    return [
        {
            "id": "TC005",
            "type": "Validation",
            "title": "Login with empty username",
            "steps": [
                "Open the login page",
                "Leave the username field empty",
                "Enter a valid password",
                "Click the Login button"
            ],
            "expected_result": "Username validation message should be displayed"
        },
        {
            "id": "TC006",
            "type": "Validation",
            "title": "Login with empty password",
            "steps": [
                "Open the login page",
                "Enter a valid username",
                "Leave the password field empty",
                "Click the Login button"
            ],
            "expected_result": "Password validation message should be displayed"
        },
        {
            "id": "TC007",
            "type": "Validation",
            "title": "Login with both fields empty",
            "steps": [
                "Open the login page",
                "Leave username empty",
                "Leave password empty",
                "Click the Login button"
            ],
            "expected_result": "Required field validation messages should be displayed"
        }
    ]


def generate_login_security_cases():

    return [
        {
            "id": "TC008",
            "type": "Security",
            "title": "Verify account lockout after multiple failed login attempts",
            "steps": [
                "Open the login page",
                "Enter invalid credentials repeatedly",
                "Submit the login request"
            ],
            "expected_result": "Account should be locked or further login attempts should be restricted according to the security policy"
        }
    ]


def generate_generic_test_cases(requirement: str):
    req_low = requirement.lower()

    # --------------------------------------------------------
    # HMIS: ROLE-BASED ACCESS CONTROL (RBAC) & PERMISSIONS DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["rbac", "permission", "role", "access control", "unauthorized", "super admin", "doctor portal", "pharmacist access"]):
        return [
            {
                "id": "TC-HMIS-RBAC-001",
                "tc_code": "TC-HMIS-RBAC-001",
                "type": "Security",
                "title": "Verify role isolation: Pharmacist cannot edit clinical diagnoses or doctor notes",
                "priority": "Critical",
                "preconditions": [
                    "Pharmacist user account is active with role 'Pharmacist'",
                    "Patient has active clinical diagnosis recorded by physician"
                ],
                "test_data": ["username: pharmacist_mike", "patient_id: UHID-2026-9081"],
                "steps": [
                    "Login as pharmacist with credentials pharmacist_mike",
                    "Navigate to Patient Medical Records EMR section",
                    "Attempt to click Edit Diagnosis button on consultation note",
                    "Verify edit action is restricted or denied with 403 Forbidden"
                ],
                "expected_result": "Pharmacist is prevented from modifying clinical history and audit log records access denial",
                "requirement_id": "CRD-SEC-05-01"
            },
            {
                "id": "TC-HMIS-RBAC-002",
                "tc_code": "TC-HMIS-RBAC-002",
                "type": "Security",
                "title": "Verify doctor consultation portal access restricted to authorized clinical staff",
                "priority": "High",
                "preconditions": ["User account has non-clinical role 'Receptionist'"],
                "test_data": ["username: reception_sarah"],
                "steps": [
                    "Login as receptionist with credentials reception_sarah",
                    "Attempt direct navigation to Doctor Consultation Portal /doctor/clinical-notes",
                    "Verify system redirects to front desk dashboard with unauthorized alert"
                ],
                "expected_result": "Unauthorized user is blocked from viewing sensitive clinical records",
                "requirement_id": "CRD-SEC-05-02"
            },
            {
                "id": "TC-HMIS-RBAC-003",
                "tc_code": "TC-HMIS-RBAC-003",
                "type": "Security",
                "title": "Verify billing clerk cannot access or modify laboratory diagnostic results",
                "priority": "Critical",
                "preconditions": ["User account has financial role 'Billing Clerk'"],
                "test_data": ["username: billing_clerk_01"],
                "steps": [
                    "Login as billing clerk with credentials billing_clerk_01",
                    "Attempt to open Laboratory Result Entry URL /lab/results/edit/LAB-2026-5501",
                    "Verify access denied message and security event logged"
                ],
                "expected_result": "Access denied with HTTP 403 Forbidden; separation of duties enforced",
                "requirement_id": "CRD-SEC-05-03"
            }
        ]

    # --------------------------------------------------------
    # HMIS: PATIENT MANAGEMENT & UHID DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["uhid", "patient", "demographics", "duplicate patient", "duplicate detection"]):
        return [
            {
                "id": "TC-HMIS-PAT-001",
                "tc_code": "TC-HMIS-PAT-001",
                "type": "Positive",
                "title": "Verify patient registration and unique UHID generation",
                "priority": "Critical",
                "preconditions": ["Receptionist is logged into hospital front-desk portal"],
                "test_data": [
                    "first_name: John",
                    "last_name: Doe",
                    "dob: 1988-04-12",
                    "gender: Male",
                    "blood_group: O+",
                    "phone: +1-555-019-2834",
                    "allergies: Penicillin"
                ],
                "steps": [
                    "Navigate to Patient Registration module",
                    "Enter First Name with John",
                    "Enter Last Name with Doe",
                    "Enter Date of Birth with 1988-04-12",
                    "Select Gender with Male",
                    "Select Blood Group with O+",
                    "Enter Phone Number with +1-555-019-2834",
                    "Enter Allergies with Penicillin",
                    "Click Save Patient Registration button"
                ],
                "expected_result": "Patient record saved successfully and unique permanent UHID generated (e.g. UHID-2026-XXXX)",
                "requirement_id": "CRD-PAT-08-01"
            },
            {
                "id": "TC-HMIS-PAT-002",
                "tc_code": "TC-HMIS-PAT-002",
                "type": "Negative",
                "title": "Verify duplicate patient detection by matching phone number and national ID",
                "priority": "High",
                "preconditions": ["Existing patient registered with phone +1-555-019-2834"],
                "test_data": ["phone: +1-555-019-2834", "first_name: John"],
                "steps": [
                    "Navigate to Patient Registration module",
                    "Enter Phone Number with +1-555-019-2834",
                    "Enter First Name with John",
                    "Click Check Duplicate or Save Patient button"
                ],
                "expected_result": "Duplicate Patient Warning modal displayed showing existing matching UHID and merge option",
                "requirement_id": "CRD-PAT-08-02"
            },
            {
                "id": "TC-HMIS-PAT-003",
                "tc_code": "TC-HMIS-PAT-003",
                "type": "Workflow",
                "title": "Verify emergency unidentified patient temporary UHID allocation and retrospective merge",
                "priority": "High",
                "preconditions": ["Emergency trauma intake active with unconscious unknown patient"],
                "test_data": ["temporary_name: Unknown Male - Bay 01", "estimated_age: 35"],
                "steps": [
                    "Navigate to Patient Registration module",
                    "Click Quick Emergency Intake button",
                    "Select Gender with Male",
                    "Click Generate Temporary Emergency UHID button",
                    "Assert Temporary UHID issued with prefix EMG-TEMP-"
                ],
                "expected_result": "Temporary emergency UHID generated and flagged for retrospective identification and demographic merge",
                "requirement_id": "CRD-PAT-08-03"
            }
        ]

    # --------------------------------------------------------
    # HMIS: APPOINTMENT & OPD QUEUE DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["appointment", "opd", "queue", "slot", "booking", "token"]):
        return [
            {
                "id": "TC-HMIS-OPD-001",
                "tc_code": "TC-HMIS-OPD-001",
                "type": "Positive",
                "title": "Verify OPD appointment booking, slot reservation and token generation",
                "priority": "High",
                "preconditions": ["Patient registered with UHID", "Doctor has active OPD schedule"],
                "test_data": [
                    "uhid: UHID-2026-1044",
                    "department: Cardiology",
                    "doctor: Dr. Robert Smith",
                    "appointment_date: 2026-09-15",
                    "slot: 10:30 AM"
                ],
                "steps": [
                    "Navigate to OPD Appointment Booking module",
                    "Enter Patient UHID with UHID-2026-1044",
                    "Select Department with Cardiology",
                    "Select Doctor with Dr. Robert Smith",
                    "Select Appointment Date with 2026-09-15",
                    "Select Available Slot with 10:30 AM",
                    "Click Confirm Appointment button"
                ],
                "expected_result": "Appointment confirmed, OPD queue token issued (e.g. Token #14), and status marked as Confirmed",
                "requirement_id": "CRD-OPD-09-01"
            },
            {
                "id": "TC-HMIS-OPD-002",
                "tc_code": "TC-HMIS-OPD-002",
                "type": "Validation",
                "title": "Verify double booking prevention for booked doctor slot",
                "priority": "Medium",
                "preconditions": ["Slot 10:30 AM is already reserved for another patient"],
                "test_data": ["doctor: Dr. Robert Smith", "slot: 10:30 AM"],
                "steps": [
                    "Navigate to OPD Appointment Booking module",
                    "Select Doctor with Dr. Robert Smith",
                    "Select Appointment Date with 2026-09-15",
                    "Observe slot 10:30 AM availability"
                ],
                "expected_result": "Booked slot is grayed out / disabled and cannot be selected",
                "requirement_id": "CRD-OPD-09-02"
            },
            {
                "id": "TC-HMIS-OPD-003",
                "tc_code": "TC-HMIS-OPD-003",
                "type": "Workflow",
                "title": "Verify doctor consultation queue status transition from Waiting to In-Consultation to Completed",
                "priority": "High",
                "preconditions": ["Patient checked in at OPD waiting room with Token #14"],
                "test_data": ["token: Token #14", "doctor: Dr. Robert Smith"],
                "steps": [
                    "Open OPD Live Doctor Queue dashboard",
                    "Select Patient Token #14 from Waiting list",
                    "Click Call Patient button to change status to In-Consultation",
                    "Complete clinical examination and click Finish Encounter button"
                ],
                "expected_result": "Queue status transitions sequentially from Waiting -> In-Consultation -> Completed with queue display updated",
                "requirement_id": "CRD-OPD-09-03"
            }
        ]

    # --------------------------------------------------------
    # HMIS: CLINICAL RECORDS / EMR & CONSULTATION DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["emr", "consultation", "diagnosis", "clinical notes", "vitals", "medical record"]):
        return [
            {
                "id": "TC-HMIS-EMR-001",
                "tc_code": "TC-HMIS-EMR-001",
                "type": "Positive",
                "title": "Verify doctor clinical consultation recording with ICD-10 diagnosis and vitals",
                "priority": "Critical",
                "preconditions": ["Doctor logged in", "Patient checked in to OPD queue"],
                "test_data": [
                    "blood_pressure: 120/80",
                    "pulse: 72 bpm",
                    "temperature: 98.6 F",
                    "chief_complaint: Persistent chest tightness for 2 days",
                    "icd10_code: I20.9 (Angina pectoris, unspecified)"
                ],
                "steps": [
                    "Open active patient consultation encounter from OPD Queue",
                    "Enter Blood Pressure with 120/80",
                    "Enter Pulse Rate with 72",
                    "Enter Temperature with 98.6",
                    "Enter Chief Complaint with Persistent chest tightness for 2 days",
                    "Select ICD-10 Diagnosis with I20.9",
                    "Click Save and Finalize Consultation button"
                ],
                "expected_result": "Clinical encounter saved to patient longitudinal timeline with immutable version timestamp",
                "requirement_id": "CRD-EMR-12-01"
            },
            {
                "id": "TC-HMIS-EMR-002",
                "tc_code": "TC-HMIS-EMR-002",
                "type": "Safety",
                "title": "Verify drug allergy contraindication alert when prescribing contraindicated medicine",
                "priority": "Critical",
                "preconditions": ["Patient clinical record has known allergy: Penicillin"],
                "test_data": ["rx_medicine: Amoxicillin 500mg (Penicillin class)"],
                "steps": [
                    "Open Doctor Consultation Prescription tab",
                    "Select Medicine Item with Amoxicillin 500mg",
                    "Click Add to Prescription button"
                ],
                "expected_result": "System raises high-severity red Allergy Contraindication Alert requiring physician override justification",
                "requirement_id": "CRD-EMR-12-02"
            },
            {
                "id": "TC-HMIS-EMR-003",
                "tc_code": "TC-HMIS-EMR-003",
                "type": "Audit",
                "title": "Verify clinical consultation audit trail: finalized notes cannot be silently modified",
                "priority": "High",
                "preconditions": ["Clinical consultation encounter finalized and signed by doctor"],
                "test_data": ["encounter_id: ENC-2026-9041"],
                "steps": [
                    "Open finalized encounter ENC-2026-9041 in Doctor Portal",
                    "Attempt to edit physical examination findings",
                    "Verify system enforces Addendum workflow with new signature and revision timestamp"
                ],
                "expected_result": "Original record remains intact; system logs addendum revision with doctor identity and exact timestamp",
                "requirement_id": "CRD-EMR-12-03"
            }
        ]

    # --------------------------------------------------------
    # HMIS: PHARMACY & PRESCRIPTION DISPENSING DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["pharmacy", "prescription", "dispense", "dispensing", "medicine", "batch", "expiry"]):
        return [
            {
                "id": "TC-HMIS-PHARM-001",
                "tc_code": "TC-HMIS-PHARM-001",
                "type": "Positive",
                "title": "Verify prescription dispensing with batch verification and stock deduction",
                "priority": "Critical",
                "preconditions": [
                    "Doctor has issued electronic prescription for patient",
                    "Pharmacy inventory has active stock with valid batch"
                ],
                "test_data": [
                    "prescription_id: RX-2026-8812",
                    "medicine: Amoxicillin 500mg",
                    "quantity: 20",
                    "batch: BATCH-AMX-901"
                ],
                "steps": [
                    "Navigate to Pharmacy Dispensing module",
                    "Search Prescription with RX-2026-8812",
                    "Select Medicine Item with Amoxicillin 500mg",
                    "Select Batch with BATCH-AMX-901",
                    "Enter Dispensed Quantity with 20",
                    "Click Dispense and Update Inventory button"
                ],
                "expected_result": "Prescription status updated to Dispensed, pharmacy stock reduced by 20, and stock movement logged",
                "requirement_id": "CRD-PHARM-13-01"
            },
            {
                "id": "TC-HMIS-PHARM-002",
                "tc_code": "TC-HMIS-PHARM-002",
                "type": "Security",
                "title": "Verify expired medicine batch blocking during dispensing",
                "priority": "Critical",
                "preconditions": ["Medicine batch has expiry date in the past"],
                "test_data": ["batch: BATCH-EXP-004", "expiry: 2025-12-31"],
                "steps": [
                    "Navigate to Pharmacy Dispensing module",
                    "Select Medicine Item",
                    "Attempt to select expired batch BATCH-EXP-004"
                ],
                "expected_result": "System blocks selection with 'Batch Expired' warning and prevents dispensing",
                "requirement_id": "CRD-PHARM-13-02"
            },
            {
                "id": "TC-HMIS-PHARM-003",
                "tc_code": "TC-HMIS-PHARM-003",
                "type": "Inventory",
                "title": "Verify pharmacy inventory real-time depletion and low-stock reorder threshold trigger",
                "priority": "High",
                "preconditions": ["Item Paracetamol 500mg current stock is 12 units, reorder threshold is 15 units"],
                "test_data": ["medicine: Paracetamol 500mg", "dispense_quantity: 5"],
                "steps": [
                    "Navigate to Pharmacy Dispensing module",
                    "Dispense 5 units of Paracetamol 500mg",
                    "Check Pharmacy Inventory Alert dashboard"
                ],
                "expected_result": "Stock drops to 7 units and system triggers automated Low Stock Reorder Notification",
                "requirement_id": "CRD-PHARM-13-03"
            }
        ]

    # --------------------------------------------------------
    # HMIS: IPD, WARDS & BED MANAGEMENT DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["ipd", "ward", "bed", "inpatient", "admission", "discharge", "doctor rounds"]):
        return [
            {
                "id": "TC-HMIS-IPD-001",
                "tc_code": "TC-HMIS-IPD-001",
                "type": "Positive",
                "title": "Verify IPD patient admission and bed allocation workflow",
                "priority": "High",
                "preconditions": ["Patient has admission recommendation from doctor", "General Ward has available beds"],
                "test_data": [
                    "uhid: UHID-2026-1044",
                    "ward: General Ward A",
                    "bed: Bed-GW-102",
                    "attending_physician: Dr. Sarah Connor"
                ],
                "steps": [
                    "Navigate to IPD Inpatient Admission module",
                    "Enter Patient UHID with UHID-2026-1044",
                    "Select Ward with General Ward A",
                    "Select Bed with Bed-GW-102",
                    "Select Attending Physician with Dr. Sarah Connor",
                    "Click Confirm Admission button"
                ],
                "expected_result": "IPD Admission created with IPD number, Bed status changes from Available to Occupied",
                "requirement_id": "CRD-IPD-10-01"
            },
            {
                "id": "TC-HMIS-IPD-002",
                "tc_code": "TC-HMIS-IPD-002",
                "type": "Workflow",
                "title": "Verify bed status transition to Cleaning upon patient discharge",
                "priority": "Medium",
                "preconditions": ["Patient is admitted in Bed-GW-102", "Final billing cleared"],
                "test_data": ["ipd_id: IPD-2026-4401", "bed: Bed-GW-102"],
                "steps": [
                    "Open IPD Patient Discharge panel",
                    "Enter IPD Number with IPD-2026-4401",
                    "Click Generate Discharge Summary button",
                    "Click Finalize Patient Discharge button"
                ],
                "expected_result": "Patient status updated to Discharged, Bed-GW-102 status transitions to Cleaning",
                "requirement_id": "CRD-IPD-10-02"
            },
            {
                "id": "TC-HMIS-IPD-003",
                "tc_code": "TC-HMIS-IPD-003",
                "type": "Validation",
                "title": "Verify bed allocation conflict prevention for beds undergoing cleaning or maintenance",
                "priority": "High",
                "preconditions": ["Bed-GW-105 is currently in Cleaning status"],
                "test_data": ["bed: Bed-GW-105", "status: Cleaning"],
                "steps": [
                    "Open IPD Admission Bed Selection dialog",
                    "Attempt to select Bed-GW-105 for new patient admission"
                ],
                "expected_result": "System disables bed selection with tooltip 'Bed undergoing sanitization/cleaning; unavailable for admission'",
                "requirement_id": "CRD-IPD-10-03"
            }
        ]

    # --------------------------------------------------------
    # HMIS: LABORATORY & INVESTIGATIONS DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["lab", "laboratory", "specimen", "test result", "sample", "critical value", "critical alert"]):
        return [
            {
                "id": "TC-HMIS-LAB-001",
                "tc_code": "TC-HMIS-LAB-001",
                "type": "Positive",
                "title": "Verify lab test ordering, sample barcode tracking and result verification",
                "priority": "High",
                "preconditions": ["Lab investigation ordered by doctor"],
                "test_data": [
                    "order_id: LAB-2026-5501",
                    "test_name: Complete Blood Count (CBC)",
                    "barcode: BAR-CBC-9872",
                    "hemoglobin_result: 14.2 g/dL"
                ],
                "steps": [
                    "Navigate to Laboratory Sample Collection module",
                    "Scan Specimen Barcode with BAR-CBC-9872",
                    "Click Acknowledge Sample Receipt button",
                    "Enter Hemoglobin Result with 14.2",
                    "Click Verify and Publish Lab Report button"
                ],
                "expected_result": "Lab report verified by pathologist and immediately accessible in doctor EMR",
                "requirement_id": "CRD-LAB-14-01"
            },
            {
                "id": "TC-HMIS-LAB-002",
                "tc_code": "TC-HMIS-LAB-002",
                "type": "Security",
                "title": "Verify critical lab result triggers immediate physician alert notification",
                "priority": "Critical",
                "preconditions": ["Ordered test: Serum Potassium (Normal: 3.5 - 5.0 mEq/L)"],
                "test_data": ["potassium_result: 6.8 mEq/L (Critical High)"],
                "steps": [
                    "Navigate to Lab Result Entry module",
                    "Enter Potassium Result with 6.8",
                    "Click Save Result button"
                ],
                "expected_result": "System highlights result in Red and sends immediate high-priority alert notification to attending doctor",
                "requirement_id": "CRD-LAB-14-02"
            },
            {
                "id": "TC-HMIS-LAB-003",
                "tc_code": "TC-HMIS-LAB-003",
                "type": "Validation",
                "title": "Verify specimen rejection workflow with mandatory reason code",
                "priority": "Medium",
                "preconditions": ["Phlebotomist collected sample that arrived hemolyzed or clotted"],
                "test_data": ["sample_id: SMP-9021", "rejection_reason: Hemolyzed Sample"],
                "steps": [
                    "Open Lab Sample Accessioning desk",
                    "Scan Sample Barcode SMP-9021",
                    "Click Reject Specimen button",
                    "Select Rejection Reason with Hemolyzed Sample",
                    "Click Confirm Sample Rejection button"
                ],
                "expected_result": "Sample status marked as Rejected, re-collection order auto-prompted, ward notified",
                "requirement_id": "CRD-LAB-14-03"
            }
        ]

    # --------------------------------------------------------
    # HMIS: RADIOLOGY & IMAGING DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["radiology", "imaging", "dicom", "pacs", "x-ray", "ct scan", "mri", "ultrasound"]):
        return [
            {
                "id": "TC-HMIS-RAD-001",
                "tc_code": "TC-HMIS-RAD-001",
                "type": "Positive",
                "title": "Verify radiology examination scheduling and modality slot allocation",
                "priority": "High",
                "preconditions": ["Attending physician ordered Chest X-Ray PA View"],
                "test_data": ["modality: X-Ray", "study: Chest X-Ray PA View", "time_slot: 11:00 AM"],
                "steps": [
                    "Navigate to Radiology Information System RIS module",
                    "Select Order from Clinical Orders worklist",
                    "Select Modality with X-Ray",
                    "Select Slot with 11:00 AM",
                    "Click Schedule Radiology Exam button"
                ],
                "expected_result": "Radiology accession number generated (e.g. RAD-ACC-8801) and appointment confirmed",
                "requirement_id": "CRD-RAD-15-01"
            },
            {
                "id": "TC-HMIS-RAD-002",
                "tc_code": "TC-HMIS-RAD-002",
                "type": "Workflow",
                "title": "Verify DICOM PACS image accession linking and radiologist report authoring",
                "priority": "Critical",
                "preconditions": ["Radiology study completed on scanner; DICOM images transmitted to PACS"],
                "test_data": ["accession_id: RAD-ACC-8801", "report_text: No active infiltrates, normal cardiothoracic ratio"],
                "steps": [
                    "Open Radiologist Reading Workstation",
                    "Open Accession RAD-ACC-8801",
                    "Launch DICOM Image Viewer",
                    "Enter Diagnostic Impression with No active infiltrates",
                    "Click Sign and Authorize Radiology Report button"
                ],
                "expected_result": "Radiologist digital signature captured, report status set to Finalized, linked to patient EMR",
                "requirement_id": "CRD-RAD-15-02"
            },
            {
                "id": "TC-HMIS-RAD-003",
                "tc_code": "TC-HMIS-RAD-003",
                "type": "Safety",
                "title": "Verify critical radiology alert notification for emergent findings",
                "priority": "Critical",
                "preconditions": ["CT Head scan shows acute intracranial hemorrhage"],
                "test_data": ["finding: Acute intracranial hemorrhage", "urgency: STAT Critical"],
                "steps": [
                    "Check Critical Finding checkbox in Radiology reporting module",
                    "Click Send Urgent Clinical Alert button"
                ],
                "expected_result": "Immediate STAT alert dispatched to emergency physician on-call with acknowledgement audit logging",
                "requirement_id": "CRD-RAD-15-03"
            }
        ]

    # --------------------------------------------------------
    # HMIS: BILLING, PAYMENTS & INSURANCE DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["billing", "invoice", "payment", "receipt", "insurance", "tpa", "charge master", "refund"]):
        return [
            {
                "id": "TC-HMIS-BILL-001",
                "tc_code": "TC-HMIS-BILL-001",
                "type": "Positive",
                "title": "Verify itemized hospital billing, payment collection and receipt generation",
                "priority": "Critical",
                "preconditions": ["Patient has unbilled consultation and pharmacy charges"],
                "test_data": [
                    "uhid: UHID-2026-1044",
                    "payment_mode: Credit Card",
                    "consultation_charge: 150.00",
                    "pharmacy_charge: 45.50",
                    "total_amount: 195.50"
                ],
                "steps": [
                    "Navigate to Hospital Billing and Invoices module",
                    "Enter Patient UHID with UHID-2026-1044",
                    "Click Generate Consolidated Invoice button",
                    "Verify itemized charges include Consultation ($150) and Pharmacy ($45.50)",
                    "Select Payment Mode with Credit Card",
                    "Enter Payment Amount with 195.50",
                    "Click Process Payment and Print Receipt button"
                ],
                "expected_result": "Payment recorded as Paid, immutable financial transaction receipt issued, balance set to $0.00",
                "requirement_id": "CRD-BILL-17-01"
            },
            {
                "id": "TC-HMIS-BILL-002",
                "tc_code": "TC-HMIS-BILL-002",
                "type": "Security",
                "title": "Verify financial audit immutability: Completed invoices cannot be overwritten",
                "priority": "Critical",
                "preconditions": ["Invoice status is PAID with receipt issued"],
                "test_data": ["invoice_id: INV-2026-0091"],
                "steps": [
                    "Navigate to Billing Archive module",
                    "Open paid invoice INV-2026-0091",
                    "Attempt to edit line item amounts or delete record"
                ],
                "expected_result": "Modifications blocked; corrections require formal credit note or audited refund workflow",
                "requirement_id": "CRD-BILL-17-02"
            },
            {
                "id": "TC-HMIS-BILL-003",
                "tc_code": "TC-HMIS-BILL-003",
                "type": "Financial",
                "title": "Verify advance deposit collection and automatic deduction against final IPD bill",
                "priority": "High",
                "preconditions": ["Inpatient has recorded advance deposit of $1,000.00"],
                "test_data": ["ipd_id: IPD-2026-4401", "gross_bill: 2500.00", "advance_paid: 1000.00"],
                "steps": [
                    "Open IPD Final Discharge Billing screen",
                    "Enter IPD ID with IPD-2026-4401",
                    "Verify Advance Deposit credit of $1,000.00 is automatically subtracted from gross total",
                    "Assert Net Payable Amount is exactly $1,500.00"
                ],
                "expected_result": "Deposit ledger correctly reconciled and reflected in final itemized bill statement",
                "requirement_id": "CRD-BILL-17-03"
            }
        ]

    # --------------------------------------------------------
    # HMIS: EMERGENCY & TRIAGE DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["emergency", "triage", "casualty", "ambulance", "trauma"]):
        return [
            {
                "id": "TC-HMIS-EMERG-001",
                "tc_code": "TC-HMIS-EMERG-001",
                "type": "Positive",
                "title": "Verify emergency patient registration and rapid triage severity categorization",
                "priority": "Critical",
                "preconditions": ["Emergency front desk triage workstation is active"],
                "test_data": [
                    "triage_color: Red (Resuscitation / Immediate)",
                    "chief_complaint: Severe trauma / unconscious",
                    "spO2: 85%",
                    "pulse: 130 bpm"
                ],
                "steps": [
                    "Open Emergency Admission Quick Entry module",
                    "Select Triage Category with Red (Immediate)",
                    "Enter Chief Complaint with Severe trauma",
                    "Enter SpO2 with 85",
                    "Enter Pulse with 130",
                    "Click Assign Trauma Bay button"
                ],
                "expected_result": "Immediate Emergency ID generated, trauma team alerted, patient assigned to Resuscitation Bay",
                "requirement_id": "CRD-EMERG-11-01"
            },
            {
                "id": "TC-HMIS-EMERG-002",
                "tc_code": "TC-HMIS-EMERG-002",
                "type": "Workflow",
                "title": "Verify yellow and green triage acuity assignment and waiting queue monitoring",
                "priority": "High",
                "preconditions": ["Walk-in emergency patient presenting with moderate fever and pain"],
                "test_data": ["triage_acuity: Green (Non-urgent)", "vitals: SpO2 99%, BP 118/76"],
                "steps": [
                    "Open Emergency Triage Assessment screen",
                    "Enter vital signs SpO2 99 and BP 118/76",
                    "Select Triage Category with Green (Non-urgent)",
                    "Click Add to Emergency Queue button"
                ],
                "expected_result": "Patient categorized into Green priority stream with target doctor assessment within 120 minutes",
                "requirement_id": "CRD-EMERG-11-02"
            },
            {
                "id": "TC-HMIS-EMERG-003",
                "tc_code": "TC-HMIS-EMERG-003",
                "type": "Emergency",
                "title": "Verify emergency to IPD or Operating Theater immediate transfer workflow",
                "priority": "Critical",
                "preconditions": ["Emergency patient stabilized in Resuscitation Bay requires immediate surgery"],
                "test_data": ["destination: Emergency OT-1", "transfer_reason: Acute appendiceal rupture"],
                "steps": [
                    "Click Emergency Transfer / Escalate button",
                    "Select Destination Department with Operating Theater",
                    "Select OT Room with Emergency OT-1",
                    "Complete Clinical Handover Checklist",
                    "Click Confirm Transfer button"
                ],
                "expected_result": "Patient transferred out of emergency bay, OT notified, and handover log saved",
                "requirement_id": "CRD-EMERG-11-03"
            }
        ]

    # --------------------------------------------------------
    # OTP / NOTIFICATION / SMS DOMAIN
    # --------------------------------------------------------
    if any(k in req_low for k in ["otp", "sms", "notification", "2fa", "verification code", "message"]):
        return [
            {
                "id": "TC-HMIS-NOTIF-001",
                "tc_code": "TC-HMIS-NOTIF-001",
                "type": "Positive",
                "title": f"Verify automated appointment reminder notification for {requirement}",
                "priority": "Medium",
                "preconditions": ["Patient has registered mobile number and email"],
                "test_data": ["phone: +1-555-019-2834", "channel: SMS and Email"],
                "steps": [
                    "Trigger scheduled appointment reminder service",
                    "Check SMS notification gateway delivery status",
                    "Verify SMS content includes doctor name, date, time and clinic location"
                ],
                "expected_result": "Notification logged as sent with timestamp and delivery receipt",
                "requirement_id": "CRD-NOTIF-21-01"
            }
        ]

    # --------------------------------------------------------
    # GENERIC FEATURE EXTRACTION
    # --------------------------------------------------------
    feature = requirement.replace("Verify ", "").replace("verify ", "").replace(".", "").strip() or "Hospital Feature"

    return [
        {
            "id": "TC-HMIS-GEN-001",
            "tc_code": "TC-HMIS-GEN-001",
            "type": "Positive",
            "title": f"Verify {feature} primary hospital workflow",
            "priority": "High",
            "preconditions": ["User is authenticated with required hospital role"],
            "test_data": ["Standard hospital test dataset"],
            "steps": [
                f"Navigate to {feature} section",
                f"Enter required clinical/operational details for {feature}",
                f"Click Submit {feature} button"
            ],
            "expected_result": f"{feature} processed successfully with audit record created",
            "requirement_id": "CRD-GEN-01"
        },
        {
            "id": "TC-HMIS-GEN-002",
            "tc_code": "TC-HMIS-GEN-002",
            "type": "Negative",
            "title": f"Verify validation constraints for {feature}",
            "priority": "Medium",
            "preconditions": ["User is on {feature} input form"],
            "test_data": ["Invalid or missing input parameters"],
            "steps": [
                f"Navigate to {feature} section",
                f"Leave required inputs empty or enter invalid data",
                f"Click Submit {feature} button"
            ],
            "expected_result": "Validation error alerts displayed and invalid data rejected",
            "requirement_id": "CRD-GEN-02"
        }
    ]