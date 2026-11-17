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
last_updated_by_agent: "Analyst Cache, ML Evaluation & Navigation Integrator"
active_branch_merged_to_main: "feature/ml-evaluation -> main"
project_phase: "Phase 7 & ML Evaluation Tasks 1-3 Complete"

completed_modules:
  - "Phase 1-5: Core Shell, Auth/RBAC, Admin/Teacher Panels & Rule 20 Sidebar Isolation"
  - "Phase 6 & 7: Student Panel (Dashboard, Report Card, Study Tips, Alerts & Support), Teacher Risk Alerts & Analyst Model Health"
  - "ML Evaluation Tasks 1-3 (analytics/preprocessing.py, analytics/evaluation.py, analytics/ml_engine.py, analytics/data_pipeline.py, analytics/views.py, panels/views_analyst.py, templates/panels/analyst_evaluation_section.html, static/js/analyst_evaluation.js, analytics/tests.py, panels/tests.py):"
      - "Leakage-free sklearn Pipelines (MedianFallbackImputer + StandardScaler) and train/test split evaluation for Dropout Classifier and GPA Regressor."
      - "Integrated ML Performance & Validation section into analyst_dashboard.html with shared 'analyst:evaluation:default' TTL caching, ?refresh=1 support, and AI Accuracy sidebar navigation."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py test analytics panels --verbosity=2: 19/19 tests PASSED."
  - "Zero comments and <= 350-400 line caps verified across all modified files."

active_routes_and_files:
  - "/analyst-panel/ -> panels:analyst_dashboard (includes #ml-evaluation-section)"
  - "/analyst-panel/evaluation/ -> analytics:model_evaluation (cached default + custom params + refresh=1)"
  - "/analyst-panel/accuracy/ -> panels:analyst_accuracy"
  - "/teacher-panel/alerts/ -> panels:teacher_alerts"
  - "/student-panel/* -> panels:student_dashboard, student_report, student_tips, student_notifications"

pending_modules_in_order:
  - "Phase 8 (optional hardening): Admin Activity Logs & Settings pages"

important_notes_for_next_agent:
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys and invalidate_cache on mutations."
  - "Always track .env and .agents/* in Git."
```