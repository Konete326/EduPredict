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
last_updated_by_agent: "Phase 89 AI Dock Popover Fix & Meta Astryx Unslop Polish"
active_branch_merged_to_main: "feature/astryx-dock-polish -> main"
project_phase: "Phase 89: Stationary Quadrant-Aware AI Dock Popover & Full Meta Astryx + unslop UI Alignment"

completed_modules:
  - "Phase 1-88: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline, Theme Studio & 21st.dev Curated Presets, Cloudinary Avatars, Real-Time Notifications, Feedback Reply CRUD, Stepper Signup, Teacher Approval/Reject Guard, Official Monochrome A4 PDFs, Cgroup Health, Rate Limits, Encrypted Backups, Multi-Agent AI Dock, Vercel Auto-Deploy, Provably Hero & Live Testimonial Globe, Single-Institute Datasets, Student-ID Auth, Teacher CSV Isolation & Credentials Export, Training vs Live Separation, Bento Grid Modals, 4-Col Minimal Lists + View Details Modal, Dedicated /admin-panel/training/ Page, Clean-Start DB Reset & Full Docs Sync."
  - "Phase 89 (AI Dock Popover Fix & Meta Astryx Design System + unslop Across All Panels):"
      - "templates/components/ai_message_dock.html, static/js/ai_agent_dock.js, templates/base.html: converted #ep-message-dock and #ep-agent-chat-panel into position:absolute popovers inside a compact toggle-sized #ep-agent-dock-root with syncDockPlacement(el) quadrant anchoring, eliminating sideways button jump when clicking dragged #ep-agent-dock-toggle; switched Tailwind sans font stack to Figtree."
      - "static/css/global.css, templates/components/{data_table,metric_card,topbar,form_modal,confirm_modal}.html: added Astryx radius tokens (--radius-inner/element/container), 14px/20px body scale, .ep-page-header hairline layout, rounded-[16px] flat cards (zero shadow-sm), rounded-[12px] controls, sentence-case table headers, and StatusDot indicators for normal states."
      - "templates/panels/{admin_*,teacher_*,student_*,analyst_*}.html (all 17 panel templates): replaced boxed card-soup headers with flat ep-page-header, removed shouty role eyebrow pills/uppercase tracked headings, kept monochrome A4 print sheet (#ep-a4-print-sheet) and 17-inch viewport-fit tabs intact."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all static/js/*.js files exited 0."
  - "Zero-comment & line-cap audit: 0 comments across all 26 modified code files; all within caps (<= 350)."
  - "manage.py test: Ran 137 tests in 72.671s (137/137 OK)."
  - "manage.py verify_uat: UAT Results 7/7 passed in 8.40s - System 100% Operational."
  - "Live Browser QA (http://127.0.0.1:8000): verified Figtree font load, dragged #ep-agent-dock-toggle click deltaX=0 / deltaY=0 with dock/chat opening inside viewport, flat ep-page-header + StatusDot tables + Bento Add Course modal across Admin pages, and cleaned MongoDB Atlas back to 1 Admin user only."

active_routes_and_files:
  - "static/css/global.css, static/js/ai_agent_dock.js, templates/base.html, templates/components/{ai_message_dock,confirm_modal,data_table,form_modal,metric_card,topbar}.html, templates/panels/{admin_courses,admin_dashboard,admin_logs,admin_settings,admin_tickets,admin_training,admin_users,analyst_accuracy,analyst_dashboard,student_dashboard,student_notifications,student_report,student_tips,teacher_alerts,teacher_dashboard,teacher_ingest,teacher_students}.html, .agents/git-sync.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables (local Windows fallback reads HKCU\\Environment)."
```