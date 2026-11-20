# System Requirements Document (SRD) — EduPredict

## 1. System Architecture Overview
EduPredict follows a modular, beginner-friendly **Django MVT (Model-View-Template)** architecture integrated with **MongoDB Atlas** as the primary cloud database and **scikit-learn / pandas** as the embedded analytical processing engine.

[ Browser: Django Templates + Tailwind CSS + Chart.js + FontAwesome ]
|
(HTTP Requests / JSON)
v
[ Django Application Server: URLs -> Role Middleware -> Modular Views ]
|                                               |
(Data Operations)                               (ML & Data Pipeline)
v                                               v
[ MongoDB Atlas Cloud DB ]                     [ Pandas + Scikit-Learn ]
(Users, Records, Predictions, Alerts)          (Cleaning, Batch/Stream, ML)


## 2. Functional System Specifications

### 2.1. Role-Based Access Control (RBAC)
- Every user account contains a strict `role` field: `ADMIN`, `TEACHER`, `STUDENT`, or `ANALYST`.
- Custom Django Decorator (`@role_required(['ADMIN'])`) protects every view. If a Student tries to open `/admin-panel/`, the system redirects them back to `/student-panel/` with a clean Toast notification.

### 2.2. Automated Data Ingestion & Cleaning Pipeline
- **Supported Formats:** `.csv`, `.xlsx`, and standard web form inputs.
- **Automated Preprocessing (`analytics/data_pipeline.py` & `analytics/preprocessing.py`):**
  1. **Smart CSV Column Auto-Mapper:** Automatically maps common institutional header aliases (`Roll_No`, `Enrollment`, `Reg_No` -> `student_id`; `Attendance`, `Att_%` -> `attendance_pct`; `Marks`, `Score`, `Test_Score` -> `internal_marks`; `Prev_GPA` -> `previous_gpa`; `LMS_Hours` -> `lms_hours_weekly`) so staff uploads succeed without manual renaming.
  2. Automatically fills missing numeric values using median imputation and categorical values using mode imputation so the system never crashes on incomplete data.
  3. Stores partitioned document collections in MongoDB Atlas with indexing on `student_id`, `batch`, and `timestamp`.

### 2.3. Predictive Analytics, Auto-Escalation & Real-Time Stream (`analytics/ml_engine.py`)
- **Zero-Click ML Execution:** Triggered automatically whenever a Teacher updates marks/attendance or an Analyst uploads a dataset (eliminating manual retraining clicks).
- **Algorithms Used (Lightweight & Fast):**
  - *Dropout Classification:* `RandomForestClassifier(n_estimators=50, n_jobs=-1)` (`Low` < 35%, `Medium` 35–70%, `High` > 70%).
  - *Score Prediction:* Ridge Regression (`predicted_gpa` 0.0–4.0, millisecond training, noise-resistant linear model).
  - *Anomaly Detection:* Isolation Forest + rule thresholds (flags students whose attendance or score drops > 25% suddenly).
- **Zero-Click Auto-Alert Escalation & Bulk Notify:** Whenever `attendance < 75%`, `risk == HIGH`, or an anomaly is detected, automatically dispatch an encouraging tip notification to the Student and a warning alert to Teachers (deduplicated), plus support 1-click "Notify All High-Risk Students" in Teacher Alerts.
- **Real-Time LMS Stream Simulator (Phase 63):** Optional Analyst live-stream toggle pushing 2–3 simulated LMS/attendance events every 5 seconds into MongoDB with live anomaly flagging for real-time streaming demos.

## 3. Non-Functional Requirements (NFRs)

### 3.1. Performance & Big Data Handling
- Batch uploads up to 50,000 rows are processed in chunks using `pandas` and inserted into MongoDB Atlas via `insert_many(..., ordered=False)` for sub-second batch writes.
- Dashboard queries use MongoDB aggregation pipelines (`$match`, `$group`, `$project`) so pages load in under 1.5 seconds.

### 3.2. Security & Data Integrity
- Passwords hashed using Django's PBKDF2/Argon2 hashing.
- CSRF protection enabled on all POST forms and AJAX requests.
- Environment variables (`.env`) used for `MONGODB_URI` and `SECRET_KEY` — credentials are never hardcoded in code.

### 3.3. Reliability, Usability & Accessibility
- Graceful fallback: If MongoDB Atlas has a temporary network hiccup or an uploaded file is corrupted, the user sees a clean, theme-aware Custom Modal explaining the issue instead of a yellow Django debug crash page.
- 100% Mobile-First Responsive layout (320px mobile up to 1920px desktop).
- Strict Light and Dark mode parity with WCAG AA contrast ratios.

## 4. Hardware & Software Requirements
- **Hardware:** Minimum Intel Core i5 (4 Cores), 8–16 GB RAM, 256 GB SSD.
- **Software Stack:**
  - Python 3.11+
  - Django 5.x (Latest Stable)
  - MongoDB Atlas (Cloud URI via `pymongo` / `mongoengine` or `djongo`)
  - Pandas, NumPy, Scikit-Learn, OpenPyXL (Latest Stable)
  - Tailwind CSS + FontAwesome Icons + Chart.js (Configured globally in `base.html`)