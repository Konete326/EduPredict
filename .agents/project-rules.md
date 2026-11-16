# Mandatory Agent Rules & Execution Protocol (`project-rules.md`)

> **CRITICAL DIRECTIVE FOR ALL AI AGENTS (Antigravity, Claude, Claude Code, Cursor):**
> You MUST read `.agents/PRD.md`, `.agents/SRD.md`, `.agents/TRD.md`, `.agents/design.md`, `.agents/project-rules.md`, and `.agents/git-sync.md` BEFORE writing or editing a single line of code.

## Rule 1: Technology Stack Lock & Latest Packages Rule (MERN Strictly Prohibited)
- This project is built **100% on Python Django + MongoDB Atlas + Tailwind CSS + Vanilla JS**.
- **REJECT ALL MERN ARTIFACTS:** Never create `package.json` for React/Vite, `.jsx`, `.tsx`, TypeScript files, or Node/Express servers.
- Use standard Django templates (`templates/`), modular Django views, and global static assets (`static/css/global.css`, `static/js/app.js`).
- **Always Install Latest Packages Rule:** Whenever any Python package, library, or dependency is installed or updated, the **latest stable version** MUST be installed (`pip install --upgrade <package>`) and frozen into `requirements.txt`.

## Rule 2: Active Superpower & Native Tool Usage
- Regardless of how short or simple the user's prompt is (e.g., "add student page"), you MUST use all your native agent superpowers: codebase search, file inspection, terminal test execution (`python manage.py check`), and systematic verification before finishing.
- Ensure any clutter or unauthorized skills (such as `'Ponytail Skill'`) are removed if present, and strictly enforce the rules in this `.agents/` directory.

## Rule 3: Strict One-Feature-At-A-Time Execution Lock (MANDATORY)
- **NEVER build the entire project in one go**, even if the user forces you or says "build the whole project now" or "implement all features."
- Building everything at once causes broken overlays, disconnected routes, and bugs.
- **Execution Cap:** Implement **ONLY ONE feature or panel module** per turn (e.g., Phase 1: Base Shell & Auth, Phase 2: Analyst Data Ingestion & ML, Phase 3: Admin Panel, Phase 4: Teacher Panel, Phase 5: Student Panel).
- After completing and testing that single feature, update `.agents/git-sync.md`, push to GitHub, and **STOP**. Ask the user in Roman Urdu:
  *"Yeh feature mukammal aur test ho gaya hai. Kya main ab agla feature [Next Feature Name] start karun?"*

## Rule 4: Zero Comments in Code
- **All generated Python, HTML, CSS, and JavaScript code must contain ZERO comments** (No `# comment`, `<!-- comment -->`, or `/* comment */`). Write self-explanatory variable and function names instead.

## Rule 5: Global Components & File Size Discipline
- **Maximum File Length:** No Python file or HTML template may exceed **350–400 lines**. Split large views into modular files (`views_admin.py`, `views_teacher.py`, `views_student.py`, `views_analyst.py`).
- **Global Reuse Only:** Never duplicate modal HTML, KPI card markup, or CSS styles inside individual pages. Always `{% include %}` from `templates/components/` and use CSS variables from `static/css/global.css`.

## Rule 6: Light & Dark Mode Completeness
- Every button, input, dropdown, table cell, badge, chart, and modal backdrop MUST use the global theme tokens (`var(--bg-surface)`, `var(--text-primary)`, `var(--border-subtle)`) defined in `design.md`.
- Never hardcode `bg-white` or `text-black` without its corresponding dark-mode variable, ensuring zero unreadable text or broken overlays in either theme.

## Rule 7: Icons, Charts & Modals Standard
- **Icons:** Use FontAwesome classes (`fa-solid fa-...`) loaded globally. Never use AI-generated SVGs or Gemini/sparkle logos.
- **Charts:** Use Chart.js via CDN with dynamic colors that adapt when the theme toggle is clicked.
- **Modals:** Never use browser `alert()` or `confirm()`. Always trigger the global `confirm_modal.html` or `toast.html`.

## Rule 8: Dynamic MongoDB Atlas Data (No Dummy Placeholders)
- Every table, KPI counter, and chart must query real data from MongoDB Atlas (`core/db.py`). Provide a clean management command or 1-click seed/upload dataset utility so the database has realistic educational records to process.

## Rule 9: Communication Language & Post-Task Suggestions
- **Roman Urdu Mandatory:** Always communicate with the user strictly in **Roman Urdu**.
- **2 Actionable Suggestions After Every Task:** At the end of every completed task, provide **2 concise improvements** for existing code:
  - *Problem 1:* [Short description of an existing bottleneck/issue] -> *Hal:* [1-line actionable fix]
  - *Problem 2:* [Short description of an existing UI/code issue] -> *Hal:* [1-line actionable fix]

## Rule 10: `.env` & Full Project Auto-Sync Rule (MANDATORY)
- `.env` and ALL project files (code, `templates/`, `static/`, `requirements.txt`, `.env.example`, `.gitignore`, `.agents/*`) MUST always be tracked, committed, and auto-synced/pushed to GitHub whenever any change occurs.
- ONLY installed library/virtual-environment folders and local caches (`.venv/`, `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`, `db.sqlite3`) remain ignored in `.gitignore`.

## Rule 11: Full-Width Responsive Panel Layout — No Centered Box
- NEVER wrap dashboard content inside a centered fixed-width box (`max-w-7xl mx-auto`).
- Use the full-width fluid layout (`w-full px-3 py-4 sm:px-5 sm:py-5 lg:px-6 lg:py-6 xl:px-8 space-y-6` inside `<main class="flex-1 w-full min-w-0">`) with responsive grid splits (`grid-cols-1 sm:grid-cols-2 xl:grid-cols-4`, `grid-cols-1 xl:grid-cols-12`) so large desktop screens span full width beside the sidebar and mobile screens (`320px+`) stack cleanly with `min-w-0` and `overflow-x-auto`.