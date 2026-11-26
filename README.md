# EduPredict - Educational Analytics & Early Warning Portal

EduPredict is an enterprise-grade academic analytics and early warning platform built with Python 3.12, Django (MVT architecture), MongoDB Atlas, Tailwind CSS, Vanilla JS, and ReportLab. It identifies student attrition patterns, predicts semester GPA, flags academic anomalies, and empowers educators with real-time intervention tools, a single-institute CSV auto-provisioning workflow, a Multi-Agent AI Message Dock, and a 21st.dev-inspired public showcase & Curated Theme Studio.

- **GitHub Repository:** https://github.com/Konete326/EduPredict
- **Live Deployment (Vercel):** https://edupredict.vercel.app (`vercel.json` + `config/wsgi.py`, auto-deployed from GitHub `main` on every push)

---

## Key Capabilities & Role Panels

EduPredict strictly isolates four role-based dashboard panels:

1. **Admin Panel (`/admin-panel/`)**
   - **Master Training CSV Ingestion (`/admin-panel/training/`):** Dedicated `Training Data` sidebar page for one-time historical dataset upload (`is_training_dataset=True`) to train the ML suite without polluting live teacher/admin class rosters.
   - **User Lifecycle & Teacher Approvals:** Approve or reject pending Teacher signups with audited reasons, plus role protection and self-deactivation guards (`data-is-self="true"`).
   - **Course Catalog & Portal Settings:** Manage courses, capacity limits, risk thresholds, and the **Admin-only Curated Theme Studio** (21st.dev presets with per-theme text contrast tokens).
   - **Audit Logs & Backups:** Filterable activity logs, incoming Admin support tickets, and full-database JSON/CSV backup exports (`export_backup`).

2. **Teacher Panel (`/teacher-panel/`)**
   - **Strict Teacher Data Isolation:** Each approved Teacher views and manages only their own uploaded class records and assigned courses.
   - **Class CSV Upload & Auto Student Provisioning:** Uploading a class CSV (`student_id, full_name, birth_date, course_code, marks, attendance`) automatically creates/updates student accounts (`student_id` + `<first_name>@<birth_date>`) and runs live ML GPA/risk predictions.
   - **1-Click Credentials CSV Download:** Export `class_student_credentials.csv` directly via `/teacher-panel/credentials/download/` to share login details with students.
   - **Student 360°, Risk Alerts & Feedback Inbox:** Inline marks/attendance editing, Student 360° drawer, 1-click high-risk alerts, incoming Student Feedback inbox, and official A4 PDF class roster export (`/teacher-panel/students/export-pdf/`).

3. **Student Panel (`/student-panel/`)**
   - **Student ID Login & Strictly Read-Only Dashboard:** Students sign in at `/auth/` with their `student_id` and `<first_name>@<birth_date>` to view live marks, attendance, predicted GPA, dropout risk status, and assigned teacher details.
   - **Dual Feedback System:** Send feedback or support requests directly to either the **Assigned Teacher** (routed to Teacher Alerts inbox) or **Portal Admin** (routed to Admin Tickets).
   - **AI Study Tips & Official A4 Report Card:** Personalized weekly recovery plans plus zero-UI monochrome A4 printable & downloadable PDF/CSV transcripts (`/student-panel/report/download-pdf/`).

4. **Data Analyst Panel (`/analyst-panel/`)**
   - **Big Data & ML Evaluation Hub:** Leakage-free train/test diagnostics for `RandomForestClassifier`, `Ridge`, and `IsolationForest` with automated missing-value imputation.
   - **Live LMS Stream Simulator:** Real-time streaming ticks (`/analyst-panel/stream-tick/`) with live Recent Uploads sync, prediction table auto-hydration, and background tab pause guards.

---

## Single-Institute Workflow (End-to-End)

1. **Admin Uploads Master Training CSV:** Sign in as Admin and upload `sample_datasets/admin_master_training_dataset.csv` at `/admin-panel/training/` (`Training Data` in sidebar). Records are stored with `is_training_dataset=True` to train the ML models while staying isolated from live class rosters.
2. **Teacher Approval:** Teachers register at `/auth/` and wait for Admin approval in `/admin-panel/users/`.
3. **Teacher Uploads Class CSV & Auto-Provisions Students:** Approved Teachers upload their class CSV (e.g., `sample_datasets/teacher_cs101_class.csv`) at `/teacher-panel/ingest/`. EduPredict automatically tags records to that teacher, creates/updates student logins (`student_id` + `<first_name>@<birth_date>`), and generates ML predictions.
4. **Teacher Downloads Student Credentials CSV:** Click **Download Credentials CSV** (`/teacher-panel/credentials/download/`) to export `class_student_credentials.csv` for class distribution.
5. **Student Sign-In & Dual Feedback:** Students sign in at `/auth/` using their `student_id` and `<first_name>@<birth_date>`, inspect their read-only academic progress & A4 report card, and send feedback to either their Teacher or Admin.

---

## Sample Datasets Guide (`sample_datasets/`)

Ready-to-use CSVs are included in [`sample_datasets/`](sample_datasets/README.md) for instant end-to-end testing and demos:

| File | Rows | Scope | Key Columns |
| :--- | ---: | :--- | :--- |
| `admin_master_training_dataset.csv` | 200 | Admin one-time ML training (`LOW`: 70, `MEDIUM`: 65, `HIGH`: 65) | `student_id,full_name,birth_date,department,course_code,attendance_pct,internal_marks,assignment_score,lms_hours_per_week,previous_gpa,final_gpa,dropout_risk` |
| `teacher_cs101_class.csv` | 18 | `CS-101` (Computer Science) | `student_id,full_name,birth_date,course_code,marks,attendance` |
| `teacher_ds301_class.csv` | 18 | `DS-301` (Data Science) | `student_id,full_name,birth_date,course_code,marks,attendance` |
| `teacher_se210_class.csv` | 18 | `SE-210` (Software Engineering) | `student_id,full_name,birth_date,course_code,marks,attendance` |
| `teacher_ml401_class.csv` | 18 | `ML-401` (Machine Learning) | `student_id,full_name,birth_date,course_code,marks,attendance` |
| `teacher_ai205_class.csv` | 18 | `AI-205` (Artificial Intelligence) | `student_id,full_name,birth_date,course_code,marks,attendance` |
| `teacher_la110_class.csv` | 18 | `LA-110` (Mathematics) | `student_id,full_name,birth_date,course_code,marks,attendance` |

**Example Student Login (after uploading `teacher_cs101_class.csv`):** Username `EDU-2026-101`, Password `maham@2005-03-19`.

---

## Public Showcase & Curated Theme Studio (21st.dev Upgrades)

- **21st.dev Provably Hero & Live Walkthrough:** Public landing page (`/`) dynamically hydrates live student credential cards and walkthrough previews directly from MongoDB via `accounts/public_data.py` (60s TTL cache).
- **Live Testimonial Globe:** Interactive global campus testimonial showcase backed by real MongoDB `support_tickets` and active `users`.
- **Curated Theme Studio:** 21st.dev-curated Light/Dark theme presets with per-theme text contrast tokens (`static/css/global.css`), Ocean Blue default, and scoped persistence.

---

## Enterprise UI/UX Standards

- **Minimalist Lists + `View` Modal (`openViewDetailsModal`):** All data tables across all panels display only 3–4 essential columns (`Name/Title`, `Role/Meta`, `Status`, `Actions`) and place full metadata (IDs, emails, timestamps, batches, full messages) inside a `View` (`fa-eye`) detail modal.
- **Bento Grid Modals:** Any form modal with `>= 5` visible fields renders in a desktop 2-column Bento Grid (`max-w-2xl`, `md:grid-cols-2`) instead of a tall vertical stack.
- **Clean Dashboards & Dedicated Training Data:** Role dashboards stay minimal (`Header + 4 KPIs + 2 Graphs + 1 concise card`), and Admin Master Training CSV lives on its dedicated `/admin-panel/training/` page (`Training Data` in sidebar).
- **Draggable AI Assistants Dock:** `#ep-agent-dock-toggle` is draggable anywhere on screen with `sessionStorage` position persistence.

---

## Architecture Overview

```text
[ Browser Clients: Chrome / Firefox / Safari / Edge ]
                       │
       HTTP / HTTPS (Reverse Proxy / Nginx / Direct)
                       ▼
      [ Gunicorn WSGI Server: 3 Workers / Port 8000 ]
                       │
        [ Django Application Server (MVT) ]
   ├── Authentication & RBAC Middleware (@role_required)
   ├── Role Views (Admin, Teacher, Student, Analyst)
   ├── Analytics Engine (Pandas, NumPy, Scikit-Learn)
   ├── PDF Generation Engine (ReportLab)
   ├── Live Theme Studio Service (CSS Variable Tokenization)
   └── WhiteNoise Middleware (Compressed Static Serving)
                       │
             PyMongo Connection Pool
                       ▼
    [ MongoDB Atlas Cloud Database: edupredict_db ]
   ├── users (RBAC, credentials, scoped theme preferences)
   ├── courses (catalog, department, instructor mapping)
   ├── student_records (marks, attendance, activity logs)
   ├── predictions (ML risk scores, anomalies, suggestions)
   ├── notifications (targeted alerts with real-time sync)
   ├── support_tickets (issue resolution tracking)
   ├── activity_logs (audit trail and actor attribution)
   └── system_settings (dynamic operational thresholds)
```

---

## Quickstart Guide

### Option 1: Local Development Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Konete326/EduPredict.git
   cd EduPredict
   ```

2. **Set Up Python Virtual Environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .\.venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables (`.env`):**
   ```env
   SECRET_KEY=your-secure-django-secret-key
   DEBUG=True
   MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/edupredict_db?retryWrites=true&w=majority
   MONGODB_DB_NAME=edupredict_db
   ADMIN_EMAIL=admin@edupredict.edu
   ADMIN_PASSWORD=Admin@123
   ADMIN_FULL_NAME=System Administrator
   ```

5. **Run Django System Check & Dev Server:**
   ```bash
   python manage.py check
   python manage.py runserver
   ```
   Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

---

### Option 2: Docker Containerization

Run the multi-stage production container with a single command:
```bash
docker compose up --build -d
```

Verify container status:
```bash
docker compose ps
curl http://localhost:8000/health/
```

---

## Automated Verification & Testing

### 1. Unit & Integration Test Suite (98 Tests)
```bash
python manage.py test
```

### 2. End-to-End Multi-Role UAT Simulator (7/7 Checks)
Simulates Health, Auth/RBAC, Admin self-lock, Teacher marks & PDF roster, Analyst ML, Student overview & PDF report card, and Support ticket workflow:
```bash
python manage.py verify_uat
```

### 3. JavaScript Syntax Verification
```bash
node --check static/js/app.js
node --check static/js/nav.js
node --check static/js/charts.js
node --check static/js/theme_studio.js
node --check static/js/analyst_evaluation.js
```

---

## Operations & Monitoring Runbook

### 1. Real-Time System Health Endpoint (`/health/`)
Provides sub-second uptime monitoring with live MongoDB ping, connection pool latency, and collection record counts:
```bash
curl -s http://localhost:8000/health/
```
Sample JSON Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "latency_ms": 12.5,
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
    "entries": 14,
    "status": "active"
  },
  "memory": {
    "status": "healthy",
    "cache_entries": 14,
    "rss_mb": 142.5,
    "container_limit_mb": 512.0,
    "container_usage_pct": 27.83
  }
}
```
Collection counts are cached for 30 seconds; append `?fresh=1` to force a live refresh. `container_limit_mb` and `container_usage_pct` appear only when a Linux cgroup memory limit is set. On failure the endpoint returns HTTP 503 with `"status": "unhealthy"`.

### 2. MongoDB Atlas Connection Pooling Configuration
Tunable via environment variables:
* `MONGODB_MAX_POOL_SIZE`: Maximum concurrent sockets (default: 50).
* `MONGODB_MIN_POOL_SIZE`: Minimum pre-warmed sockets (default: 2).
* `MONGODB_MAX_IDLE_TIME_MS`: Idle socket cleanup threshold (default: 45000 ms).
* `MONGODB_SOCKET_TIMEOUT_MS`: Query execution timeout (default: 10000 ms).

### 3. Automated Database Backup Command (`export_backup`)
Export the entire database state into JSON or CSV for offsite backup or cron scheduling, with automatic old backup retention pruning:
```bash
python manage.py export_backup --format json --output-dir backups/ --retention-days 30
python manage.py export_backup --format csv --output-dir backups/ --quiet
```
Alternatively, administrators can trigger downloads from the UI at `/admin-panel/backup/?format=json` or `/admin-panel/backup/?format=csv`.

Each backup also gets a `<file>.sha256` sidecar manifest. Verify integrity at any time (a mismatch exits with an error):
```bash
python manage.py verify_backup backups/<file>.json
```

Optional encryption (Fernet): set `BACKUP_ENCRYPTION_KEY` in `.env` (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) and add `--encrypt`. The file is saved as `<name>.enc`; `verify_backup` also confirms it decrypts with the configured key. Keep the key safe, because backups cannot be restored without it:
```bash
python manage.py export_backup --format json --output-dir backups/ --encrypt
```
To restore a plain file from an encrypted backup (refuses to overwrite unless `--overwrite` is given):
```bash
python manage.py decrypt_backup backups/<file>.json.enc
```

### 4. Automated GitHub Actions CI & Vercel Auto-Deploy (`.github/workflows/django.yml`)
Triggers on every push to `main`, `feature/**`, and pull requests targeting `main`:
1. **Ubuntu Runner:** Python 3.12 + Node.js 20.
2. **System Check:** `python manage.py check`.
3. **JS Syntax Audit:** `node --check` across all 13 `static/js/*.js` scripts.
4. **Unit Test Suite:** Full Django test runner execution (`python manage.py test`).
5. **Multi-Role UAT:** `python manage.py verify_uat`.
6. **Static Verification:** `python manage.py collectstatic --noinput --dry-run`.
7. **Vercel Continuous Deployment:** Connected directly to `Konete326/EduPredict` (`main` branch) via Vercel Git integration (`vercel.json`), so every push to `main` automatically builds and deploys live.

### 5. Rate Limiting (Per-Worker Limits)
Endpoints such as `/health/` use an in-memory rate limiter that returns `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and (on HTTP 429) `Retry-After`.

> **Note:** Counters live in each worker process memory and are not shared. The Docker image runs gunicorn with 2 workers (`${PORT:-7860}`), so the effective limit per client IP can reach up to `workers x max_requests`. Use a shared store such as Redis, or a limit at the reverse proxy, if you need a strict global limit.

---

## Default Admin & Role Onboarding Credentials

| Role | Username / Email | Password | Primary Route | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin@gmail.com` | `admin123` | `/admin-panel/` | Seeded automatically via `ADMIN_EMAIL` / `ADMIN_PASSWORD` |
| **Teacher** | Self-Register / Admin Invite | User-Chosen | `/teacher-panel/` | Pending Admin approval in `/admin-panel/users/` |
| **Student** | `student_id` (e.g. `EDU-2026-101`) | `<first_name>@<birth_date>` | `/student-panel/` | Auto-provisioned when Teacher uploads class CSV (exportable via `/teacher-panel/credentials/download/`) |
| **Analyst** | Created by Admin | Admin-Assigned | `/analyst-panel/` | Provisioned inside `/admin-panel/users/` |

---

## Production Security Checklist

When deploying with `DEBUG=False`:
- `SECURE_BROWSER_XSS_FILTER` and `SECURE_CONTENT_TYPE_NOSNIFF` are active.
- `X_FRAME_OPTIONS` is locked to `DENY` (and CSP permits Hugging Face frame embedding when hosted inside Spaces).
- `SECURE_PROXY_SSL_HEADER` and `USE_X_FORWARDED_HOST` are configured for reverse proxies (HF Spaces, Render, Railway, Koyeb).
- `SECURE_HSTS_SECONDS` defaults to 31,536,000 (1 year) with subdomains and preload enabled.
- `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are enforced over HTTPS.
- WhiteNoise automatically serves compressed and cached assets from `staticfiles/`.
- Container native `HEALTHCHECK` monitors `http://localhost:7860/health/`.
- Theme-aware custom `500.html` and `404.html` error pages prevent stack trace exposure.
