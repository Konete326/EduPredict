# Automated GitHub Sync & Multi-Agent Handover (`git-sync.md`)

> **CRITICAL NOTICE FOR AI AGENTS:**
> The human users giving you tasks **DO NOT know Git or GitHub commands**. You (the AI Agent) are 100% responsible for managing branches, pulling updates, resolving conflicts, updating this handover log, committing, and pushing to GitHub automatically before and after every single task.

---

## 1. Mandatory Pre-Task Git Routine (Run BEFORE Touching Any Code)
Whenever a user asks you to build or fix anything, execute these exact steps silently in the terminal first:

1. **Read `.agents/git-sync.md` (Section 4 below)** to see what the previous agent completed and which files were modified.
2. **Fetch & Pull Latest Main:**
   ```bash
   git checkout main
   git pull origin main
   ```
3. **Create or Switch to Role/Feature Dedicated Branch:**
   Work in a dedicated branch for the specific module being built so team members never clash (e.g., `feature/core-shell`, `feature/auth-rbac`, `feature/analyst-ml`, `feature/admin-panel`, `feature/teacher-panel`, `feature/student-panel`).
   ```bash
   git checkout -B feature/<module-name>
   git merge main
   ```

## 2. Mandatory Post-Task Git Routine & `.env` Auto-Sync Rule (Run AFTER Testing the Feature)
- **`.env` & Full Project Auto-Sync Rule (MANDATORY):** `.env` and ALL project files (code, `templates/`, `static/`, `requirements.txt`, `.env.example`, `.gitignore`, `.agents/*`) MUST always be tracked, committed, and auto-synced/pushed to GitHub whenever any change occurs.
- **`.gitignore` Scope Lock:** ONLY installed library/venv folders and local caches (`.venv/`, `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`, `db.sqlite3`) remain ignored in `.gitignore`. Never ignore `.env`.

Once you finish implementing the single requested feature:

1. **Verify Zero Errors:**
   ```bash
   python manage.py check
   ```
2. **Rewrite Section 4 (Active Handover State) of this file (`.agents/git-sync.md`):**
   - REMOVE/CLEAR the outdated handover notes from the previous agent so this file stays short, clean, and current.
   - Write a crisp summary of what is now completed, what routes/collections were updated, and what the next agent should know.
3. **Commit, Merge to `main`, and Push Both Branches (including `.env` and `.agents/*`):**
   ```bash
   git add .
   git commit -m "feat(<module>): implement and verify <feature-name>"
   git push -u origin feature/<module-name>
   git checkout main
   git pull origin main
   git merge feature/<module-name>
   git push origin main
   ```
4. Inform the user in Roman Urdu that their feature is live and synced on GitHub.

3. Multi-Developer Isolation Rules
Never Break Global Contracts: templates/base.html, templates/components/*, static/css/global.css, and core/db.py are shared across all panels. Only add backwards-compatible keys; never rename existing template block names ({% block content %}, {% block extra_js %}).

Panel Isolation:

Person working on Student Panel edits panels/views_student.py and templates/panels/student_*.html.

Person working on Teacher Panel edits panels/views_teacher.py and templates/panels/teacher_*.html.

Person working on Admin Panel edits panels/views_admin.py and templates/panels/admin_*.html.

Person working on Analyst & ML edits panels/views_analyst.py, analytics/*, and templates/panels/analyst_*.html.

## 4. Active Handover State (Agents: Replace This Block on Every Push)
```yaml
last_updated_by_agent: "Coordinator & Senior Full-Stack Architect (@coordinator)"
active_branch_merged_to_main: "feature/auth-rbac -> main"
project_phase: "Live Prediction Count Badge & Caps-Lock Warning Implemented & Verified on Split Login (auth.html)"

completed_modules:
  - "Phase 1: Django Project Init, Core MongoDB Layer & App-Shell-3 Layout (core/, templates/components/, static/)"
  - "Phase 2: Authentication, Default Admin Sync & Role-Based Routing (accounts/services.py, accounts/views.py, templates/accounts/auth.html)"
  - "Phase 3: Analyst Panel, ML Engine, chunked CSV ingestion, anomaly detection & full-width dashboard"
  - "Phase 4 & 5: Admin Panel (CRUD, 5-row pagination, mobile cards, backups), Teacher Panel, Zero-Lag Caching & SPA Navigation"
  - "Rule 20: Strict Role Navigation Isolation & Ultra-Simple Marks Ingestion verified and merged"
  - "Astryx Integration & Split-Login Template (templates/accounts/auth.html):"
      - "Executed npx @astryxdesign/cli init --features agents generating AGENTS.md and GEMINI.md reference files."
      - "Evaluated Astryx tokens, themes (Neutral, Butter, Chocolate, Gothic, Matcha, Stone, Y2K), and component patterns."
      - "Redesigned auth.html using Astryx's login-split template: left column features brand showcase, ML highlights, and live MongoDB status; right column hosts clean sign-in and account registration forms with password eye toggles and 1-click default admin button."
  - "Actionable Improvements (auth.html & accounts/views.py):"
      - "Problem 1 Fixed: In accounts/views.py, added _get_live_stats() with short-TTL caching (get_cached) to read live predictions document count from MongoDB predictions_col(). Displayed dynamic '{{ live_predictions_count }}+ Active Predictions' badge in the split login showcase pane."
      - "Problem 2 Fixed: Attached lightweight keyup/keydown Caps-Lock listener (initCapsLockListeners) to both login and registration password fields. Warns user with a subtle amber 'Caps' pill icon whenever Caps Lock is active, preventing accidental authentication failures."

verification_results:
  - "manage.py check: 0 issues reported."
  - "Auth view check: GET /auth/ renders live predictions badge and caps lock warning targets with HTTP 200."
  - "File limits & zero comments: auth.html is 310 lines (< 350 cap) and accounts/views.py is 176 lines with 0 comments."

active_routes_and_files:
  - "/auth/ -> accounts:auth_view (Astryx login-split layout with live prediction count & Caps-Lock warning)"
  - "/admin-panel/* -> panels:views_admin.py (Admin only sees Admin sidebar)"
  - "/teacher-panel/* -> panels:views_teacher.py (Teacher only sees Teacher sidebar)"
  - "/student-panel/* -> panels:views_student.py (Student only sees Student sidebar)"
  - "/analyst-panel/* -> panels:views_analyst.py (Analyst only sees Analyst sidebar)"

pending_modules_in_order:
  - "Phase 6: Student Panel Full Implementation (Personal Dashboard, AI Risk Card, Report Download, Study Recommendations)"

important_notes_for_next_agent:
  - "Next Phase: Build the dedicated Student Panel in panels/views_student.py and templates/panels/student_*.html."
  - "Keep role navigation strictly isolated across all panels per Rule 20."
  - "Preserve zero-lag caching (core/db.py get_cached/invalidate_cache), 5-row pagination, mobile cards, and zero comments policy."
  - "Always track .env and .agents/* in Git."
```