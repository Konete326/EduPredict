# EduPredict — Big Data & Predictive Analytics Educational SaaS Portal

EduPredict is an enterprise-grade academic intelligence and predictive analytics SaaS platform engineered to detect student dropout risks, evaluate learning trajectories, and deliver actionable early interventions. Powered by a pure Django MVT architecture, cloud-native MongoDB Atlas document persistence, and an embedded Scikit-learn predictive engine, EduPredict bridges institutional administration, educator workflows, data science research, and student academic success.

---

## Architecture & Tech Stack Overview

EduPredict is built with a strict pure Django MVT architecture, avoiding heavyweight frontend frameworks in favor of high-performance server-rendered HTML, atomic Tailwind CSS utility styling, and lightweight vanilla JavaScript.

```
+-----------------------------------------------------------------------------------+
|                                 Client Browser                                    |
|   (Responsive Viewport, Theme Studio Tokens, Chart.js v4, SPA Navigation Cache)   |
+-----------------------------------------------------------------------------------+
                                         |
                                         | HTTP / HTTPS / JSON / PDF
                                         v
+-----------------------------------------------------------------------------------+
|                           Django 6.1 Application Tier                             |
|                                                                                   |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  |   Accounts & RBAC  |  |   Panels & Views     |  |   Analytics & ML Pipeline |  |
|  |   - Auth / Session |  |   - Admin Services   |  |   - Model Training (RF/GB)|  |
|  |   - Guard Checks   |  |   - Teacher Roster   |  |   - Feature Preprocessing |  |
|  |   - Password Hash  |  |   - Student Portal   |  |   - Evaluation Metrics    |  |
|  +--------------------+  +----------------------+  +---------------------------+  |
|                                         |                                         |
|  +--------------------+  +--------------+-------+  +---------------------------+  |
|  | WhiteNoise Serving |  | In-Memory TTL Cache  |  | ReportLab PDF Engine      |  |
|  | Compressed Static  |  | Short-lived Queries  |  | Transcripts & Rosters     |  |
|  +--------------------+  +----------------------+  +---------------------------+  |
+-----------------------------------------------------------------------------------+
                                         |
                                         | PyMongo Connection Pool
                                         v
+-----------------------------------------------------------------------------------+
|                            MongoDB Atlas Cloud Cluster                            |
|                                                                                   |
|  - users              - student_records     - predictions     - datasets_log      |
|  - courses            - notifications       - support_tickets                     |
+-----------------------------------------------------------------------------------+
```

### Core Technologies

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | Python / Django | 3.12 / 6.1.3 | Server-rendered MVT architecture, sessions, and secure routing |
| **Database** | MongoDB Atlas / PyMongo | 4.20.0 | Cloud document store with thread-safe client connection pooling |
| **Styling & Design** | Tailwind CSS | v3 Engine | Fluid full-width CSS variable token system (`static/css/global.css`) |
| **Icons & Visuals** | FontAwesome 6 | Free CDN | Semantic iconography across tables, buttons, and badges |
| **Client Scripting** | Vanilla JavaScript | ES6+ | SPA-smooth page transitions, modal controllers, and theme sync |
| **Charts & Analytics** | Chart.js | v4+ | Theme-aware dynamic charting with auto-resize and dark-mode sync |
| **Machine Learning** | Scikit-learn / NumPy / Pandas | 1.9.1 / 2.5.5 / 3.1.1 | Embedded predictive modeling, dropout classification, ROC AUC |
| **Document Generation**| ReportLab | 5.1.0 | High-fidelity vector PDF academic transcripts and teacher rosters |
| **Static Serving** | WhiteNoise | 6.12.0 | Compressed, cached, and versioned static file delivery |
| **WSGI Server** | Gunicorn | 27.0.1 | Multi-worker, multi-threaded production HTTP application server |

---

## 4 Specialized Roles & Workbenches

EduPredict enforces strict Role-Based Access Control (RBAC). Each role accesses an isolated workbench with navigation tailored to their operational responsibilities.

```
+-----------------------------------------------------------------------------+
|                          Role Isolation Hierarchy                           |
+-------------------+--------------------+-------------------+----------------+
|    ADMIN          |     TEACHER        |     STUDENT       |    ANALYST     |
| System Control    | Academic Roster    | Personal Progress | ML Pipeline    |
| Audit & Users     | Ingestion & Alerts | PDF Transcripts   | Evaluation Lab |
+-------------------+--------------------+-------------------+----------------+
```

### 1. Administrator Workbench

The Administrator workbench provides governance, user provisioning, academic course catalog controls, institutional auditing, and disaster recovery.

* **Primary Route:** `/admin-panel/`
* **Sub-routes & Capabilities:**
  * `/admin-panel/users/` — Full user lifecycle management (Admin, Teacher, Student, Analyst). Supports creation, profile edits, and deactivation. Includes self-destruction protection preventing active administrators from deleting or deactivating their own accounts.
  * `/admin-panel/courses/` — Central course catalog management, enrollment caps, department filters, and instructor assignments.
  * `/admin-panel/tickets/` — Institutional support ticket management, status transitions (`OPEN`, `RESOLVED`), and inquiry resolution.
  * `/admin-panel/logs/` — System audit and user activity logs with severity categorization and one-click CSV export.
  * `/admin-panel/settings/` — Portal-wide configuration (maintenance mode, term dates, registration toggles).
  * `/admin-panel/backup/` — Full database backup download in structured JSON or CSV format across all collections.

### 2. Teacher Workbench

Designed for daily classroom operations, early identification of struggling learners, and rapid performance ingestion.

* **Primary Route:** `/teacher-panel/`
* **Sub-routes & Capabilities:**
  * `/teacher-panel/students/` — Class roster table with student search, GPA display, risk badges, and manual marks entry.
  * `/teacher-panel/students/export-pdf/` — One-click generation of official printable class performance rosters via ReportLab.
  * `/teacher-panel/ingest/` — Batch marks and attendance upload supporting CSV and Excel (`.xlsx`) files with flexible column alias detection and a 1.2-second cancelable auto-upload window.
  * `/teacher-panel/alerts/` — Real-time warning board surfacing students at high dropout risk, attendance deficits, or sharp grade declines.

### 3. Student Workbench

A personalized academic portal empowering students to track course milestones, review performance analytics, and download official credentials.

* **Primary Route:** `/student-panel/`
* **Sub-routes & Capabilities:**
  * `/student-panel/report/` — Comprehensive academic report card detailing subject marks, class attendance percentages, and GPA trajectories.
  * `/student-panel/report/download/` — Raw grade and attendance history download in CSV format.
  * `/student-panel/report/download-pdf/` — Official university-branded academic transcript generated dynamically via ReportLab with security verification badges.
  * `/student-panel/tips/` — Personalized AI study recommendations and intervention guidance tailored to performance weak points.
  * `/student-panel/notifications/` — Real-time notification center tracking attendance warnings, assignment reminders, and portal announcements.

### 4. Data Analyst Workbench

The research workbench for institutional data scientists to train, validate, and monitor machine learning models predicting student outcomes.

* **Primary Route:** `/analyst-panel/`
* **Sub-routes & Capabilities:**
  * `/analyst-panel/upload/` — Academic historical dataset ingestion with schema validation and missing-value profiling.
  * `/analyst-panel/run-ml/` — One-click retraining of predictive pipelines (Random Forest and Gradient Boosting classifiers).
  * `/analyst-panel/accuracy/` — Model accuracy metrics, cross-validation scores, and classification distribution charts.
  * `/analyst-panel/evaluation/` — Deep model evaluation laboratory with interactive Confusion Matrices, ROC AUC curves, and feature importance rankings.

### Shared User Capabilities

* `/profile/` — User profile editor with read-only role protections, contact updates, and password reset toggles.
* `/theme/preferences/` — Live Theme Studio supporting custom Chrome themes, accents, and dark modes.
* `/health/` — Real-time system diagnostic endpoint.

---

## Key Engineering & UX Features

### Live Theme Studio with Per-Role Isolation
* **OLED Dark & High-Contrast Light Modes:** Full color token parity via CSS variables defined in `static/css/global.css`.
* **13 Accent Palettes & 6 Chrome Themes:** Instant UI color customization (Indigo, Emerald, Violet, Amber, Rose, Cyan, Slate, etc.).
* **Per-Role Preference Persistence:** Preferences are stored per user and role (`ep_theme_prefs:<user_id>:<role>` in session and MongoDB `users.theme_prefs`), preserving tailored setups when switching accounts.
* **Live DOM Application:** CSS variables update dynamically without triggering full page reloads.

### ReportLab Vector PDF Engine
* **Branded Report Cards (`student_report_pdf`):** Generates official academic transcripts featuring institutional headers, student credentials, subject breakdown tables, risk status badges, and signature blocks.
* **Class Performance Rosters (`teacher_roster_pdf`):** Printable summary for instructors summarizing cohort metrics, class averages, at-risk rosters, and attendance rates.
* **Vector Quality:** Built using ReportLab Platypus flowables (`SimpleDocTemplate`, `Table`, `Paragraph`, `Spacer`) returning valid `%PDF-` streams directly in HTTP responses.

### 1.2-Second Cancelable Auto-Upload Grace Window
* **Smart File Ingestion:** Automatically validates drag-and-drop CSV or Excel files upon selection.
* **Cancelable Toast:** Provides an immediate 1200ms grace window with a visible countdown toast, allowing teachers to cancel mistaken uploads before transmission.
* **Graceful Fallback:** Cleans pending timeouts on SPA route transitions to avoid background leaks.

### Real-Time `/health/` Monitoring Endpoint
* **Deep MongoDB Connectivity Check:** Executes `admin.command("ping")` and measures round-trip database latency in milliseconds.
* **Collection Telemetry:** Counts total active documents across all 6 core collections (`users`, `student_records`, `predictions`, `courses`, `notifications`, `support_tickets`).
* **Cache Diagnostics:** Reports active in-memory TTL cache entries and operational status.
* **Standard HTTP Codes:** Returns HTTP 200 when healthy and HTTP 503 when the database is unreachable.

### Automated End-to-End Multi-Role UAT (`verify_uat`)
* **7-Stage Complete User Journey:** Validates all system operations via a single Django command (`python manage.py verify_uat`):
  1. System Health & DB Ping Latency
  2. Authentication, Session Provisioning & Profile Update
  3. Administrator User Management & Self-Protection Guard Verification
  4. Teacher Roster Listing, Grade Ingestion & PDF Generation
  5. Analyst Dashboard & Model Evaluation Verification
  6. Student Overview, Report Card & Vector PDF Transcript Download
  7. Support Ticket Submission, Admin Resolution & Theme Preference Persistence

---

## Quickstart Guide

Follow these steps to run EduPredict locally in development mode.

### Prerequisites
* Python 3.11 or Python 3.12
* Node.js 20+ (required only for static syntax checks with `node --check`)
* MongoDB Atlas cluster or local MongoDB instance (version 6.0+)
* Git

### Step-by-Step Installation

```bash
git clone https://github.com/your-org/edupredict.git
cd edupredict
```

```bash
python -m venv .venv
```

Activate the virtual environment:
* **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
* **Linux / macOS:**
  ```bash
  source .venv/bin/activate
  ```

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```ini
SECRET_KEY=generate-a-secure-random-secret-key
DEBUG=True
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/edupredict_db?retryWrites=true&w=majority
MONGODB_DB_NAME=edupredict_db
ADMIN_EMAIL=admin@edupredict.edu
ADMIN_PASSWORD=AdminSecurePassword2026!
ADMIN_FULL_NAME=System Administrator
```

```bash
python manage.py migrate
```

On first startup, EduPredict automatically verifies database connectivity, applies compound indexes, and seeds the default system administrator configured in `.env`.

```bash
python manage.py runserver 0.0.0.0:8000
```

Open your browser at `http://127.0.0.1:8000/`. You will be redirected to `/auth/` where you can sign in using your configured administrator credentials.

```bash
python manage.py check
python manage.py test
python manage.py verify_uat
```

---

## Production Deployment & Docker

EduPredict is containerized using a hardened multi-stage Docker build and served through Gunicorn with WhiteNoise static compression.

### Multi-Stage Dockerfile Architecture

The `Dockerfile` separates the build toolchain from the minimal runtime environment:

1. **Builder Stage (`python:3.12-slim`):** Compiles Python wheels using `build-essential` and installs dependencies into `/install`.
2. **Runner Stage (`python:3.12-slim`):**
   * Copies only installed site-packages from the builder stage.
   * Creates a dedicated non-root system group and user (`edupredict:edupredict`).
   * Configures built-in Docker `HEALTHCHECK` targeting `http://localhost:8000/health/`.
   * Executes via Gunicorn with 3 workers and 2 threads.

### Running with Docker Compose

A production-ready `docker-compose.yml` is provided at the root:

```bash
docker compose up --build -d
```

Check container status and healthcheck logs:

```bash
docker compose ps
docker compose logs -f web
```

To stop the service:

```bash
docker compose down
```

### Production Static File Handling

Static assets (CSS, JavaScript, vendor libraries) are handled directly by Django and WhiteNoise without requiring external reverse proxy configuration for static files:

```bash
python manage.py collectstatic --noinput
```

WhiteNoise is configured in `config/settings.py` with `CompressedManifestStaticFilesStorage`, providing Gzip/Brotli compression and content hash cache busting (`?v=8`).

---

## Operations & Monitoring Runbook

This Operations Runbook provides technical specifications for database connection pooling, healthcheck monitoring, automated CI/CD pipelines, and disaster recovery procedures.

### MongoDB Connection Pooling

EduPredict manages MongoDB connections through a thread-safe singleton (`core/db.py`). Customize connection pooling parameters in `.env`:

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MONGODB_MAX_POOL_SIZE` | `50` | Maximum number of concurrent connections in the connection pool |
| `MONGODB_MIN_POOL_SIZE` | `2` | Minimum number of idle connections maintained in the pool |
| `MONGODB_MAX_IDLE_TIME_MS` | `45000` | Milliseconds after which an idle connection is closed (45 seconds) |
| `MONGODB_SOCKET_TIMEOUT_MS` | `10000` | Milliseconds to wait on socket read/write operations (10 seconds) |
| `MONGODB_SERVER_SELECTION_TIMEOUT_MS` | `3000` | Milliseconds to wait for server selection during replica set discovery |
| `MONGODB_CONNECT_TIMEOUT_MS` | `3000` | Milliseconds allowed for establishing a raw TCP connection |

### Healthcheck Endpoint Specification

* **Path:** `GET /health/`
* **Authentication:** Public / No session required (accessible to load balancers)
* **Response Statuses:**
  * `200 OK` — MongoDB ping succeeded, cluster healthy.
  * `503 Service Unavailable` — MongoDB unreachable or connection timeout.

#### Sample Healthy JSON Response

```json
{
  "status": "healthy",
  "database": "connected",
  "latency_ms": 4.12,
  "counts": {
    "users": 28,
    "student_records": 150,
    "predictions": 150,
    "courses": 12,
    "notifications": 45,
    "support_tickets": 8
  },
  "collections": {
    "users": 28,
    "student_records": 150,
    "predictions": 150,
    "courses": 12,
    "notifications": 45,
    "support_tickets": 8
  },
  "cache": {
    "entries": 5,
    "status": "active"
  },
  "memory": {
    "status": "healthy",
    "cache_entries": 5
  }
}
```

### Automated GitHub Actions CI Pipeline

The continuous integration pipeline is defined in `.github/workflows/django.yml` and triggers automatically on every push to `main`, `feature/**`, and pull requests targeting `main`.

1. **Environment Setup:** Provision Ubuntu runner with Python 3.12 and Node.js 20.
2. **Dependency Resolution:** Upgrade `pip` and install locked packages from `requirements.txt`.
3. **Django System Check:** Execute `python manage.py check` to catch configuration and template errors.
4. **JavaScript Syntax Verification:** Run `node --check` across `app.js`, `nav.js`, `charts.js`, `theme_studio.js`, and `analyst_evaluation.js`.
5. **Django Unit & Integration Tests:** Run `python manage.py test`.
6. **End-to-End Multi-Role UAT:** Run `python manage.py verify_uat` across all 7 user journeys.
7. **Static Asset Verification:** Run `python manage.py collectstatic --noinput --dry-run` to ensure all asset paths and hashes compile cleanly.

### Backup & Disaster Recovery Procedures

#### 1. Portal Web Export (Self-Service)
Administrators can trigger full data exports through the web interface:
* **JSON Export:** Navigate to `/admin-panel/backup/?format=json` to download `edupredict_backup_<timestamp>.json`.
* **CSV Export:** Navigate to `/admin-panel/backup/?format=csv` to download `edupredict_backup_<timestamp>.csv`.

#### 2. Enterprise MongoDB Atlas Snapshots (Recommended)
For production environments, utilize native Atlas automated continuous cloud backups with point-in-time recovery (PITR).

#### 3. Database Dump & Restore via CLI
To perform cold backup and restore via standard MongoDB utilities:

```bash
mongodump --uri="mongodb+srv://<username>:<password>@cluster.mongodb.net/edupredict_db" --out=./backups/$(date +%Y%m%d_%H%M%S)
```

```bash
mongorestore --uri="mongodb+srv://<username>:<password>@cluster.mongodb.net/edupredict_db" --drop ./backups/<timestamp>/edupredict_db
```

---

## Security & Best Practices

* **CSRF Protection:** Enabled across all form submissions with Django CSRF token validation.
* **Password Hashing:** Passwords hashed with PBKDF2 with SHA-256 iterations.
* **Session Security:** Cookie security configured with `SESSION_COOKIE_HTTPONLY=True` and `SESSION_COOKIE_SAMESITE='Lax'`.
* **Zero Comment Standard:** Production codebase adheres to self-documenting clean code standards with zero clutter comments.
* **Self-Action Guard:** Administrators cannot deactivate, downgrade, or delete their own active credentials.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.
