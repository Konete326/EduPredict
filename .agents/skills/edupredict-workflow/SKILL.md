---
name: edupredict-workflow
description: >-
  Standard operating workflow for EduPredict tasks. Use whenever starting,
  implementing, verifying, or handing over any EduPredict Django feature,
  panel module, UI update, or GitHub sync.
---

# EduPredict End-to-End Agent Workflow

Follow this exact sequence for every EduPredict feature, fix, or panel phase.

## 1. Mandatory Pre-Flight Reading

Before inspecting code or editing files, read all six project specification documents:

1. [prd.md](../../prd.md) — Product scope, role capabilities, anti-bloat lock
2. [srd.md](../../srd.md) — Architecture, RBAC, data pipeline, ML & NFR specs
3. [trd.md](../../trd.md) — Stack, directory layout, MongoDB schemas, URL map, component contracts
4. [design.md](../../design.md) — Theme tokens, app-shell-3, z-index stack, viewport-fit & mobile card-list rules
5. [project-rules.md](../../project-rules.md) — All 15 mandatory engineering, UI/UX, and communication rules
6. [git-sync.md](../../git-sync.md) — Git automation, module isolation, and Section 4 Active Handover State

## 2. Pre-Task Git Routine

Before writing or editing any code, sync with `main` and create/switch to a dedicated feature branch:

```bash
git checkout main
git pull origin main
git checkout -B feature/<module-name>
git merge main
```

Use role/module branch names such as `feature/core-shell`, `feature/auth-rbac`, `feature/analyst-ml`, `feature/admin-panel`, `feature/teacher-panel`, or `feature/student-panel`.

## 3. Module Isolation & Scope Lock

- **One Feature Per Execution:** Implement ONLY the single requested feature or panel module. Never build the entire project in one turn.
- **Panel Ownership Boundaries** (per [git-sync.md](../../git-sync.md) Section 3):
  - **Admin Panel:** `panels/views_admin.py`, `panels/admin_services.py`, `templates/panels/admin_*.html`
  - **Teacher Panel:** `panels/views_teacher.py`, `templates/panels/teacher_*.html`
  - **Student Panel:** `panels/views_student.py`, `templates/panels/student_*.html`
  - **Analyst & ML:** `panels/views_analyst.py`, `analytics/*`, `templates/panels/analyst_*.html`
- **Protect Shared Contracts:** Do not break `templates/base.html` block names (`{% block content %}`, `{% block extra_js %}`), `templates/components/*`, `static/css/global.css` tokens, or `core/db.py` helpers.

## 4. Implementation Guardrails

Verify every rule below while coding (see [project-rules.md](../../project-rules.md) and [design.md](../../design.md)):

- **Stack Lock:** Pure Python 3.11+ Django (MVT) + MongoDB Atlas (`pymongo`) + Tailwind CSS + Vanilla JS (`static/js/app.js`, `charts.js`). Zero React/MERN/TSX/JSX.
- **Latest Packages:** If installing/updating dependencies, run `pip install --upgrade <package>` and update `requirements.txt`.
- **Zero Comments:** ZERO comments in `.py`, `.html`, `.css`, and `.js` files (no `#`, `<!-- -->`, `/* */`, `//`).
- **File Size Discipline:** Keep every file `<= 350–400` lines (`<= 250` lines for panel view files; move DB/ML logic to service modules).
- **Theme & Z-Index Parity:** Use CSS variables from `static/css/global.css` for Light/Dark mode parity; follow `z-10`..`z-60` hierarchy; no native `alert()`/`confirm()`/`prompt()` (use `openConfirmModal`, `openFormModal`, `openComingSoonModal`, `toast.html`).
- **Full-Width Fluid Layout:** Never wrap panels in `max-w-7xl mx-auto`. Use `<main class="flex-1 w-full min-w-0">` with responsive grids (`grid-cols-1 sm:grid-cols-2 xl:grid-cols-4`, `xl:grid-cols-12`, `min-w-0`).
- **Desktop Viewport-Fit & 5-Row Pagination:** Use compact vertical spacing (`p-4`, `gap-4`, `space-y-4`), compact chart heights (`h-44` to `h-48`), and `[data-paginated-container data-page-size="5"]` + `[data-pagination-bar]` so desktop views avoid unnecessary vertical scrollbars.
- **Mobile Card-Lists (`< md`):** Every list/table renders BOTH desktop `hidden md:block` table rows (`tbody tr[data-page-item]`) AND mobile `md:hidden` stacked cards (`[data-mobile-card][data-page-item]`) inside the same paginated container, synced with `input[data-table-search]`.
- **Collapsible Sidebar & Coming Soon:** Keep `#mobile-sidebar-toggle` functional on both desktop (`body.sidebar-collapsed` + `localStorage`) and mobile drawer; mark unbuilt sidebar items with `"Soon"` badges + `data-coming-soon="true"` (`openComingSoonModal`).
- **Live MongoDB Atlas Data:** Query real collections via `core/db.py`; never ship dummy static data or hardcoded secrets (`.env` only).

## 5. Verification Checklist

Run and confirm every check after your final edit:

1. Run Django system check:
   ```bash
   python manage.py check
   ```
   (On Windows with project venv: `.\.venv\Scripts\python.exe manage.py check`)
2. Confirm zero comments in every modified/created `.py`, `.html`, `.css`, and `.js` file.
3. Confirm line counts stay within `<= 350–400` lines (`<= 250` lines for view files).
4. Confirm Light & Dark mode tokens, desktop viewport-fit (5-row pagination, `h-44`/`h-48` charts), mobile card-lists (`md:hidden`), collapsible sidebar, and named `{% url %}` routes work cleanly.
5. Confirm `.env` and `.agents/*` are NOT ignored in `.gitignore`.

## 6. Post-Task `git-sync.md` Rewrite & Git Auto-Sync

1. **Rewrite Section 4 of [git-sync.md](../../git-sync.md):** Clear outdated handover notes from the previous phase and write a crisp YAML summary covering `last_updated_by_agent`, `active_branch_merged_to_main`, `project_phase`, `completed_modules`, `active_routes_and_files`, `pending_modules_in_order`, and `important_notes_for_next_agent`.
2. **Commit, Merge to `main`, and Push Both Branches (including `.env` and `.agents/*`):**
   ```bash
   git add .
   git commit -m "feat(<module>): implement and verify <feature-name>"
   git push -u origin feature/<module-name>
   git checkout main
   git pull origin main
   git merge feature/<module-name>
   git push origin main
   ```

## 7. Handover Response to User (Roman Urdu)

Respond strictly in **Roman Urdu**:
1. Confirm the feature is completed, verified (`manage.py check`), and synced to GitHub.
2. Provide **2 concise actionable improvements** for existing code:
   - *Problem 1:* [Short bottleneck/issue] -> *Hal:* [1-line actionable fix]
   - *Problem 2:* [Short UI/code issue] -> *Hal:* [1-line actionable fix]
3. Stop and ask:
   *"Yeh feature mukammal aur test ho gaya hai. Kya main ab agla feature [Next Feature Name] start karun?"*
