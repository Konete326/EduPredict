# EduPredict - Educational Analytics & Early Warning Portal

EduPredict is an enterprise-grade academic analytics and early warning platform built with Python 3.12, Django (MVT architecture), MongoDB Atlas, Tailwind CSS, Vanilla JS, and ReportLab. It identifies student attrition patterns, predicts semester GPA, flags academic anomalies, and empowers educators with real-time intervention tools.

---

## Key Capabilities & Role Panels

EduPredict strictly isolates four role-based dashboard panels:

1. **Admin Panel (`/admin-panel/`)**
   - User lifecycle management with role protection and self-deactivation guards.
   - Course catalog, capacity limits, and instructor assignments.
   - Comprehensive system activity audit logs with actor attribution and manual notes.
   - Dynamic portal settings (risk thresholds, minimum attendance rules).
   - Full-database backup exports in JSON and CSV formats.

2. **Teacher Panel (`/teacher-panel/`)**
   - Real-time student roster with search, filter, and 5-row pagination.
   - Frictionless inline marks and attendance updates.
   - Instant student risk notifications and alert history.
   - Official academic class roster PDF export with sign-off blocks.

3. **Student Panel (`/student-panel/`)**
   - Personal academic performance dashboard, subject comparisons, and batch standing.
   - Dynamic attendance recovery tips and ML advice.
   - Notification and risk alert center with unread badge tracking.
   - Official academic report card and transcript PDF export.

4. **Analyst Panel (`/analyst-panel/`)**
   - Predictive ML engine for dropout risk classification, GPA regression, and anomaly detection.
   - Leakage-free model evaluation suite (accuracy, ROC-AUC, PR-AUC, F1 score).
   - Dataset ingestion pipeline with automated type casting and cleaning.

---

## Technology Stack

- **Backend**: Python 3.12+, Django 6.1 (Model-View-Template)
- **Database**: MongoDB Atlas (`pymongo` connection pooling)
- **Frontend**: Tailwind CSS, Vanilla JavaScript (zero framework bloat), FontAwesome 6
- **Data Visualization**: Chart.js v4+ (theme-synchronized)
- **Reporting**: ReportLab 5.1 (vector PDF generation)
- **Static Asset Serving**: WhiteNoise 6.12 (compressed manifest storage)
- **Production Server**: Gunicorn 27 WSGI server
- **CI/CD**: GitHub Actions automated linting, test suite, and UAT runner

---

## Local Development Setup

### 1. Prerequisites
- Python 3.12+
- Node.js 20+ (for JavaScript syntax validation)
- MongoDB Atlas cluster URI or local MongoDB instance

### 2. Environment Configuration
Create a `.env` file in the project root:

```env
SECRET_KEY=your-secure-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=edupredict_db
MONGODB_MAX_POOL_SIZE=50
MONGODB_MIN_POOL_SIZE=2
SENTRY_DSN=https://public@sentry.example.com/1
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### 3. Installation
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Database Seeding & Startup
```bash
python manage.py check
python manage.py runserver
```
Visit `http://localhost:8000/` in your browser.

---

## Docker Container Deployment

Deploy the entire application inside a multi-stage production container with a non-root user:

```bash
docker compose up --build -d
```

Check container health:
```bash
docker compose ps
curl http://localhost:8000/health/
```

---

## Automated Verification & Testing

### 1. Unit & Integration Test Suite (67 Tests)
```bash
python manage.py test
```

### 2. End-to-End Multi-Role UAT Simulator (7/7 Checks)
Simulates Health, Auth/RBAC, Admin self-lock, Teacher marks & PDF roster, Analyst ML, Student overview & PDF report card, and Support workflow:
```bash
python manage.py verify_uat
```

### 3. Real-Time System Health Endpoint
```bash
curl http://localhost:8000/health/
```
Returns:
```json
{
  "status": "healthy",
  "database": "connected",
  "latency_ms": 520.0,
  "counts": {
    "users": 15,
    "student_records": 120,
    "predictions": 120,
    "courses": 12
  }
}
```

### 4. Automated Database Backup Command
Export full database state into JSON or CSV for offsite backup or cron scheduling:
```bash
python manage.py export_backup --format json --output-dir backups/
python manage.py export_backup --format csv --output-dir backups/ --quiet
```

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
