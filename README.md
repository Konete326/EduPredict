# EduPredict - Educational Analytics & Early Warning Portal

EduPredict is an enterprise-grade academic analytics and early warning platform built with Python 3.12, Django (MVT architecture), MongoDB Atlas, Tailwind CSS, Vanilla JS, and ReportLab. It identifies student attrition patterns, predicts semester GPA, flags academic anomalies, and empowers educators with real-time intervention tools.

---

## Key Capabilities & Role Panels

EduPredict strictly isolates four role-based dashboard panels:

1. **Admin Panel (`/admin-panel/`)**
   - User lifecycle management with role protection and self-deactivation guards (`data-is-self="true"`).
   - Course catalog, capacity limits, and instructor assignments.
   - Comprehensive system activity audit logs with actor attribution and manual notes.
   - Dynamic portal settings (risk thresholds, minimum attendance rules).
   - Full-database backup exports in JSON and CSV formats (`export_backup` command & portal export).

2. **Teacher Panel (`/teacher-panel/`)**
   - Real-time student roster with search, filter, and 5-row pagination.
   - Frictionless inline marks and attendance updates.
   - Instant student risk notifications and alert history.
   - Official academic class roster PDF export with sign-off blocks (`/teacher-panel/students/export-pdf/`).

3. **Student Panel (`/student-panel/`)**
   - Personal academic performance dashboard, subject comparisons, and batch standing.
   - AI-driven study recommendations and attendance recovery plans.
   - Printable and downloadable official report card in PDF and CSV formats (`/student-panel/report/download-pdf/`).
   - Notification center for alerts dispatched by course instructors.

4. **Data Analyst Panel (`/analyst-panel/`)**
   - High-throughput CSV/Excel dataset ingestion with automated missing-data imputation.
   - Machine learning evaluation pipeline with leakage-free train/test splits.
   - Comparative model diagnostics (Random Forest Classifier, Ridge Regression, Isolation Forest).
   - Automated risk alert dispatch on high-risk prediction generation.

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

### 4. Automated GitHub Actions CI Pipeline (`.github/workflows/django.yml`)
Triggers on every push to `main`, `feature/**`, and pull requests targeting `main`:
1. **Ubuntu Runner:** Python 3.12 + Node.js 20.
2. **System Check:** `python manage.py check`.
3. **JS Syntax Audit:** `node --check` across all 5 JavaScript scripts.
4. **Unit Test Suite:** Full Django test runner execution.
5. **Multi-Role UAT:** `python manage.py verify_uat`.
6. **Static Verification:** `python manage.py collectstatic --noinput --dry-run`.

### 5. Rate Limiting (Per-Worker Limits)
Endpoints such as `/health/` use an in-memory rate limiter that returns `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and (on HTTP 429) `Retry-After`.

> **Note:** Counters live in each worker process memory and are not shared. The Docker image runs gunicorn with 3 workers, so the effective limit per client IP can reach up to `workers x max_requests` (for example, 3 x 120 = 360 requests per minute on `/health/`). Use a shared store such as Redis, or a limit at the reverse proxy, if you need a strict global limit.

---

## Default Seed Credentials

| Role | Email | Password | Primary Route |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@edupredict.edu` | `Admin@123` | `/admin-panel/` |
| **Teacher** | `teacher@edupredict.edu` | `Teacher@123` | `/teacher-panel/` |
| **Student** | `student@edupredict.edu` | `Student@123` | `/student-panel/` |
| **Analyst** | `analyst@edupredict.edu` | `Analyst@123` | `/analyst-panel/` |

---

## Production Security Checklist

When deploying with `DEBUG=False`:
- `SECURE_BROWSER_XSS_FILTER` and `SECURE_CONTENT_TYPE_NOSNIFF` are active.
- `X_FRAME_OPTIONS` is locked to `DENY`.
- `SECURE_HSTS_SECONDS` defaults to 31,536,000 (1 year) with subdomains and preload enabled.
- `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are enforced over HTTPS.
- WhiteNoise automatically serves compressed and cached assets from `staticfiles/`.
- Container native `HEALTHCHECK` monitors `http://localhost:8000/health/`.
- Theme-aware custom `500.html` and `404.html` error pages prevent stack trace exposure.
