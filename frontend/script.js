"use strict";

/*
============================================================
 QA Bot AI — FRONTEND CONTROLLER (Enterprise Edition)
============================================================
 Responsibilities:
 1. Global State & Multi-Project Context Management
 2. Dashboard Real-Time Metrics & Recent Execution Feed
 3. Projects & Target Applications Workspace CRUD
 4. AI Test Case Generation (Requirement + Base URL + Screenshot OCR)
 5. Test Cases Repository Management (Search, Filter, Edit, Delete, Export)
 6. Automation Studio (Playwright, Selenium, Appium, Cypress across Py/Java/JS)
 7. Code Editor (Copy, Reset, Save to DB, Download Script)
 8. Sandboxed Test Execution Runner & Failure Diagnostics
 9. Persistent Execution History & Analytics
 10. User Authentication & Session Management
============================================================
*/

// ============================================================
// GLOBAL APPLICATION STATE
// ============================================================

const state = {
    activeProjectId: "proj-default-001",
    activeEnv: "QA",
    projects: [],
    applications: [],
    screenshots: [],
    generatedTestCases: [],
    savedTestCases: [],
    selectedTestCase: null,
    generatedCode: "",
    originalCode: "",
    generatedFilename: "test_generated.py",
    framework: "playwright",
    language: "python",
    baseUrl: "",
    lastExecutionResult: null,
    executionHistory: [],
};

const API_BASE_URL = window.TESTPILOT_API_URL || "";


// ============================================================
// DOM HELPERS
// ============================================================

function getElement(id) {
    return document.getElementById(id);
}

function showElement(element) {
    if (!element) return;
    element.classList.remove("hidden");
}

function hideElement(element) {
    if (!element) return;
    element.classList.add("hidden");
}

function setText(id, value) {
    const element = getElement(id);
    if (element) {
        element.textContent = value ?? "";
    }
}

function createId() {
    return "id_" + Math.random().toString(36).substring(2, 9);
}

function apiUrl(path) {
    if (!path.startsWith("/")) path = "/" + path;
    return API_BASE_URL + path;
}


// ============================================================
// FETCH API HELPER
// ============================================================

async function apiFetch(path, options = {}, timeoutMs = 180000) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(path.startsWith("http") ? path : apiUrl(path), {
            ...options,
            signal: controller.signal,
        });

        const contentType = response.headers.get("content-type") || "";
        let data;

        if (contentType.includes("application/json")) {
            data = await response.json();
        } else {
            const text = await response.text();
            data = { detail: text };
        }

        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = "/login";
                throw new Error("Authentication required. Please sign in.");
            }
            const message = data?.detail || data?.message || `Request failed with HTTP ${response.status}`;
            throw new Error(message);
        }

        return data;
    } catch (error) {
        if (error.name === "AbortError") {
            throw new Error("Request timed out. Ensure QA Bot backend is running.");
        }
        throw error;
    } finally {
        clearTimeout(timeout);
    }
}


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
    initializeTestPilot();
});

async function initializeTestPilot() {
    // Synchronously display Test Generator section immediately on refresh
    showSection("generator");

    setupRequirementCounter();
    setupScreenshotUpload();
    setupFrameworkLanguage();
    setupCodeEditor();
    setupTestCaseViewButtons();
    checkBackendHealth();
    
    try {
        await loadProjects();
        await loadApplications();
        await loadDashboardStats();
    } catch (err) {
        console.warn("Context loading error:", err);
    }
}

function setupTestCaseViewButtons() {
    const btnCards = getElement("btnViewCards");
    const btnMatrix = getElement("btnViewMatrix");
    const btnExport = getElement("btnExportCSV");

    if (btnCards) btnCards.addEventListener("click", () => switchTestCaseView("cards", "generator"));
    if (btnMatrix) btnMatrix.addEventListener("click", () => switchTestCaseView("matrix", "generator"));
    if (btnExport) btnExport.addEventListener("click", () => exportQAMatrixCSV("generator"));

    const btnRepoCards = getElement("btnRepoCards");
    const btnRepoMatrix = getElement("btnRepoMatrix");
    const btnRepoExport = getElement("btnRepoExportCSV");

    if (btnRepoCards) btnRepoCards.addEventListener("click", () => switchTestCaseView("cards", "repository"));
    if (btnRepoMatrix) btnRepoMatrix.addEventListener("click", () => switchTestCaseView("matrix", "repository"));
    if (btnRepoExport) btnRepoExport.addEventListener("click", () => exportQAMatrixCSV("repository"));
}


// ============================================================
// NAVIGATION & SECTIONS
// ============================================================

function showSection(sectionName) {
    // If dashboard or projects is requested while commented out, automatically redirect to generator
    if (sectionName === "dashboard" || sectionName === "projects" || !sectionName) {
        sectionName = "generator";
    }

    const sections = {
        dashboard: getElement("dashboardSection"),
        projects: getElement("projectsSection"),
        generator: getElement("generatorSection"),
        testCases: getElement("testCasesSection"),
        automation: getElement("automationSection"),
        results: getElement("resultsSection"),
    };

    const buttons = {
        dashboard: getElement("navDashboard"),
        projects: getElement("navProjects"),
        generator: getElement("navGenerator"),
        testCases: getElement("navTestCases"),
        automation: getElement("navAutomation"),
        results: getElement("navResults"),
    };

    Object.keys(sections).forEach(key => {
        if (sections[key]) {
            if (key === sectionName) {
                showElement(sections[key]);
                sections[key].classList.add("active");
            } else {
                hideElement(sections[key]);
                sections[key].classList.remove("active");
            }
        }
        if (buttons[key]) {
            if (key === sectionName) {
                buttons[key].classList.add("active");
            } else {
                buttons[key].classList.remove("active");
            }
        }
    });

    // Title Updates
    const titles = {
        dashboard: ["AI Test Case Generator", "Generate test cases from business requirements, URLs, and screenshots."],
        projects: ["AI Test Case Generator", "Generate test cases from business requirements, URLs, and screenshots."],
        generator: ["AI Test Case Generator", "Generate test cases from business requirements, URLs, and screenshots."],
        testCases: ["Test Case Repository", "Persistent database repository of all QA test cases."],
        automation: ["Automation Studio", "Convert test cases into executable Playwright, Selenium, Appium, or Cypress scripts."],
        results: ["Results & Reports", "Review test run outcomes, execution metrics, and failure diagnostics."],
    };

    if (titles[sectionName]) {
        setText("pageTitle", titles[sectionName][0]);
        setText("pageSubtitle", titles[sectionName][1]);
    }

    // Refresh context data when navigating
    if (sectionName === "dashboard") loadDashboardStats();
    if (sectionName === "projects") { loadProjects(); loadApplications(); }
    if (sectionName === "testCases") loadTestCasesRepository();
    if (sectionName === "automation") renderSelectedTestCase();
    if (sectionName === "results") loadExecutionHistory();
}

window.showSection = showSection;


// ============================================================
// PROJECTS & APPLICATIONS MANAGEMENT
// ============================================================

async function loadProjects() {
    try {
        const projects = await apiFetch("/api/projects");
        state.projects = projects;

        if (projects.length > 0) {
            const exists = projects.some(p => p.id === state.activeProjectId);
            if (!exists) {
                state.activeProjectId = projects[0].id;
            }
        }
        
        const select = getElement("activeProjectSelect");
        if (select) {
            select.innerHTML = "";
            projects.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = p.name;
                if (p.id === state.activeProjectId) opt.selected = true;
                select.appendChild(opt);
            });
            if (select.options.length > 0 && !select.value) {
                select.value = state.activeProjectId;
            }
        }

        renderProjectsListGrid();
    } catch (err) {
        console.error("Failed to load projects:", err);
    }
}

function renderProjectsListGrid() {
    const grid = getElement("projectsListGrid");
    if (!grid) return;

    if (!state.projects.length) {
        grid.innerHTML = `<div class="dashboard-empty">No projects found. Create a new project to get started.</div>`;
        return;
    }

    grid.innerHTML = state.projects.map(p => `
        <div class="project-card ${p.id === state.activeProjectId ? 'active-project' : ''}">
            <div class="project-card-header">
                <h3>${escapeHtml(p.name)}</h3>
                ${p.id === state.activeProjectId ? '<span class="badge badge-active">ACTIVE</span>' : ''}
            </div>
            <p>${escapeHtml(p.description || "No description provided.")}</p>
            <div class="project-card-footer">
                <span class="project-date">Created: ${new Date(p.created_at).toLocaleDateString()}</span>
                <div class="project-actions">
                    ${p.id !== state.activeProjectId ? `<button class="small-button" onclick="setActiveProject('${p.id}')">Select</button>` : ''}
                    ${state.projects.length > 1 ? `<button class="small-button danger-button" onclick="deleteProject('${p.id}')">Delete</button>` : ''}
                </div>
            </div>
        </div>
    `).join("");
}

function onProjectChange() {
    const select = getElement("activeProjectSelect");
    if (select) {
        state.activeProjectId = select.value;
        showToast("Active project updated.");
        loadDashboardStats();
        loadApplications();
        renderProjectsListGrid();
    }
}
window.onProjectChange = onProjectChange;

function setActiveProject(id) {
    state.activeProjectId = id;
    const select = getElement("activeProjectSelect");
    if (select) select.value = id;
    onProjectChange();
}
window.setActiveProject = setActiveProject;

async function deleteProject(id) {
    if (!confirm("Are you sure you want to delete this project? All associated data will be removed.")) return;
    try {
        await apiFetch(`/api/projects/${id}`, { method: "DELETE" });
        showToast("Project deleted.");
        if (state.activeProjectId === id) state.activeProjectId = "proj-default-001";
        await loadProjects();
        await loadDashboardStats();
    } catch (err) {
        showToast(err.message);
    }
}
window.deleteProject = deleteProject;

function openCreateProjectModal() {
    showElement(getElement("createProjectModal"));
}
window.openCreateProjectModal = openCreateProjectModal;

function closeCreateProjectModal() {
    hideElement(getElement("createProjectModal"));
    getElement("newProjectName").value = "";
    getElement("newProjectDesc").value = "";
}
window.closeCreateProjectModal = closeCreateProjectModal;

async function submitCreateProject() {
    const name = getElement("newProjectName").value.trim();
    const desc = getElement("newProjectDesc").value.trim();

    if (!name) {
        showToast("Project name is required.");
        return;
    }

    try {
        const created = await apiFetch("/api/projects", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, description: desc }),
        });
        showToast(`Project '${created.name}' created!`);
        closeCreateProjectModal();
        state.activeProjectId = created.id;
        await loadProjects();
        await loadDashboardStats();
    } catch (err) {
        showToast(err.message);
    }
}
window.submitCreateProject = submitCreateProject;


// ============================================================
// TARGET APPLICATIONS MANAGEMENT
// ============================================================

async function loadApplications() {
    try {
        const apps = await apiFetch(`/api/applications?project_id=${state.activeProjectId}`);
        state.applications = apps;
        
        const tbody = getElement("applicationsTableBody");
        if (!tbody) return;

        if (!apps.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="dashboard-empty">No target applications configured for this project.</td></tr>`;
            return;
        }

        tbody.innerHTML = apps.map(app => `
            <tr>
                <td><strong>${escapeHtml(app.name)}</strong></td>
                <td>${escapeHtml(state.projects.find(p => p.id === app.project_id)?.name || app.project_id)}</td>
                <td><a href="${escapeHtml(app.base_url)}" target="_blank" class="table-link">${escapeHtml(app.base_url)}</a></td>
                <td><span class="badge badge-env">${escapeHtml(app.environment)}</span></td>
                <td>${new Date(app.created_at).toLocaleDateString()}</td>
                <td><button class="small-button danger-button" onclick="deleteApplication('${app.id}')">Delete</button></td>
            </tr>
        `).join("");

        // Sync first app base URL to inputs if empty
        if (apps.length > 0 && !getElement("baseUrl").value) {
            getElement("baseUrl").value = apps[0].base_url;
        }
    } catch (err) {
        console.error("Failed to load applications:", err);
    }
}

function openCreateAppModal() {
    showElement(getElement("createAppModal"));
}
window.openCreateAppModal = openCreateAppModal;

function closeCreateAppModal() {
    hideElement(getElement("createAppModal"));
    getElement("newAppName").value = "";
    getElement("newAppUrl").value = "";
}
window.closeCreateAppModal = closeCreateAppModal;

async function submitCreateApp() {
    const name = getElement("newAppName").value.trim();
    const url = getElement("newAppUrl").value.trim();
    const env = getElement("newAppEnv").value;

    if (!name || !url) {
        showToast("Application name and URL are required.");
        return;
    }

    try {
        await apiFetch("/api/applications", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: state.activeProjectId,
                name,
                base_url: url,
                environment: env,
            }),
        });
        showToast(`Application '${name}' added!`);
        closeCreateAppModal();
        await loadApplications();
        await loadDashboardStats();
    } catch (err) {
        showToast(err.message);
    }
}
window.submitCreateApp = submitCreateApp;

async function deleteApplication(id) {
    if (!confirm("Are you sure you want to delete this target application?")) return;
    try {
        await apiFetch(`/api/applications/${id}`, { method: "DELETE" });
        showToast("Application deleted.");
        await loadApplications();
        await loadDashboardStats();
    } catch (err) {
        showToast(err.message);
    }
}
window.deleteApplication = deleteApplication;

function onEnvChange() {
    const el = getElement("activeEnvSelect");
    if (!el) return;
    state.activeEnv = el.value;
    setText("dashboardEnvironment", state.activeEnv);
    showToast(`Environment switched to ${state.activeEnv}`);
}
window.onEnvChange = onEnvChange;


// ============================================================
// DASHBOARD METRICS & FEED
// ============================================================

async function loadDashboardStats() {
    try {
        const stats = await apiFetch(`/api/dashboard/stats?project_id=${state.activeProjectId}`);

        setText("dashboardTestCases", stats.test_cases);
        setText("dashboardAutomations", stats.automations);
        setText("dashboardExecutions", stats.executions);
        setText("dashboardPassed", stats.passed);
        setText("dashboardFailed", stats.failed);
        setText("dashboardPassRate", stats.pass_rate);

        setText("dashboardApplication", stats.application);
        setText("dashboardEnvironment", state.activeEnv || stats.environment);
        setText("dashboardUrl", stats.base_url || "Not configured");

        const recentContainer = getElement("dashboardRecentExecutions");
        if (recentContainer) {
            if (!stats.recent_executions || !stats.recent_executions.length) {
                recentContainer.innerHTML = "No executions recorded yet.";
                recentContainer.className = "dashboard-empty";
            } else {
                recentContainer.className = "";
                recentContainer.innerHTML = `
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Framework</th>
                                <th>Language</th>
                                <th>Status</th>
                                <th>Failure Type</th>
                                <th>Duration</th>
                                <th>Timestamp</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${stats.recent_executions.map(r => `
                                <tr>
                                    <td><strong>${escapeHtml(r.framework.toUpperCase())}</strong></td>
                                    <td>${escapeHtml(r.language)}</td>
                                    <td><span class="badge ${r.status === 'PASSED' ? 'badge-passed' : 'badge-failed'}">${r.status}</span></td>
                                    <td><span class="badge badge-failure">${r.failure_type}</span></td>
                                    <td>${r.duration}s</td>
                                    <td>${new Date(r.executed_at).toLocaleTimeString()}</td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                `;
            }
        }
    } catch (err) {
        console.error("Dashboard stats error:", err);
    }
}


// ============================================================
// REQUIREMENT COUNTER & SCREENSHOT UPLOADER
// ============================================================

function setupRequirementCounter() {
    const requirement = getElement("requirement");
    if (!requirement) return;
    requirement.addEventListener("input", () => {
        setText("requirementCount", `${requirement.value.length} / 5000`);
    });
}

const HMIS_TEMPLATES = {
    patient: {
        requirement: "Verify patient registration workflow: Register a new patient with First Name John, Last Name Doe, Date of Birth 1988-04-12, Gender Male, Blood Group O+, Mobile Phone +1-555-019-2834, and Allergies Penicillin. Ensure a unique Hospital Identifier (UHID) is automatically generated. Verify duplicate patient detection triggers when attempting to register with an already existing phone number and name.",
        url: "https://hmis.hospital.internal/patients/register"
    },
    opd: {
        requirement: "Verify OPD appointment booking and queue workflow: Select department with Cardiology and doctor with Dr. Robert Smith. Reserve an available 10:30 AM slot on 2026-09-15 for patient UHID-2026-1044. Confirm appointment, verify queue token #14 is generated, and verify that slot 10:30 AM becomes unavailable to prevent double booking.",
        url: "https://hmis.hospital.internal/opd/appointments"
    },
    emr: {
        requirement: "Verify doctor clinical consultation and EMR workflow: Doctor opens patient encounter from OPD Queue. Record vital signs (Blood Pressure 120/80, Pulse 72 bpm, Temperature 98.6 F), record chief complaints ('Persistent chest tightness for 2 days'), and select ICD-10 diagnosis code I20.9 (Angina pectoris, unspecified). Save consultation note and verify it creates an immutable version in the longitudinal clinical timeline.",
        url: "https://hmis.hospital.internal/doctor/consultation"
    },
    pharmacy: {
        requirement: "Verify pharmacy prescription review, dispensing, and inventory stock deduction: Pharmacist searches electronic prescription RX-2026-8812. Review prescribed medication Amoxicillin 500mg, select valid batch BATCH-AMX-901, and dispense quantity of 20 units. Verify prescription status transitions to Dispensed, pharmacy inventory stock decrements by 20, and expired batch BATCH-EXP-004 is blocked with an expiry alert.",
        url: "https://hmis.hospital.internal/pharmacy/dispense"
    },
    ipd: {
        requirement: "Verify IPD inpatient admission and bed allocation workflow: Enter patient UHID-2026-1044 with doctor admission order. Select General Ward A and assign available Bed-GW-102 with attending physician Dr. Sarah Connor. Verify IPD admission record is created and Bed status transitions from Available to Occupied. Upon patient discharge, verify bed status transitions to Cleaning.",
        url: "https://hmis.hospital.internal/ipd/admissions"
    },
    emergency: {
        requirement: "Verify emergency patient registration and rapid triage severity categorization: Front desk registers emergency patient presenting with severe trauma. Select Triage Category Red (Immediate Resuscitation), record vital signs (SpO2 85%, Pulse 130 bpm), and assign patient to Trauma Bay 1. Verify emergency team is immediately alerted and emergency case identifier is generated.",
        url: "https://hmis.hospital.internal/emergency/triage"
    },
    lab: {
        requirement: "Verify laboratory investigation ordering, specimen collection, and critical result alert: Scan specimen barcode BAR-POT-1102 for ordered Serum Potassium test. Enter test result value 6.8 mEq/L. Verify system flags result in Red as Critical High (reference range: 3.5 - 5.0 mEq/L) and automatically dispatches an immediate critical alert notification to the attending physician.",
        url: "https://hmis.hospital.internal/lab/results"
    },
    radiology: {
        requirement: "Verify radiology imaging test scheduling and radiologist reporting: Schedule ordered Chest X-Ray for patient UHID-2026-1044. Technician acquires imaging study and uploads digital radiograph. Radiologist reviews image, enters clinical impression ('No acute cardiopulmonary abnormality detected'), and publishes verified radiology report to the patient EMR.",
        url: "https://hmis.hospital.internal/radiology/imaging"
    },
    billing: {
        requirement: "Verify itemized hospital billing, payment processing, and financial audit immutability: Generate consolidated invoice for patient UHID-2026-1044 combining OPD consultation charge ($150.00) and pharmacy charge ($45.50), totaling $195.50. Process full payment via Credit Card, verify invoice status transitions to PAID with receipt issued and balance set to $0.00, and verify paid invoice cannot be modified without formal credit note.",
        url: "https://hmis.hospital.internal/billing/invoices"
    },
    rbac: {
        requirement: "Verify role-based access control (RBAC) and separation of duties: Log in as user with role 'Pharmacist'. Attempt to access doctor clinical notes to edit an ICD-10 diagnosis. Verify action is blocked with 403 Forbidden. Log in as 'Receptionist' and attempt to access lab result entry. Verify access is denied and unauthorized attempt is logged to the security audit trail.",
        url: "https://hmis.hospital.internal/auth/rbac"
    }
};

function loadHmisTemplate(key) {
    if (!key || !HMIS_TEMPLATES[key]) return;
    const tpl = HMIS_TEMPLATES[key];
    const reqElem = getElement("requirement");
    const urlElem = getElement("baseUrl");
    if (reqElem) {
        reqElem.value = tpl.requirement;
        setText("requirementCount", `${reqElem.value.length} / 5000`);
    }
    if (urlElem && !urlElem.value.trim()) {
        urlElem.value = tpl.url;
    }
    state.activeProjectId = "proj-hmis-001";
    showToast(`Loaded HMIS template: ${key.toUpperCase()}`);
}
window.loadHmisTemplate = loadHmisTemplate;

function setupScreenshotUpload() {
    const uploadZone = getElement("uploadZone");
    const input = getElement("screenshotInput");
    if (!uploadZone || !input) return;

    uploadZone.addEventListener("click", () => input.click());

    input.addEventListener("change", event => {
        const files = Array.from(event.target.files || []);
        addScreenshots(files);
        input.value = "";
    });

    uploadZone.addEventListener("dragover", event => {
        event.preventDefault();
        uploadZone.classList.add("drag-over");
    });

    uploadZone.addEventListener("dragleave", event => {
        event.preventDefault();
        uploadZone.classList.remove("drag-over");
    });

    uploadZone.addEventListener("drop", event => {
        event.preventDefault();
        uploadZone.classList.remove("drag-over");
        const files = Array.from(event.dataTransfer.files || []);
        addScreenshots(files);
    });
}

function addScreenshots(files) {
    if (!files.length) return;
    const allowedTypes = ["image/png", "image/jpeg", "image/webp", "image/bmp"];
    const availableSlots = 5 - state.screenshots.length;

    if (availableSlots <= 0) {
        showToast("Maximum 5 screenshots allowed.");
        return;
    }

    const filesToAdd = files.slice(0, availableSlots);

    for (const file of filesToAdd) {
        if (!allowedTypes.includes(file.type)) {
            showToast(`${file.name} is not a supported image format.`);
            continue;
        }
        if (file.size > 10 * 1024 * 1024) {
            showToast(`${file.name} is larger than 10 MB.`);
            continue;
        }
        if (state.screenshots.some(item => item.file.name === file.name && item.file.size === file.size)) {
            continue;
        }
        state.screenshots.push({ id: createId(), file });
    }
    renderScreenshots();
}

function removeScreenshot(id) {
    state.screenshots = state.screenshots.filter(item => item.id !== id);
    renderScreenshots();
}
window.removeScreenshot = removeScreenshot;

function renderScreenshots() {
    const grid = getElement("screenshotGrid");
    if (!grid) return;
    grid.innerHTML = "";

    state.screenshots.forEach(item => {
        const wrapper = document.createElement("div");
        wrapper.className = "screenshot-preview";

        const image = document.createElement("img");
        const url = URL.createObjectURL(item.file);
        image.src = url;
        image.alt = item.file.name;
        image.onload = () => URL.revokeObjectURL(url);

        const overlay = document.createElement("div");
        overlay.className = "screenshot-overlay";

        const filename = document.createElement("span");
        filename.textContent = item.file.name;
        filename.className = "screenshot-name";

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "screenshot-remove";
        removeBtn.textContent = "×";
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            removeScreenshot(item.id);
        };

        overlay.appendChild(filename);
        overlay.appendChild(removeBtn);
        wrapper.appendChild(image);
        wrapper.appendChild(overlay);
        grid.appendChild(wrapper);
    });
}


// ============================================================
// AI TEST CASE GENERATION
// ============================================================

async function generateTestCases() {
    const reqText = getElement("requirement").value.trim();
    const urlText = getElement("baseUrl").value.trim();
    const errorBox = getElement("generatorError");
    const button = getElement("generateButton");

    hideElement(errorBox);

    if (!reqText || reqText.length < 10) {
        showElement(errorBox);
        errorBox.textContent = "Please enter a detailed requirement (minimum 10 characters).";
        return;
    }


    button.disabled = true;
    setText("generateButtonText", "Analyzing UI & Generating Test Cases...");

    try {
        const formData = new FormData();
        formData.append("requirement", reqText);
        formData.append("base_url", urlText);
        formData.append("project_id", state.activeProjectId);

        state.screenshots.forEach(item => {
            formData.append("screenshots", item.file);
        });

        const data = await apiFetch("/generate-test-cases-with-context", {
            method: "POST",
            body: formData,
        });

        state.generatedTestCases = data.test_cases || [];
        state.latestBatchIds = new Set((data.test_cases || []).map(tc => tc.id));
        state.baseUrl = data.base_url || urlText;

        renderGeneratedTestCases();
        showToast(`Generated ${state.generatedTestCases.length} AI test cases!`);
        await loadTestCasesRepository();
        await loadDashboardStats();
    } catch (err) {
        showElement(errorBox);
        errorBox.textContent = err.message || "Test case generation failed.";
    } finally {
        button.disabled = false;
        setText("generateButtonText", "Generate Test Cases");
    }
}
window.generateTestCases = generateTestCases;

function switchTestCaseView(mode, context = "generator") {
    let list, matrix, btnCards, btnMatrix;

    if (context === "repository") {
        list = getElement("repositoryList");
        matrix = getElement("repoMatrixContainer");
        btnCards = getElement("btnRepoCards");
        btnMatrix = getElement("btnRepoMatrix");
    } else {
        list = getElement("testCaseList");
        matrix = getElement("matrixTableContainer");
        btnCards = getElement("btnViewCards");
        btnMatrix = getElement("btnViewMatrix");
    }

    if (!list || !matrix) return;

    if (mode === "matrix") {
        list.classList.add("hidden");
        list.style.setProperty("display", "none", "important");

        matrix.classList.remove("hidden");
        matrix.style.setProperty("display", "block", "important");

        if (btnCards) {
            btnCards.classList.remove("active", "primary-button");
            btnCards.classList.add("secondary-button");
        }
        if (btnMatrix) {
            btnMatrix.classList.add("active", "primary-button");
            btnMatrix.classList.remove("secondary-button");
        }
    } else {
        list.classList.remove("hidden");
        list.style.removeProperty("display");

        matrix.classList.add("hidden");
        matrix.style.setProperty("display", "none", "important");

        if (btnCards) {
            btnCards.classList.add("active", "primary-button");
            btnCards.classList.remove("secondary-button");
        }
        if (btnMatrix) {
            btnMatrix.classList.remove("active", "primary-button");
            btnMatrix.classList.add("secondary-button");
        }
    }
}
window.switchTestCaseView = switchTestCaseView;

function renderGeneratedTestCases() {
    const card = getElement("testCaseCard");
    const list = getElement("testCaseList");
    const matrixBody = getElement("matrixTableBody");

    if (!card || !list) return;

    if (!state.generatedTestCases.length) {
        hideElement(card);
        return;
    }

    showElement(card);
    setText("testCaseCount", state.generatedTestCases.length);

    // Ensure default card view is visible when rendering
    switchTestCaseView("cards", "generator");

    // 1. Cards View Rendering
    list.innerHTML = state.generatedTestCases.map((tc, idx) => `
        <div class="test-case-item">
            <div class="test-case-header">
                <div>
                    <span class="tc-id">${escapeHtml(tc.tc_code || tc.id)}</span>
                    <span class="badge badge-priority">${escapeHtml(tc.priority)}</span>
                    <span class="badge badge-type">${escapeHtml(tc.type)}</span>
                </div>
                <button class="primary-button small-button" onclick="selectTestCaseForAutomation(${idx})">Select for Automation →</button>
            </div>

            <h3 class="tc-title">${escapeHtml(tc.test_scenario || tc.title)}</h3>

            ${tc.preconditions?.length ? `
                <div class="tc-section">
                    <strong>Preconditions:</strong>
                    <ul>${tc.preconditions.map(p => `<li>${escapeHtml(p)}</li>`).join("")}</ul>
                </div>
            ` : ''}

            <div class="tc-section">
                <strong>Test Steps:</strong>
                <ol>${(tc.steps || []).map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol>
            </div>

            <div class="tc-section">
                <strong>Expected Result:</strong>
                <p class="tc-expected">${escapeHtml(tc.expected_result)}</p>
            </div>

            ${tc.test_data?.length ? `
                <div class="tc-section">
                    <strong>Test Data:</strong>
                    <p class="tc-expected">${escapeHtml(tc.test_data.join(", "))}</p>
                </div>
            ` : ''}
        </div>
    `).join("");

    // 2. Matrix Table Rendering
    if (matrixBody) {
        matrixBody.innerHTML = state.generatedTestCases.map((tc, idx) => `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); vertical-align: top;">
                <td style="padding: 10px; font-weight: bold; color: var(--accent-blue);">${escapeHtml(tc.tc_code || tc.id)}</td>
                <td style="padding: 10px;"><span class="badge badge-priority">${escapeHtml(tc.priority)}</span></td>
                <td style="padding: 10px;"><span class="badge badge-type">${escapeHtml(tc.type)}</span></td>
                <td style="padding: 10px; font-weight: 500;">${escapeHtml(tc.test_scenario || tc.title)}</td>
                <td style="padding: 10px; max-width: 150px;">${(tc.preconditions || []).map(p => `• ${escapeHtml(p)}`).join("<br>")}</td>
                <td style="padding: 10px; max-width: 250px;"><ol style="margin: 0; padding-left: 15px;">${(tc.steps || []).map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol></td>
                <td style="padding: 10px; max-width: 200px;">${escapeHtml(tc.expected_result)}</td>
                <td style="padding: 10px; max-width: 120px;">${(tc.test_data || []).map(d => escapeHtml(d)).join("<br>")}</td>
                <td style="padding: 10px;">${escapeHtml(tc.requirement_id || "US-PAT-001")}</td>
                <td style="padding: 10px;"><span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981;">${escapeHtml(tc.status || "Ready for Automation")}</span></td>
                <td style="padding: 10px; max-width: 150px; font-style: italic; color: #a0aec0;">${escapeHtml(tc.remarks || "QA Matrix Candidate")}</td>
                <td style="padding: 10px;"><button class="primary-button small-button" onclick="selectTestCaseForAutomation(${idx})">Automate</button></td>
            </tr>
        `).join("");
    }
}

function exportQAMatrixCSV(source = 'auto') {
    let dataset = state.generatedTestCases;
    if (source === 'repository' || (!dataset || !dataset.length)) {
        dataset = state.savedTestCases;
    }
    if (!dataset || !dataset.length) {
        showToast("No test cases available to export.");
        return;
    }

    const headers = [
        "Test ID", "Priority", "Test Type", "Test Scenario", "Preconditions",
        "Test Steps", "Expected Result", "Test Data", "Requirement ID", "Status", "Remarks"
    ];

    const rows = dataset.map(tc => [
        `"${(tc.tc_code || tc.id || "").replace(/"/g, '""')}"`,
        `"${(tc.priority || "Medium").replace(/"/g, '""')}"`,
        `"${(tc.type || "Functional").replace(/"/g, '""')}"`,
        `"${(tc.test_scenario || tc.title || "").replace(/"/g, '""')}"`,
        `"${(tc.preconditions || []).join(" | ").replace(/"/g, '""')}"`,
        `"${(tc.steps || []).join(" | ").replace(/"/g, '""')}"`,
        `"${(tc.expected_result || "").replace(/"/g, '""')}"`,
        `"${(tc.test_data || []).join(" | ").replace(/"/g, '""')}"`,
        `"${(tc.requirement_id || "US-PAT-001").replace(/"/g, '""')}"`,
        `"${(tc.status || "Ready for Automation").replace(/"/g, '""')}"`,
        `"${(tc.remarks || "QA Matrix Candidate").replace(/"/g, '""')}"`
    ]);

    const csvString = [headers.join(","), ...rows.map(r => r.join(","))].join("\r\n");
    const blob = new Blob([csvString], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `QA_Test_Matrix_${state.activeProjectId}_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast("QA Test Matrix exported to CSV!");
}
window.exportQAMatrixCSV = exportQAMatrixCSV;
window.exportSeniorQAMatrixCSV = exportQAMatrixCSV;


// ============================================================
// TEST CASE REPOSITORY MANAGEMENT
// ============================================================

async function loadTestCasesRepository() {
    try {
        const testCases = await apiFetch(`/api/test-cases?project_id=${state.activeProjectId}`);
        state.savedTestCases = testCases;
        filterTestCasesRepository();
    } catch (err) {
        console.error("Failed to load test cases repository:", err);
    }
}

function filterTestCasesRepository() {
    const scope = getElement("tcScopeFilter")?.value || "all";
    const search = (getElement("tcSearchInput")?.value || "").toLowerCase();
    const priority = getElement("tcPriorityFilter")?.value || "";
    const type = getElement("tcTypeFilter")?.value || "";

    const list = getElement("repositoryList");
    const repoMatrixBody = getElement("repoMatrixTableBody");
    if (!list) return;

    let dataset = state.savedTestCases || [];

    if (scope === "latest") {
        if (state.latestBatchIds && state.latestBatchIds.size > 0) {
            dataset = dataset.filter(tc => state.latestBatchIds.has(tc.id));
        } else if (state.generatedTestCases && state.generatedTestCases.length > 0) {
            const genSet = new Set(state.generatedTestCases.map(tc => tc.id));
            dataset = dataset.filter(tc => genSet.has(tc.id));
        }
    }

    let filtered = dataset.filter(tc => {
        const matchesSearch = !search || tc.title.toLowerCase().includes(search) || tc.id.toLowerCase().includes(search);
        const matchesPriority = !priority || tc.priority === priority;
        const matchesType = !type || tc.type === type;
        return matchesSearch && matchesPriority && matchesType;
    });

    if (!filtered.length) {
        list.innerHTML = `<div class="dashboard-empty">No test cases found in repository matching criteria.</div>`;
        if (repoMatrixBody) repoMatrixBody.innerHTML = `<tr><td colspan="12" style="text-align: center; padding: 20px; color: #a0aec0;">No test cases found.</td></tr>`;
        return;
    }

    // 1. Cards View Rendering
    list.innerHTML = filtered.map((tc) => `
        <div class="test-case-item">
            <div class="test-case-header">
                <div>
                    <span class="tc-id">${escapeHtml(tc.tc_code || tc.id)}</span>
                    <span class="badge badge-priority">${escapeHtml(tc.priority)}</span>
                    <span class="badge badge-type">${escapeHtml(tc.type)}</span>
                </div>
                <div>
                    <button class="small-button primary-button" onclick="selectSavedTestCase('${tc.id}')">Automate →</button>
                    <button class="small-button danger-button" onclick="deleteSavedTestCase('${tc.id}')">Delete</button>
                </div>
            </div>
            <h3 class="tc-title">${escapeHtml(tc.test_scenario || tc.title)}</h3>
            <div class="tc-section">
                <strong>Steps (${tc.steps?.length || 0}):</strong>
                <ol>${(tc.steps || []).map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol>
            </div>
            <div class="tc-section">
                <strong>Expected Result:</strong>
                <p class="tc-expected">${escapeHtml(tc.expected_result)}</p>
            </div>
        </div>
    `).join("");

    // 2. Matrix Table Rendering for Repository
    if (repoMatrixBody) {
        repoMatrixBody.innerHTML = filtered.map((tc) => `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); vertical-align: top;">
                <td style="padding: 10px; font-weight: bold; color: var(--accent-blue);">${escapeHtml(tc.tc_code || tc.id)}</td>
                <td style="padding: 10px;"><span class="badge badge-priority">${escapeHtml(tc.priority)}</span></td>
                <td style="padding: 10px;"><span class="badge badge-type">${escapeHtml(tc.type)}</span></td>
                <td style="padding: 10px; font-weight: 500;">${escapeHtml(tc.test_scenario || tc.title)}</td>
                <td style="padding: 10px; max-width: 150px;">${(tc.preconditions || []).map(p => `• ${escapeHtml(p)}`).join("<br>")}</td>
                <td style="padding: 10px; max-width: 250px;"><ol style="margin: 0; padding-left: 15px;">${(tc.steps || []).map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol></td>
                <td style="padding: 10px; max-width: 200px;">${escapeHtml(tc.expected_result)}</td>
                <td style="padding: 10px; max-width: 120px;">${(tc.test_data || []).map(d => escapeHtml(d)).join("<br>")}</td>
                <td style="padding: 10px;">${escapeHtml(tc.requirement_id || "US-PAT-001")}</td>
                <td style="padding: 10px;"><span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981;">${escapeHtml(tc.status || "Ready for Automation")}</span></td>
                <td style="padding: 10px; max-width: 150px; font-style: italic; color: #a0aec0;">${escapeHtml(tc.remarks || "QA Matrix Candidate")}</td>
                <td style="padding: 10px;">
                    <button class="primary-button small-button" onclick="selectSavedTestCase('${tc.id}')">Automate</button>
                </td>
            </tr>
        `).join("");
    }
}
window.filterTestCasesRepository = filterTestCasesRepository;

async function clearRepositoryHistory() {
    if (!confirm("Are you sure you want to clear historical test cases from the database for this project?")) return;
    try {
        await apiFetch(`/api/test-cases-purge?project_id=${state.activeProjectId}`, { method: "DELETE" });
        showToast("Historical test cases cleared.");
        state.latestBatchIds = new Set();
        state.generatedTestCases = [];
        renderGeneratedTestCases();
        await loadTestCasesRepository();
        await loadDashboardStats();
    } catch (err) {
        showToast(err.message || "Failed to purge test case history.");
    }
}
window.clearRepositoryHistory = clearRepositoryHistory;

function selectTestCaseForAutomation(index) {
    const tc = state.generatedTestCases[index];
    if (!tc) return;
    state.selectedTestCase = tc;
    renderSelectedTestCase();
    showSection("automation");
}
window.selectTestCaseForAutomation = selectTestCaseForAutomation;

function selectSavedTestCase(tcId) {
    const tc = state.savedTestCases.find(item => item.id === tcId);
    if (!tc) return;
    state.selectedTestCase = tc;
    renderSelectedTestCase();
    showSection("automation");
}
window.selectSavedTestCase = selectSavedTestCase;

async function deleteSavedTestCase(id) {
    if (!confirm("Are you sure you want to delete this test case?")) return;
    try {
        await apiFetch(`/api/test-cases/${id}`, { method: "DELETE" });
        showToast("Test case deleted.");
        await loadTestCasesRepository();
        await loadDashboardStats();
    } catch (err) {
        showToast(err.message);
    }
}
window.deleteSavedTestCase = deleteSavedTestCase;

function exportTestCasesJSON() {
    const jsonStr = JSON.stringify(state.savedTestCases, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `test_cases_${state.activeProjectId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Exported test cases JSON.");
}
window.exportTestCasesJSON = exportTestCasesJSON;


// ============================================================
// AUTOMATION STUDIO & FRAMEWORKS MATRIX
// ============================================================

function setupFrameworkLanguage() {
    const framework = getElement("framework");
    const language = getElement("language");

    if (framework) {
        framework.addEventListener("change", () => {
            state.framework = framework.value;
            updateLanguageOptions();
        });
    }

    if (language) {
        language.addEventListener("change", () => {
            state.language = language.value;
        });
    }
    updateLanguageOptions();
}

function updateLanguageOptions() {
    const framework = getElement("framework")?.value || "playwright";
    const languageSelect = getElement("language");
    if (!languageSelect) return;

    const currentLang = languageSelect.value;
    languageSelect.innerHTML = "";

    if (framework === "cypress") {
        const opt = document.createElement("option");
        opt.value = "javascript";
        opt.textContent = "JavaScript (Cypress requirement)";
        languageSelect.appendChild(opt);
        state.language = "javascript";
    } else {
        const options = [
            { value: "python", label: "Python" },
            { value: "java", label: "Java" },
            { value: "javascript", label: "JavaScript" },
        ];
        options.forEach(o => {
            const opt = document.createElement("option");
            opt.value = o.value;
            opt.textContent = o.label;
            if (o.value === currentLang) opt.selected = true;
            languageSelect.appendChild(opt);
        });
        state.language = languageSelect.value;
    }
}
window.updateLanguageOptions = updateLanguageOptions;

function renderSelectedTestCase() {
    const container = getElement("selectedTestCase");
    if (!container) return;

    const tc = state.selectedTestCase;
    if (!tc) {
        container.innerHTML = `
            <div class="empty-selection">
                <div class="empty-icon">🧪</div>
                <h3>No test case selected</h3>
                <p>Generate or select a test case to configure automation.</p>
                <button class="secondary-button" onclick="showSection('generator')">Go to Test Generator</button>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div class="selected-tc-banner">
            <div>
                <span class="tc-id">${escapeHtml(tc.id)}</span>
                <span class="badge badge-priority">${escapeHtml(tc.priority)}</span>
                <span class="badge badge-type">${escapeHtml(tc.type)}</span>
            </div>
            <h3>${escapeHtml(tc.title)}</h3>
        </div>
    `;
}

async function generateAutomation() {
    const tc = state.selectedTestCase;
    const errorBox = getElement("automationError");
    const button = getElement("automationButton");
    const codeSection = getElement("codeSection");

    hideElement(errorBox);

    if (!tc) {
        showElement(errorBox);
        errorBox.textContent = "Please select a test case before generating automation code.";
        return;
    }

    const framework = getElement("framework").value;
    const language = getElement("language").value;
    const baseUrl = getElement("baseUrl").value.trim() || state.baseUrl || "https://example.com";

    button.disabled = true;
    setText("automationButtonText", "Resolving Locators & Generating Code...");

    try {
        const data = await apiFetch("/generate-automation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                test_case: tc,
                framework,
                language,
                base_url: baseUrl,
                project_id: state.activeProjectId,
            }),
        });

        state.generatedCode = data.code || "";
        state.originalCode = data.code || "";
        
        const ext = getExt(language);
        const sanitizedTcName = (tc.title || tc.test_scenario || tc.id || "test")
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "_")
            .substring(0, 35);
        state.generatedFilename = data.filename || `test_${sanitizedTcName}_${framework}.${ext}`;

        showElement(codeSection);
        setText("codeFilename", state.generatedFilename);
        setText("codeFrameworkBadge", framework.toUpperCase());
        setText("codeLanguageBadge", language.toUpperCase());
        
        const editor = getElement("codeEditor");
        if (editor) {
            editor.value = state.generatedCode;
        }
        updateEditorMetrics();
        updateLineNumbers();
        setText("codeStatus", "Ready to edit or execute");

        showToast(`Generated ${framework.toUpperCase()} (${language}) automation script!`);
        await loadDashboardStats();
    } catch (err) {
        showElement(errorBox);
        errorBox.textContent = err.message || "Automation code generation failed.";
    } finally {
        button.disabled = false;
        setText("automationButtonText", "Generate Automation Code");
    }
}
window.generateAutomation = generateAutomation;

function getExt(language) {
    if (language === "java") return "java";
    if (language === "javascript") return "js";
    return "py";
}

function updateEditorMetrics() {
    const editor = getElement("codeEditor");
    if (!editor) return;
    const text = editor.value || "";
    const lines = text.length === 0 ? 0 : text.split("\n").length;
    const chars = text.length;
    setText("codeMetrics", `${lines} lines · ${chars} chars`);
}

function updateLineNumbers() {
    const editor = getElement("codeEditor");
    const lineNumbers = getElement("lineNumbers");
    if (!editor || !lineNumbers) return;
    const lines = (editor.value || "").split("\n").length;
    let numbers = "";
    for (let i = 1; i <= Math.max(lines, 1); i++) {
        numbers += i + "\n";
    }
    lineNumbers.textContent = numbers;
}


// ============================================================
// CODE EDITOR ACTIONS
// ============================================================

function setupCodeEditor() {
    const editor = getElement("codeEditor");
    const lineNumbers = getElement("lineNumbers");
    if (!editor) return;

    // Synchronize scrolling between editor and line numbers gutter
    editor.addEventListener("scroll", () => {
        if (lineNumbers) lineNumbers.scrollTop = editor.scrollTop;
    });

    // Handle Tab key indentation (insert 4 spaces)
    editor.addEventListener("keydown", (e) => {
        if (e.key === "Tab") {
            e.preventDefault();
            const start = editor.selectionStart;
            const end = editor.selectionEnd;
            editor.value = editor.value.substring(0, start) + "    " + editor.value.substring(end);
            editor.selectionStart = editor.selectionEnd = start + 4;
            state.generatedCode = editor.value;
            updateEditorMetrics();
            updateLineNumbers();
            setText("codeStatus", "Modified");
        }
    });

    // Real-time input updates
    editor.addEventListener("input", () => {
        state.generatedCode = editor.value;
        updateEditorMetrics();
        updateLineNumbers();
        setText("codeStatus", "Modified");
    });
}

function copyCode() {
    const editor = getElement("codeEditor");
    if (!editor || !editor.value) return;
    navigator.clipboard.writeText(editor.value);
    showToast("Code copied to clipboard!");
}
window.copyCode = copyCode;

function resetCode() {
    const editor = getElement("codeEditor");
    if (!editor) return;
    editor.value = state.originalCode;
    state.generatedCode = state.originalCode;
    updateEditorMetrics();
    updateLineNumbers();
    setText("codeStatus", "Reset to original");
    showToast("Reset code to original generated version.");
}
window.resetCode = resetCode;

async function saveCode() {
    const editor = getElement("codeEditor");
    if (!editor || !editor.value.trim()) {
        showToast("Code editor is empty.");
        return;
    }

    try {
        await apiFetch("/save-code", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                filename: state.generatedFilename,
                code: editor.value,
                project_id: state.activeProjectId,
                framework: getElement("framework").value,
                language: getElement("language").value,
                test_case_id: state.selectedTestCase?.id || null,
            }),
        });
        setText("codeStatus", "Saved to Database");
        showToast(`Saved '${state.generatedFilename}' to database!`);
        await loadDashboardStats();
    } catch (err) {
        showToast(err.message);
    }
}
window.saveCode = saveCode;

function downloadCode() {
    const editor = getElement("codeEditor");
    if (!editor || !editor.value) {
        showToast("No code available to download.");
        return;
    }
    const ext = getExt(state.language || "python");
    let filename = state.generatedFilename || `automation_test.${ext}`;
    if (!filename.endsWith("." + ext)) {
        filename = filename.replace(/\.[^/.]+$/, "") + "." + ext;
    }
    const mimeTypes = {
        py: "text/x-python;charset=utf-8",
        js: "application/javascript;charset=utf-8",
        java: "text/x-java-source;charset=utf-8"
    };
    const blob = new Blob([editor.value], { type: mimeTypes[ext] || "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Downloaded '${filename}'`);
}
window.downloadCode = downloadCode;


// ============================================================
// TEST EXECUTION RUNNER & DIAGNOSTICS
// ============================================================

async function executeAutomation() {
    const editor = getElement("codeEditor");
    const button = getElement("executeButton");
    if (!editor || !editor.value.trim()) {
        showToast("Code editor is empty. Generate code first.");
        return;
    }

    const framework = getElement("framework").value;
    const language = getElement("language").value;
    const baseUrl = getElement("baseUrl").value.trim() || state.baseUrl || "https://example.com";

    button.disabled = true;
    setText("executeButtonText", "Running Test Execution...");
    showSection("results");

    setText("resultStatus", "RUNNING");
    getElement("resultStatus").className = "result-status running-status";

    try {
        const result = await apiFetch("/execute-automation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code: editor.value,
                filename: state.generatedFilename,
                framework,
                language,
                base_url: baseUrl,
                test_case_id: state.selectedTestCase?.id || "",
                project_id: state.activeProjectId,
            }),
        });

        state.lastExecutionResult = result;
        renderExecutionResult(result);
        await loadDashboardStats();
        await loadExecutionHistory();
    } catch (err) {
        showToast(err.message);
    } finally {
        button.disabled = false;
        setText("executeButtonText", "Start Execution");
    }
}
window.executeAutomation = executeAutomation;

function renderExecutionResult(res) {
    const statusBadge = getElement("resultStatus");
    const summary = getElement("resultSummary");
    const outputPanels = getElement("outputPanels");

    if (res.status === "PASSED") {
        statusBadge.textContent = "PASSED";
        statusBadge.className = "result-status passed-status";
    } else {
        statusBadge.textContent = res.status || "FAILED";
        statusBadge.className = "result-status failed-status";
    }

    showElement(outputPanels);
    setText("outputText", res.output || "No console output produced.");
    setText("errorText", res.errors || "No error diagnostics produced.");

    summary.innerHTML = `
        <div class="result-details-grid">
            <div>
                <strong>Status:</strong>
                <span class="badge ${res.status === 'PASSED' ? 'badge-passed' : 'badge-failed'}">${res.status}</span>
            </div>
            <div>
                <strong>Failure Diagnosis:</strong>
                <span class="badge badge-failure">${res.failure_type || 'NONE'}</span>
            </div>
            <div>
                <strong>Duration:</strong>
                <span>${res.duration}s</span>
            </div>
            <div>
                <strong>Framework:</strong>
                <span>${escapeHtml(res.framework.toUpperCase())} (${escapeHtml(res.language)})</span>
            </div>
            <div>
                <strong>Script File:</strong>
                <span>${escapeHtml(res.filename)}</span>
            </div>
        </div>
    `;
}

async function loadExecutionHistory() {
    try {
        const history = await apiFetch(`/api/executions?project_id=${state.activeProjectId}`);
        state.executionHistory = history;
        
        const tbody = getElement("executionHistoryTableBody");
        if (!tbody) return;

        if (!history.length) {
            tbody.innerHTML = `<tr><td colspan="8" class="dashboard-empty">No execution logs in database for this project.</td></tr>`;
            return;
        }

        tbody.innerHTML = history.map(h => `
            <tr>
                <td><code>${h.id}</code></td>
                <td><strong>${escapeHtml(h.framework.toUpperCase())}</strong></td>
                <td>${escapeHtml(h.language)}</td>
                <td><span class="badge ${h.status === 'PASSED' ? 'badge-passed' : 'badge-failed'}">${h.status}</span></td>
                <td><span class="badge badge-failure">${h.failure_type}</span></td>
                <td>${h.duration}s</td>
                <td>${new Date(h.executed_at).toLocaleString()}</td>
                <td><button class="small-button danger-button" onclick="deleteExecutionRecord('${h.id}')">Delete</button></td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Failed to load execution history:", err);
    }
}

async function deleteExecutionRecord(id) {
    try {
        await apiFetch(`/api/executions/${id}`, { method: "DELETE" });
        showToast("Execution log deleted.");
        await loadExecutionHistory();
        await loadDashboardStats();
    } catch (err) {
        showToast(err.message);
    }
}
window.deleteExecutionRecord = deleteExecutionRecord;


// ============================================================
// AUTHENTICATION & SYSTEM HEALTH
// ============================================================

async function checkBackendHealth() {
    const dot = getElement("connectionDot");
    const text = getElement("connectionText");

    try {
        const health = await apiFetch("/health");
        if (health && health.status === "ok") {
            if (dot) dot.className = "status-dot online";
            if (text) text.textContent = "Backend Online";
        }
    } catch (err) {
        if (dot) dot.className = "status-dot offline";
        if (text) text.textContent = "Backend Offline";
    }
}

async function logoutUser() {
    try {
        await apiFetch("/logout", { method: "POST" });
        window.location.href = "/login";
    } catch (err) {
        window.location.href = "/login";
    }
}
window.logoutUser = logoutUser;

function openSwagger() {
    window.open("/docs", "_blank");
}
window.openSwagger = openSwagger;


// ============================================================
// UTILITIES & TOAST
// ============================================================

function showToast(message) {
    const toast = getElement("toast");
    const msg = getElement("toastMessage");
    if (!toast || !msg) return;

    msg.textContent = message;
    toast.classList.add("visible");
    setTimeout(() => toast.classList.remove("visible"), 3000);
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
