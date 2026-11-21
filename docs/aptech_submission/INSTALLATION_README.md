# EduPredict — Installation & Setup Guide

Follow this step-by-step guide to install, configure, verify, and run **EduPredict** locally or for an academic evaluation demo.

---

## 1. Prerequisites

- **Python:** 3.11 or 3.12+
- **Database:** MongoDB Atlas cluster connection URI (or local MongoDB instance)
- **Node.js:** Optional (18+ recommended to run `node --check` syntax verification on frontend scripts)
- **Git:** Installed to clone the repository

---

## 2. Clone & Virtual Environment Setup

Clone the repository and navigate into the project root:

```bash
git clone https://github.com/Konete326/EduPredict.git
cd EduPredict
```

Create and activate a Python virtual environment (`.venv`):

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

Upgrade `pip` and install all pinned packages from `requirements.txt` (Django `6.1.3`, `pymongo 4.20.0`, `pandas 3.1.1`, `numpy 2.5.5`, `scikit-learn 1.9.1`, `openpyxl 3.1.5`, `reportlab 5.1.0`, `cloudinary 1.47.0`, `cryptography 50.0.2`, `whitenoise 6.12.0`, `gunicorn 27.0.1`):

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt
```

---

## 4. Environment Configuration (`.env`)

Copy `.env.example` to `.env` in the project root and populate the required values:

| Variable | Required | Purpose |
| :--- | :--- | :--- |
| `SECRET_KEY` | Yes | Django cryptographic signing secret |
| `DEBUG` | Yes | `True` for local development, `False` for production |
| `MONGODB_URI` | Yes | MongoDB Atlas SRV URI (`mongodb+srv://...`) |
| `MONGODB_DB_NAME` | Yes | Database name (default: `edupredict_db`) |
| `ADMIN_EMAIL` | Yes | Default Admin account email (e.g. `admin@gmail.com`) |
| `ADMIN_PASSWORD` | Yes | Default Admin password |
| `ADMIN_FULL_NAME` | Yes | Display name for seeded Admin user |
| `CLOUDINARY_CLOUD_NAME` | Optional | Cloudinary cloud name for avatar & ticket screenshot hosting |
| `CLOUDINARY_API_KEY` | Optional | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Optional | Cloudinary API secret |
| `BACKUP_ENCRYPTION_KEY` | Optional | Fernet key for `--encrypt` / `decrypt_backup` operations |
| `SENTRY_DSN` | Optional | Sentry error monitoring DSN |

---

## 5. Database Migration, System Check & Run Server

Initialize the lightweight SQLite session table and verify Django configuration:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.
Check live database latency and memory health at [http://127.0.0.1:8000/health/](http://127.0.0.1:8000/health/).

---

## 6. Automated Testing, UAT & JS Verification

Run the complete automated verification suite before any demonstration:

1. **Django Unit & Integration Test Suite:**

```powershell
.\.venv\Scripts\python.exe manage.py test
```

2. **End-to-End Multi-Role User Acceptance Test (7-Step Live UAT):**

```powershell
.\.venv\Scripts\python.exe manage.py verify_uat
```

3. **JavaScript Syntax Verification (All 11 Scripts):**

```powershell
Get-ChildItem static\js\*.js | ForEach-Object { node --check $_.FullName }
```

---

## 7. Backup & Recovery Commands

Create a SHA-256 checksummed MongoDB backup, verify integrity, or encrypt/decrypt backups:

```powershell
.\.venv\Scripts\python.exe manage.py export_backup --format json --output-dir backups/
.\.venv\Scripts\python.exe manage.py verify_backup backups/<backup_file>.json
```

With `BACKUP_ENCRYPTION_KEY` set in `.env`:

```powershell
.\.venv\Scripts\python.exe manage.py export_backup --format json --output-dir backups/ --encrypt
.\.venv\Scripts\python.exe manage.py decrypt_backup backups/<backup_file>.json.enc
```
