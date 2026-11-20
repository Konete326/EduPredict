# Mandatory Agent Rules & Execution Protocol (`project-rules.md`)

> **CRITICAL DIRECTIVE FOR ALL AI AGENTS (Antigravity, Claude, Claude Code, Cursor):**
> You MUST read `.agents/prd.md`, `.agents/srd.md`, `.agents/trd.md`, `.agents/design.md`, `.agents/project-rules.md`, and `.agents/git-sync.md` BEFORE writing or editing a single line of code.

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
- **Charts:** Use Chart.js via CDN (`window.createThemedChart`) with compact heights (`h-44` to `h-48`) and dynamic colors that adapt when the theme toggle is clicked.
- **Modals:** Never use browser `alert()`, `confirm()`, or `prompt()`. Always trigger the global `confirm_modal.html` (`openConfirmModal`, `openComingSoonModal`), `form_modal.html` (`openFormModal`), or `toast.html`.

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
- Use the full-width fluid layout (`w-full px-3 py-3 sm:px-5 sm:py-3.5 lg:px-6 lg:py-4 xl:px-8 space-y-4` inside `<main class="flex-1 w-full min-w-0">`) with responsive grid splits (`grid-cols-1 sm:grid-cols-2 xl:grid-cols-4`, `grid-cols-1 xl:grid-cols-12`) so large desktop screens span full width beside the sidebar and mobile screens (`320px+`) stack cleanly with `min-w-0` and zero horizontal overflow.

## Rule 12: Desktop Viewport-Fit & Mandatory 5-Row Pagination
- Design desktop dashboards and tables with compact vertical spacing (`p-4`, `gap-4`, `space-y-4`, compact hero/filter bars), compact chart heights (`h-44` to `h-48`, ~180px–200px), and **mandatory 5-row pagination** (`[data-paginated-container data-page-size="5"]` + `[data-pagination-bar]`) on all tables.
- Desktop viewports must fit cleanly without needing unnecessary vertical page scrollbars unless data/content strictly requires scrolling.

## Rule 13: Mobile Card-List Standard (`< md` / `< 768px`)
- On mobile screens (`< 768px`), NEVER force cramped multi-column tables.
- Every list/table MUST render as crisp stacked mobile cards (`md:hidden`, `[data-mobile-card][data-page-item]`) in `data_table.html` with an elevated header, wrapped key-value rows, and action footer bar while desktop (`>= md`) renders the tabular view (`hidden md:block`, `tbody tr[data-page-item]`), both synchronized inside `[data-paginated-container data-page-size="5"]`. `analyst_evaluation_section.html` renders `sm:hidden` Confusion Matrix cards (`TN`, `FP`, `FN`, `TP`) alongside the desktop matrix table.

## Rule 14: Collapsible Sidebar on Both Desktop & Mobile
- The topbar sidebar toggle (`#mobile-sidebar-toggle`) MUST be accessible on BOTH desktop and mobile (never hide it with `lg:hidden`).
- On desktop (`>= 1024px`), it collapses/expands the `w-64` sidebar (`body.sidebar-collapsed`, toggling `#mobile-sidebar-drawer` and `#app-shell-main` left padding with `localStorage` persistence under `edupredict_sidebar_collapsed` and dispatching a `resize` event for Chart.js). On mobile (`< 1024px`), it opens/closes the off-canvas drawer and backdrop.

## Rule 15: Coming Soon Modal & Sidebar `"Soon"` Badge Standard
- All planned/unbuilt panel pages across Admin, Teacher, Student, and Analyst panels MUST appear in `templates/components/sidebar.html` with a `"Soon"` badge and open the global theme-aware Coming Soon modal (`openComingSoonModal` / `[data-coming-soon]`) when clicked, instead of broken links or raw placeholders.
- Direct route views for unbuilt modules must render `templates/panels/coming_soon_panel.html` with roadmap details, live MongoDB counts, and a trigger for `openComingSoonModal`.

## Rule 16: Basic Everyday English Only & Compact Collapsible Sidebar
- **Simple Everyday English:** All UI labels, sidebar links, headings, helper text, modal copy, and toast messages across every panel MUST use plain, everyday English (no complex technical jargon). Keep action labels intuitive with crisp FontAwesome icons and descriptive `title` tooltips.
- **Compact Collapsible Sidebar & Interactive States:** Sidebar navigation labels MUST stay short and clean, and sidebar section groups (`data-nav-group-toggle`) MUST be collapsible/minimizable via dropdown toggles persisted in `localStorage` (`edupredict_nav_groups`). Keep `cursor: pointer`, crisp `:hover`/`:focus-visible`/`:active` states, `text-wrap: balance` on headings, clickable table column sorting (`data-sortable`), and mandatory 5-row pagination.

## Rule 17: Zero Dead Routes, No Duplicate Icons & Mandatory Coming Soon Modals
- **Zero Dead Links or Placeholders:** Never leave dead/unfinished links, broken routes, or buttons that lead to 404 or empty placeholders. Either build the complete dynamic route first OR attach `data-coming-soon="true"` (`openComingSoonModal`) directly to the link/button.
- **No Duplicate `+` Icons:** Never place duplicate `+` icons/symbols on buttons (for example, never pair `<i class="fa-solid fa-plus"></i>` with a literal `+ ` text prefix on the same button).
- **Custom 404 Safety Net:** Keep the custom theme-aware `404.html` error page active in both `DEBUG=True` and `DEBUG=False` for unrecognized URLs.

## Rule 18: Strict Role Logic & Self-Action Guards
- **Real-World Role Boundaries:** Admins manage users, courses, and incoming help tickets, so Admins MUST NOT see `"Send Feedback"` or `"New Ticket"` options to message themselves (`submit_support_ticket` blocks `ADMIN`).
- **Self-Action Guards:** Admins MUST NEVER be able to delete, deactivate/block, or downgrade/change the role of their own active account. Enforce checks against BOTH `user_id` AND `email` in backend services, omit self-destructive buttons on the actor's own table/card row, and pass `data-is-self="true"` so `openEditUserModal` locks the self role field as read-only (`ADMIN (Active Self Account — Protected)`).

## Rule 19: Zero-Lag Caching & SPA-Smooth Navigation
- **Process-Once Startup & TTL Caching:** Never run DB seeding, index creation (`create_index`), or password-hash checks on every page request — run startup seed, index, and default-admin guards once per process (with thread locks). Use short-TTL in-memory caching in `core/db.py` (`get_cached` / `invalidate_cache` cleared on every mutation) and cache DB health checks.
- **Cache-Busted Assets & SPA Navigation:** Cache-bust static CSS/JS assets (`?v=9`) in `templates/base.html` and `templates/accounts/auth.html`, and provide SPA-smooth page transitions (`static/js/nav.js` with `sessionStorage` GET cache + hover prefetch + `#ep-top-progress`, invalidated on form `POST`, re-initializing charts, smart automation, UI widgets, submit lock reset, and upload timer cleanup via `window.reinitEduPredictUI()`).

## Rule 20: Strict Role Navigation Isolation & Ultra-Simple Marks Ingestion
- **Strict Role Sidebar Isolation:** Never display all panels inside one role's sidebar. Each role (`ADMIN`, `TEACHER`, `STUDENT`, `ANALYST`) must strictly render ONLY its own dedicated navigation group(s) (Admin splits into `Admin Core` + `Support & Logs`) plus the shared `Settings & Theme` dropdown (`My Profile`, `Portal Settings` for `ADMIN`, `Theme & Colors`) in `templates/components/sidebar.html`. Keep topbar & sidebar footer free of duplicate Theme Studio buttons.
- **Ultra-Simple Marks & Attendance Ingestion:** Marks entry and sheet upload must be frictionless and jargon-free for teachers. The manual entry widget requires only core inputs (Student ID with datalist autocomplete & suggested next ID, Student Name, Course, Marks 0-100, Attendance % 0-100). File upload accepts standard 3-column CSV/Excel files (`student_id`, `marks`, `attendance`) with flexible column aliases (`roll_no`, `score`, `att`), sample CSV template download (`?template=csv`), and a 1.2s cancelable auto-upload grace window.

## Rule 21: Theme Studio, My Profile, Password Toggles & Cancelable Automation
- **Theme & Appearance Live Studio (`/theme/preferences/`):** Per-user & per-panel theme preferences (`ep_theme_prefs:<user_id>:<role>` + MongoDB `users.theme_prefs.<ROLE>`) support Light/OLED Dark modes, 6 Header/Sidebar Chrome Themes, 13 Accent Swatches, 6 Surface Presets, Comfortable/Compact density, and guest `PORTAL` login sync (`sync_theme_prefs_on_login`). Keep `get_user_theme_prefs` strictly session-only on GET and keep the sidebar fixed on the left (no LTR/RTL flip).
- **My Profile (`/profile/`) & Universal Password Toggles:** Every logged-in role accesses `My Profile & Settings` (`/profile/`) with read-only protected role, optional `Department`/`Batch`/`Phone`/`Bio`, and optional password update. Every password field across `/auth/`, `/profile/`, and global `form_modal.html` (`createFieldNode` + `[data-password-toggle]`) must include a Show/Hide eye toggle button.
- **1.2s Cancelable Auto-Upload & Baseline:** `static/js/theme_studio.js` (`bindSmartFileUploads()`) provides a 1200ms cancelable toast grace window (`window.eduPredictCancelUpload` cleared on SPA swap) for `input[type="file"][data-auto-submit="true"]`. Core Phases 1–21 established the 4 panels, Theme Studio, My Profile, Password Toggles, and Automation.

## Rule 22: Ocean Blue Default, Cloudinary Media, Loading Guards & UI Widgets
- **Ocean Blue Default & Clean Topbar:** Default theme is `shell_theme="blue"`, `accent="ocean"` (`#2563eb` light / `#3b82f6` dark) with Ocean Blue graduation-cap SVG favicons in `base.html` and `auth.html`. Keep topbar clean without `"Atlas Ready / Offline"` status pills; render `current_user.avatar_url` image (or initials fallback) in topbar & sidebar footer.
- **Cloudinary Media Policy:** Store `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` in tracked `.env` (empty placeholders in `.env.example`), keep `cloudinary` in `requirements.txt`, validate (`<= 5 MB` image) & upload `320x320` face-cropped avatars via `core/cloudinary_services.py`, and persist only URLs in MongoDB Atlas `users.avatar_url`.
- **Global Button Loading Lock & `#ep-top-progress`:** `static/js/ui_widgets.js` drives `#ep-top-progress` (`window.EduPredictProgress`) on SPA swaps and valid form submissions, prevents duplicate submits, displays `"Processing..."` spinner + `aria-busy="true"` (12s fallback + `pageshow` reset via `resetEduPredictSubmitLocks`), and skips `[data-no-lock]`, `[data-no-loading]`, and file download forms.
- **Zero Horizontal Scrollbar & Change Password Modal:** Enforce `html, body { overflow-x: clip; }` in `static/css/global.css` and wrap `data_table.html` body cells (`break-words max-w-[18rem]`, keeping `whitespace-nowrap` strictly for pills/actions). Never place inline optional password inputs on the `/profile/` form — use `"Change Password"` -> `openChangePasswordModal()` (`form_modal.html` posting `action="change_password"`).
- **Reusable Widgets & Completed Phases:** Use `templates/components/gradient_file_uploader.html` (`[data-gradient-uploader]`) and `templates/components/faq_pro.html` (`[data-faq-pro]` with safe DOM `<mark>` highlighting). Phases 1–59 (all 4 panels, Theme Studio, Real-Time Notifications, Feedback Reply CRUD, Card-Grid Directories, Modalized Uploads, Stepper Signup Wizard, Teacher Approval Guard, Official PDF Transcript, and Encrypted/Checksummed Ops Tooling) are complete.

## Rule 23: Enterprise Standard, Zero-Click Automation & Aptech Viva Readiness (Phases 60–63)
- **Less Clutter, Higher Quality (Phase 60):** Keep Theme Studio inside Admin Portal Settings only (Ocean Blue + Light/Dark toggle for other roles); use an instant 3-bullet Page Guide popover instead of slow typewriter animations; default User & Student directories to a clean 5-column Compact Table with a `[Table | Cards]` toggle; keep KPI cards clean (bold tabular number + trend pill, no synthetic dot-matrix noise).
- **Zero-Click Automation & Dynamic PDF Branding (Phase 61):** Auto-trigger fast ML predictions (`Ridge`, `RandomForest(n_estimators=50, n_jobs=-1)`, `IsolationForest`) on every marks update or CSV upload with automatic high-risk Student tips & Teacher alerts; support Smart CSV Column Auto-Mapper (`Roll_No`, `Enrollment`, `Attendance`, `Marks` aliases); add 1-click `"Notify All High-Risk Students"` on Teacher Alerts; refresh notifications immediately on `visibilitychange`; inject live `institution_name` and `current_term` from `get_portal_settings()` into PDF transcripts.
- **Student 360° Drawer & Teacher Rejection Flow (Phase 62):** Provide a right-side Student 360° Slide-Over Drawer (`GET /students/<student_id>/summary/`) in Teacher & Analyst views, plus Admin `"Reject with Reason"` (`REJECT_USER` audit + rejection reason + re-apply guidance) for pending Teachers.
- **Live LMS Stream Simulator & Aptech Deliverables (Phase 63):** Provide Analyst `"Simulate Live LMS Stream"` (`POST /analyst-panel/stream-tick/`, 5s interval with live anomaly detection) and maintain the Aptech Final Submission Pack (`docs/aptech_submission/`: Project Report with Flowcharts/DFDs, Test CSV Dataset, Installation ReadMe, Demo Walkthrough).