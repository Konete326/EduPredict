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
- **Automated Preprocessing (`services/data_pipeline.py`):**
  1. Validates required columns (`student_id`, `attendance_pct`, `internal_marks`, `lms_hours`, `previous_gpa`, `course_code`).
  2. Automatically fills missing numeric values using median imputation and categorical values using mode imputation so the system never crashes on incomplete data.
  3. Stores partitioned document collections in MongoDB Atlas with indexing on `student_id`, `batch`, and `timestamp`.

### 2.3. Predictive Analytics & Anomaly Workflow (`services/ml_engine.py`)
- Triggered automatically whenever a new dataset is uploaded or when the Analyst clicks "Retrain & Predict".
- **Algorithms Used (Lightweight & Fast):**
  - *Dropout Classification:* Random Forest / Logistic Regression (`Low` < 35%, `Medium` 35–70%, `High` > 70%).
  - *Score Prediction:* Linear / Ridge Regression (`predicted_gpa`).
  - *Anomaly Detection:* Isolation Forest / Z-Score threshold (flags students whose attendance or score drops > 25% suddenly).
- **Automated Alert Generation:** Whenever a student is classified as `High` dropout risk or an anomaly is detected, the system automatically inserts an alert document in the `notifications` collection for both the Student and their assigned Teacher.

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