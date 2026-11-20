---
trigger: always_on
description: Mandatory EduPredict project rules, stack lock, UI/DB contracts, viewport-fit pagination, mobile card-lists, simple English, role guards, caching/SPA nav, and Roman Urdu invariants.
---

# EduPredict Always-On Engineering & UI/UX Rules

> **Pre-Flight Mandate (Every Task):** Before writing or editing ANY code on any task, read `.agents/prd.md`, `.agents/srd.md`, `.agents/trd.md`, `.agents/design.md`, `.agents/project-rules.md`, and `.agents/git-sync.md` (especially Section 4 Active Handover State), follow `.agents/skills/edupredict-workflow/SKILL.md`, and execute the mandatory pre-task/post-task Git pull/push routine in `.agents/git-sync.md`.

## 1. Technology Stack Lock & Latest Packages Policy
- **Pure Django Only (MERN Strictly Prohibited):** Built 100% on Python 3.11+ Django (MVT) + MongoDB Atlas (`pymongo`, `core/db.py`) + Tailwind CSS + Vanilla JS (`static/js/app.js`, `static/js/charts.js`) + FontAwesome + Chart.js v4+.
- **Reject MERN Artifacts:** Never create React, Vite, Next.js, `.jsx`, `.tsx`, TypeScript files, React `package.json`, or Node/Express servers.
- **Latest Stable Packages:** Whenever installing or updating any Python dependency, always install the latest stable release (`pip install --upgrade <package>`) and freeze into `requirements.txt`.

## 2. Active Tooling & Environment Hygiene
- Use native search, file inspection, `python manage.py check`, `python manage.py test`, and full `.agents/skills/edupredict-workflow/SKILL.md` verification before finishing any task, regardless of how brief the user prompt is.
- Keep `.agents/` clean of unauthorized or unrelated skills/clutter (such as `'Ponytail Skill'`).

## 3. Strict One-Feature-At-A-Time Execution Lock (MANDATORY)
- **Never build the entire project in one go**, even if explicitly asked to build everything at once.
- **Execution Cap:** Implement **ONLY ONE feature or panel module** per turn (e.g., Core Shell/Auth, Analyst Data & ML, Admin Panel, Teacher Panel, Student Panel).
- After verifying that single feature, update `.agents/git-sync.md` Section 4, auto-sync/push to GitHub, and **STOP**, asking the user in Roman Urdu:
  *"Yeh feature mukammal aur test ho gaya hai. Kya main ab agla feature [Next Feature Name] start karun?"*

## 4. Zero Comments in Code
- All generated or edited Python (`.py`), HTML (`.html`), CSS (`.css`), and JavaScript (`.js`) files MUST contain **ZERO comments** (no `# ...`, no `<!-- ... -->`, no `/* ... */`, no `// ...`). Write clean, self-explanatory identifiers instead.

## 5. Global Components, Module Isolation & File Size Cap
- **File Length Cap:** No Python, HTML, CSS, or JS file may exceed **350–400 lines** (keep panel view modules `<= 250` lines by extracting DB/CRUD/ML logic into service modules like `panels/admin_services.py` or `analytics/`).
- **Global Reuse Only:** Never duplicate modal HTML, KPI cards, table wrappers, or CSS inside individual pages. Always `{% include %}` from `templates/components/` (`sidebar.html`, `topbar.html`, `metric_card.html`, `confirm_modal.html`, `form_modal.html`, `data_table.html`, `toast.html`).
- **Contract Safety:** Never break shared `templates/base.html` block names (`{% block content %}`, `{% block extra_js %}`), `core/db.py`, or existing component APIs. Always use `{% url 'route_name' %}` instead of hardcoded URLs.

## 6. Light & Dark Mode Completeness, Tokens & Z-Index Stack
- Every surface, button, input, table cell, badge, chart, dropdown, and modal backdrop MUST use CSS variables from `static/css/global.css` (`--bg-canvas`, `--bg-surface`, `--bg-elevated`, `--bg-overlay`, `--text-primary`, `--text-secondary`, `--text-muted`, `--border-subtle`, `--accent-primary`, `--accent-hover`, `--accent-soft`, `--status-success`, `--status-warning`, `--status-danger`). Never hardcode `bg-white` or `text-black` without dark-mode token parity.
- **Anti-AI-Slop Mandate:** No neon purple-to-cyan gradients, no glowing sci-fi borders, and no oversized `size-12 rounded-2xl bg-muted` icon boxes.
- **Strict Z-Index Hierarchy:** `z-10` sticky headers/cards, `z-20` topbar, `z-30` desktop sidebar, `z-40` mobile drawer & notification dropdowns, `z-50` global modals (`overflow-hidden` on `body`), `z-60` global toasts.

## 7. Icons, Charts & Modals Standard
- **Icons:** FontAwesome (`fa-solid fa-...`) loaded globally. Never use AI-generated SVGs or sparkle logos.
- **Charts:** Chart.js v4+ via theme-aware helper (`window.createThemedChart`) so charts re-theme smoothly.
- **No Native Browser Popups:** `window.alert()`, `window.confirm()`, and `window.prompt()` are strictly banned. Always use `openConfirmModal`, `openFormModal`, `openComingSoonModal`, or `toast.html`.

## 8. Dynamic MongoDB Atlas Data & Security
- Every KPI, table, and chart MUST read real data from MongoDB Atlas (`core/db.py`: `users`, `student_records`, `predictions`, `datasets_log`, `notifications`, `support_tickets`, `courses`), backed by clean seeding or upload utilities and graceful fallback modals/toasts on errors.
- Keep `MONGODB_URI` and `SECRET_KEY` in `.env` (never hardcoded). Hash passwords with Django PBKDF2/Argon2 and keep CSRF protection active on all POST endpoints.

## 9. Roman Urdu Communication & 2 Actionable Suggestions
- Always communicate with the user strictly in **Roman Urdu**.
- At the end of every completed task, include **2 concise, actionable improvements** for existing code:
  - *Problem 1:* [Short bottleneck/issue] -> *Hal:* [1-line actionable fix]
  - *Problem 2:* [Short UI/code issue] -> *Hal:* [1-line actionable fix]

## 10. `.env` & Full Project Git Auto-Sync Rule (MANDATORY)
- `.env` and ALL project files (code, `templates/`, `static/`, `requirements.txt`, `.env.example`, `.gitignore`, `.agents/*`) MUST always be tracked, committed, and auto-synced/pushed to GitHub (`feature/<module>` and merged to `main`) before and after every task.
- `.gitignore` may ONLY ignore `.venv/`, `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`, and `db.sqlite3`. Never ignore `.env`.

## 11. Full-Width Fluid Responsive Layout (No Centered Box)
- NEVER wrap dashboard panels in `max-w-7xl mx-auto` or centered fixed-width containers.
- Use `<main class="flex-1 w-full min-w-0">` with fluid full-width padding and responsive grid splits (`grid-cols-1 sm:grid-cols-2 xl:grid-cols-4`, `grid-cols-1 xl:grid-cols-12`, `min-w-0`) so desktops use the full available width beside the sidebar and `320px+` mobile screens stack cleanly with zero horizontal overflow.

## 12. Desktop Viewport-Fit & Mandatory 5-Row Pagination
- Design desktop dashboards, workbenches, and CRUD tables with compact vertical spacing (`p-4`, `gap-4`, `space-y-4`, compact headers), compact chart heights (`h-44` to `h-48`, ~180px–200px), and **mandatory 5-row pagination** (`[data-paginated-container data-page-size="5"]` + `[data-pagination-bar]`) so desktop viewports fit cleanly without unnecessary vertical page scrollbars unless data/content strictly demands scrolling.

## 13. Mobile Card-List Standard (`< md` / `< 768px`)
- On mobile screens (`< 768px`), NEVER force cramped multi-column tables.
- Every list/table MUST render clean stacked mobile cards (`md:hidden`, `[data-mobile-card][data-page-item]`) while desktop (`>= md`) renders the tabular view (`hidden md:block`, `tbody tr[data-page-item]`), both synchronized inside `[data-paginated-container data-page-size="5"]` with pagination and quick search (`input[data-table-search]`).

## 14. Collapsible Sidebar on Both Desktop & Mobile
- The topbar sidebar toggle (`#mobile-sidebar-toggle`) MUST NOT be hidden on desktop (`lg:hidden` is forbidden on the toggle button).
- Clicking it on desktop (`>= 1024px`) collapses/expands the `w-64` sidebar and `#app-shell-main` left padding (`body.sidebar-collapsed`) with `localStorage` persistence (`edupredict_sidebar_collapsed`) and fires a `resize` event for Chart.js; clicking it on mobile (`< 1024px`) opens/closes the off-canvas drawer + backdrop.

## 15. Coming Soon Modal & Sidebar `"Soon"` Badge Standard
- All planned/unbuilt panel pages across Admin, Teacher, Student, and Analyst panels MUST appear in `templates/components/sidebar.html` with a `"Soon"` badge and open the global theme-aware Coming Soon modal (`openComingSoonModal` / `[data-coming-soon]`) when clicked, instead of broken links or raw placeholders. Direct routes for unbuilt pages must render `templates/panels/coming_soon_panel.html`.

## 16. Basic Everyday English Only & Compact Collapsible Sidebar
- All UI labels, sidebar links, headings, helper text, modal copy, and toast messages across every panel MUST use simple, everyday English (no complex jargon).
- Sidebar navigation labels must be short and clean, and sidebar section groups (`data-nav-group-toggle`) must be collapsible/minimizable via dropdown toggles persisted in `localStorage` (`edupredict_nav_groups`). Keep clear `title` tooltips, `cursor: pointer`, `:hover`/`:focus-visible`/`:active` states, `text-wrap: balance` on headings, and clickable table column sorting (`data-sortable`).

## 17. Zero Dead Routes, No Duplicate Icons & Mandatory Coming Soon Modals
- Never leave dead/unfinished links, broken routes, or buttons that lead to 404/empty placeholders. Either build the complete dynamic route first OR attach `data-coming-soon="true"` (`openComingSoonModal`) directly to the link/button.
- Never place duplicate `+` icons/symbols on buttons. Keep the custom theme-aware `404.html` error page active in both `DEBUG=True` and `DEBUG=False`.

## 18. Strict Role Logic & Self-Action Guards
- Enforce real-world role boundaries across all panels: Admins manage users, courses, and incoming help tickets, so Admins MUST NOT see `"Send Feedback"` or `"New Ticket"` options to message themselves (`submit_support_ticket` blocks `ADMIN`).
- Admins MUST NEVER be able to delete, deactivate, or downgrade their own active account (check BOTH `user_id` AND `email` in backend guards, omit self-destructive actions in UI rows, and pass `data-is-self="true"` to lock the self role field as read-only in `openEditUserModal`).

## 19. Zero-Lag Caching & SPA-Smooth Navigation
- Never run DB seeding, `create_index`, or password-hash checks on every page request — run startup seed/index/default-admin guards once per process (with thread locks).
- Use short-TTL in-memory caching in `core/db.py` (`get_cached` / `invalidate_cache` cleared on mutations), cache-bust static assets (`?v=9`) in `templates/base.html` and `templates/accounts/auth.html`, and provide SPA-smooth page transitions (`static/js/nav.js` with `sessionStorage` GET cache + hover prefetch + `#ep-top-progress`, invalidated on form `POST`).

## 20. Strict Role Navigation Isolation & Ultra-Simple Marks Ingestion
- **Strict Role Sidebar Isolation:** Never display all panels inside one role's sidebar. Each role (`ADMIN`, `TEACHER`, `STUDENT`, `ANALYST`) strictly renders ONLY its own dedicated navigation group(s) (Admin uses `Admin Core` + `Support & Logs`) plus the shared `Settings & Theme` dropdown (`My Profile`, `Portal Settings` for `ADMIN`, `Theme & Colors`) in `templates/components/sidebar.html`. Keep topbar and sidebar footer free of duplicate Theme buttons.
- **Ultra-Simple Marks & Attendance Ingestion:** Marks entry and sheet upload must be frictionless for teachers: manual entry uses core inputs with ID autocomplete/suggestion, and file upload accepts 3-column CSV/Excel (`student_id`, `marks`, `attendance`) with flexible aliases, `?template=csv`, and a 1.2s cancelable auto-upload grace window.

## 21. Theme Studio, My Profile, Password Toggles & Cancelable Automation
- **Theme & Appearance Live Studio (`/theme/preferences/`):** Per-user & per-panel preferences (`ep_theme_prefs:<user_id>:<role>` + MongoDB `users.theme_prefs.<ROLE>`) support Light/OLED Dark, 6 Chrome Themes, 13 Accents, 6 Presets, and Comfortable/Compact density (no sidebar LTR/RTL flip). Keep `get_user_theme_prefs` session-only on GET and sync guest `PORTAL` prefs on login via `sync_theme_prefs_on_login`.
- **My Profile (`/profile/`) & Password Toggles:** All logged-in roles get `/profile/` with read-only protected role, optional fields, and optional password update. Every password field (`/auth/`, `/profile/`, and `form_modal.html` via `[data-password-toggle]`) must include a Show/Hide eye toggle button.
- **1.2s Cancelable Auto-Upload:** `static/js/theme_studio.js` (`bindSmartFileUploads()`) enforces a 1200ms cancelable toast grace window (`window.eduPredictCancelUpload` cleared on SPA swap).

## 22. Ocean Blue Default, Cloudinary Media, Loading Guards & Widgets (Phases 22–25)
- **Ocean Blue Default & Clean Topbar:** Default theme is `shell_theme="blue"`, `accent="ocean"` (`#2563eb` light / `#3b82f6` dark) with inline Ocean Blue SVG favicons in `base.html`/`auth.html`. Remove `"Atlas Ready"` topbar pill; show `current_user.avatar_url` (or initials) in topbar & sidebar footer.
- **Cloudinary Media Policy:** Track `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` in `.env` (empty keys in `.env.example`), freeze `cloudinary` in `requirements.txt`, upload validated `<= 5 MB` avatars (`320x320` face crop) via `core/cloudinary_services.py`, and store URLs in MongoDB `users.avatar_url`.
- **Global Loading Lock & `#ep-top-progress`:** `static/js/ui_widgets.js` animates `#ep-top-progress` (`window.EduPredictProgress`), prevents double-submits, shows `"Processing..."` spinner + `aria-busy="true"` (12s fallback + `pageshow` reset, skipping `[data-no-lock]`, `[data-no-loading]`, and download forms).
- **Zero Horizontal Scrollbar & Change Password Modal:** Enforce `html, body { overflow-x: clip; }` (`global.css`) and wrapped `data_table.html` cells (`break-words max-w-[18rem]`). Never inline optional password inputs on `/profile/`; use `"Change Password"` -> `openChangePasswordModal()` (`form_modal.html`, `action="change_password"`).
- **Widgets & Phases 23–25 Roadmap:** Reuse `gradient_file_uploader.html` (`[data-gradient-uploader]`) and `faq_pro.html` (`[data-faq-pro]`, safe DOM `<mark>` highlight). Roadmap: **Phase 23** (Real-Time Notifications + Admin Feedback Reply CRUD + Typewriter Page Guide Wizard Modal), **Phase 24** (Card-Grid User/Student/Teacher Directories + Modalized Upload/Quick Entry + Dot-Graph KPI Cards), **Phase 25** (Stepper Signup Wizard + Teacher Approval Guard + Student PDF Transcript).
