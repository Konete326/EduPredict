# Design System & UI/UX Architecture (`design.md`)

## 1. Visual Aesthetic Philosophy
- **Theme Selection:** Option A — **Modern Educational SaaS Theme** (Clean Slate/Zinc neutrals + Deep Royal Indigo primary accent).
- **Anti-AI-Slop Mandate:**
  - NEVER use neon purple-to-cyan gradients, glowing sci-fi borders, or floating 3D cartoon blobs.
  - NEVER wrap icons inside oversized muted rounded boxes (`size-12 rounded-2xl bg-muted`). Place clean FontAwesome icons inline with crisp typography or subtle 1px bordered badges.
  - Design must look like an authentic, human-crafted enterprise educational platform (inspired by Linear, Vercel, and `@efferd/app-shell-3`).

## 2. Single Source of Truth: Color Tokens (`static/css/global.css`)
All colors MUST come from CSS variables so switching between Light and Dark mode updates every panel, button, border, table, and overlay automatically with zero contrast issues.

```css
:root {
  color-scheme: light;
  --bg-canvas: #f8fafc;        /* Slate 50 - Main page background */
  --bg-surface: #ffffff;       /* Pure White - Cards, Sidebar, Header */
  --bg-elevated: #f1f5f9;      /* Slate 100 - Hover states, Table headers */
  --bg-overlay: rgba(15, 23, 42, 0.55); /* Modal backdrop */
  --text-primary: #0f172a;     /* Slate 900 - Headings & primary text */
  --text-secondary: #475569;   /* Slate 600 - Body & descriptions */
  --text-muted: #64748b;       /* Slate 500 - Captions & table labels */
  --border-subtle: #e2e8f0;    /* Slate 200 - Hairline 1px borders */
  --accent-primary: #4f46e5;   /* Indigo 600 - Primary buttons & active nav */
  --accent-hover: #4338ca;     /* Indigo 700 - Primary button hover */
  --accent-soft: #eef2ff;      /* Indigo 50 - Active sidebar item bg */
  --status-success: #16a34a;   /* Emerald 600 - Low Risk / High Attendance */
  --status-warning: #d97706;   /* Amber 600 - Medium Risk */
  --status-danger: #dc2626;    /* Red 600 - High Dropout Risk / Anomaly */
}

html.dark {
  color-scheme: dark;
  --bg-canvas: #090d16;        /* Deep Slate/Zinc 950 - Main page bg */
  --bg-surface: #111827;       /* Gray/Slate 900 - Cards, Sidebar, Header */
  --bg-elevated: #1e293b;      /* Slate 800 - Hover states, Inputs, Table header */
  --bg-overlay: rgba(2, 6, 23, 0.78); /* Dark modal backdrop */
  --text-primary: #f8fafc;     /* Slate 50 - Crisp readable primary text */
  --text-secondary: #cbd5e1;   /* Slate 300 - Secondary text */
  --text-muted: #94a3b8;       /* Slate 400 - Muted labels */
  --border-subtle: #1e293b;    /* Slate 800 - Clean 1px dark border */
  --accent-primary: #6366f1;   /* Indigo 500 - High-visibility primary accent */
  --accent-hover: #818cf8;     /* Indigo 400 - Hover state */
  --accent-soft: rgba(99, 102, 241, 0.14); /* Subtle active nav highlight */
  --status-success: #22c55e;
  --status-warning: #f59e0b;
  --status-danger: #ef4444;
}
```

## 3. `@efferd/app-shell-3` Layout Architecture in Django (`templates/base.html`)
Since this is a Pure Django project, the `@efferd/app-shell-3` structure is implemented natively in `templates/base.html` using Tailwind CSS:

- **Collapsible Left Sidebar (`w-64 fixed inset-y-0 left-0 z-30`, `#mobile-sidebar-drawer`):**
  - Top Brand Header: EduPredict Logo + Role Badge (`Admin`, `Teacher`, `Student`, or `Analyst`) + close button (`#mobile-sidebar-close`, visible on both desktop and mobile).
  - Organized Collapsible Navigation Groups: Strictly isolated per logged-in role (`Rule 20`). For `ADMIN`, navigation splits cleanly into `Admin Core` (`data-nav-group="admin"`: Dashboard, Users, Courses) and `Support & Logs` (`data-nav-group="admin_ops"`: Help Tickets, Activity Logs). Teacher, Student, and Analyst retain their isolated single groups (`data-nav-group="teacher"|"student"|"analyst"`). Every logged-in role (`{% if active_role %}`) also receives a dedicated collapsible `Settings & Theme` dropdown (`data-nav-group="settings"`) containing `My Profile` (`/profile/`), `Portal Settings` (`/admin-panel/settings/`, `ADMIN` only), and `Theme & Colors` (`openThemeStudioModal()`). All group states persist in `localStorage` (`edupredict_nav_groups`).
  - Coming Soon Links: Any planned/unbuilt pages appear in the sidebar with a `"Soon"` badge and `data-coming-soon="true"` attributes, opening `#coming-soon-modal` (`openComingSoonModal`) instead of broken links.
  - Sidebar Footer: User identity card linking directly to `My Profile` (`/profile/`), Need Help button for non-Admin roles (hidden for `ADMIN` per Rule 18), and Logout button (triggers global `confirm_modal.html`). No duplicate Theme Studio button in the footer.
- **Collapsible Sidebar on Both Desktop & Mobile (`#mobile-sidebar-toggle`, `#mobile-sidebar-close`):**
  - Both the topbar sidebar toggle (`#mobile-sidebar-toggle`) and the sidebar close button (`#mobile-sidebar-close`) MUST be visible and active on BOTH desktop (`>= 1024px`) and mobile (`< 1024px`) — never hide them with `lg:hidden`.
  - **Desktop (`>= 1024px`):** Clicking `#mobile-sidebar-toggle` (or `#mobile-sidebar-close`) toggles `sidebar-collapsed` on BOTH `<html>` (`document.documentElement`) and `<body>`, using `@media (min-width: 1024px)` CSS rules (`!important`) so `#mobile-sidebar-drawer` (`w-64`) slides off-canvas (`transform: translateX(-100%)`) and `#app-shell-main` switches left padding (`lg:pl-64` <-> `0`) smoothly (`transition-all duration-200 ease-out`). State restores pre-paint from `localStorage` (`edupredict_sidebar_collapsed`), and a `resize` event fires after transition (~220ms) so Chart.js canvases resize cleanly.
  - **Mobile (`< 1024px`):** Clicking `#mobile-sidebar-toggle` opens/closes the off-canvas drawer over a backdrop (`z-40`); closes via `#mobile-sidebar-close`, `Esc` key, or outside tap.
- **Sticky Topbar (`h-16 sticky top-0 z-20 backdrop-blur`, `header.ep-topbar`):**
  - Sidebar toggle (`#mobile-sidebar-toggle`) + Current Page Title & Role Badge on the left.
  - Quick Search input (`input[data-table-search]`), Atlas status indicator, Notification Bell dropdown, single Light/Dark Toggle (`#theme-toggle-btn`, without duplicate Theme Studio button), and a compact `My Profile` link pill (`/profile/`) on the right.
- **Main Content Area (`#app-shell-main`, `lg:pl-64 min-h-screen w-full min-w-0 flex flex-col transition-all duration-200 ease-out`):**
  - **Full-Width Fluid Container (No Centered Box):** Do NOT wrap panels in centered `max-w-* mx-auto` containers. Use `<main class="flex-1 w-full min-w-0"><div class="w-full px-3 py-3 sm:px-5 sm:py-3.5 lg:px-6 lg:py-4 xl:px-8 space-y-4">` so large desktop screens span the full available width beside the sidebar, with `<div id="page-extra-js">{% block extra_js %}{% endblock %}</div>` enabling smooth SPA script swaps while keeping `{% block content %}` and `{% block extra_js %}` contracts intact.
  - **Responsive Grid Splits (`320px+` Mobile to Large Desktop):** Use responsive splits (`grid-cols-1 sm:grid-cols-2 xl:grid-cols-4` for KPI cards and `grid-cols-1 xl:grid-cols-12` for split workbenches) with `min-w-0` on grid/flex columns so mobile screens (`320px+`) stack cleanly with zero horizontal overflow.

## 4. Strict Z-Index & Overlay Hierarchy (Zero Broken Overlays)
To guarantee overlays, dropdowns, and modals never clash or clip across panels:

- `z-10`: Sticky table headers & inline cards
- `z-20`: Sticky Topbar (`topbar.html`)
- `z-30`: Fixed Desktop Sidebar (`sidebar.html`)
- `z-40`: Mobile Off-Canvas Sidebar Drawer & Topbar Dropdowns (Notifications)
- `z-50`: Global Modal Dialogs (`confirm_modal.html`, `#coming-soon-modal`, `form_modal.html`) with `overflow-hidden` locked on `<body>` while open
- `z-60`: Global Toast Notifications (`toast.html`) in bottom-right corner

## 5. Typography & Modern Web Guidance Standards
- **Font Family:** Inter or Plus Jakarta Sans (body/UI) + JetBrains Mono (Student IDs, percentages, GPA scores, dataset metrics).
- **Tabular Numbers:** Apply `tabular-nums` on all numeric table columns and KPI counters so numbers align vertically.
- **Form Usability:** Show validation error styling only after user interaction (`:user-invalid`), never preemptively on page load.

## 6. Desktop Viewport-Fit, 5-Row Pagination & Mobile Card-List Standards
- **Desktop Viewport-Fit (No Unnecessary Page Scrollbar on Desktop):**
  - Design desktop dashboards, workbenches, and CRUD tables with compact vertical spacing (`p-4`, `gap-4`, `space-y-4`, compact hero/filter headers), compact chart heights (`h-44` to `h-48`, ~180px–200px), and mandatory 5-row pagination (`data-page-size="5"`).
  - Desktop viewports must fit primary KPIs, charts, and active table page cleanly without requiring vertical page scrollbars unless data or content strictly requires scrolling.
- **Mandatory 5-Row Pagination (`[data-paginated-container]`):**
  - Wrap every dashboard or management list/table in `<div data-paginated-container data-page-size="5">` (including `templates/components/data_table.html` with `page_size=5`).
  - Include a synchronized `[data-pagination-bar]` footer (`[data-pagination-info]` showing `Showing X-Y of Z`, `[data-page-prev]`, `[data-page-indicator]`, `[data-page-next]`).
  - Quick search (`input[data-table-search]`) filters across all rows/cards and resets pagination to page 1.
- **Mobile Card-List Standard (`< md` / `< 768px`):**
  - On mobile screens (`< 768px`), NEVER force cramped multi-column tables.
  - Every list/table MUST render BOTH:
    1. **Desktop Table (`hidden md:block`):** Sticky-header table inside `overflow-x-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]` with `tbody tr[data-page-item]`.
    2. **Mobile Stacked Cards (`md:hidden space-y-2.5`):** Crisp native mobile cards (`[data-mobile-card][data-page-item]`) in `data_table.html` featuring a rounded-xl elevated header band (`forloop.first`), bordered clean label/value rows with `min-w-0 break-words`, and a subtle full-width footer bar (`pt-2 border-t`) for touch-friendly `Actions` buttons. Similarly, `analyst_evaluation_section.html` renders `sm:hidden` 2x2 Confusion Matrix cards (`TN`, `FP`, `FN`, `TP`) alongside the `hidden sm:block` matrix table.
  - Both desktop rows and mobile cards inside the same `[data-paginated-container]` stay synchronized with 5-row pagination and quick search.

## 7. Global Coming Soon Modal Standard (`openComingSoonModal`)
- **Global Modal (`templates/components/confirm_modal.html` + `static/js/app.js`):**
  - `#coming-soon-modal` (`z-50`, theme-aware tokens `--bg-surface`, `--bg-overlay`, `--border-subtle`, `--accent-soft`, `--accent-primary`) displays the module badge (`#coming-soon-modal-panel`), title (`#coming-soon-modal-title`), summary (`#coming-soon-modal-desc`), upcoming feature checklist (`#coming-soon-modal-features`), and a Close button.
  - Trigger via `window.openComingSoonModal({ panel, title, description, features })` or declaratively on any link/card with `data-coming-soon="true"`, `data-coming-panel`, `data-coming-title`, `data-coming-desc`, and pipe-separated (`|`) `data-coming-features`.
- **Direct Routes for Unbuilt Modules:** Any unbuilt panel route renders `templates/panels/coming_soon_panel.html` with a viewport-fit roadmap summary, live MongoDB counts, and a modal trigger (`openComingSoonModal`).

## 8. Basic Everyday English, Compact Collapsible Sidebar & Interactive States (Rule 16)
- **Simple Everyday English:** All UI labels, sidebar links, headings, helper text, modal copy, and toast messages across every panel MUST use plain, everyday English (no complex jargon). Pair crisp FontAwesome icons with descriptive `title` tooltips and progressive disclosure via global modals (`form_modal.html`, `confirm_modal.html`, `#coming-soon-modal`).
- **Compact Collapsible Sidebar Groups:** Keep sidebar links short and scannable (`text-xs`, tight padding), and provide collapsible/minimizable section dropdown toggles (`data-nav-group-toggle`) persisted in `localStorage` (`edupredict_nav_groups`).
- **Interactive Guidance States:** Apply `cursor: pointer` on all interactive buttons, links, selects, and sortable headers, ensure crisp `:hover`, `:focus-visible`, and `:active` press feedback, apply `text-wrap: balance` on headings, provide clickable table column sorting (`data-sortable`), and enforce mandatory 5-row pagination (`data-page-size="5"`).

## 9. Zero Dead Routes, Single Icons & Custom 404 Safety Net (Rule 17)
- **Zero Dead Links or Placeholders:** Every button, card action, and sidebar link MUST either navigate to a fully built dynamic route OR attach `data-coming-soon="true"` (`openComingSoonModal`) directly on the element.
- **No Duplicate `+` Icons:** Never place duplicate `+` icons/symbols on buttons (use either `<i class="fa-solid fa-plus"></i>` or `+` text, never both).
- **Theme-Aware 404 Page:** Keep the custom theme-aware `404.html` error page active in both `DEBUG=True` and `DEBUG=False` for unrecognized URLs.

## 10. Strict Role Boundaries & Self-Action UI Guards (Rule 18)
- **Admin Ticket Boundary:** Admins manage users, courses, and incoming help tickets, so hide `"Send Feedback"` and `"New Ticket"` self-submission controls for `ADMIN` in both `sidebar.html` and `admin_tickets.html` (backed by `submit_support_ticket` blocking `ADMIN`).
- **Self-Action Guards:** Never render Delete, Deactivate, or self-role-downgrade actions on the logged-in Admin's own table/card row (matching both `user_id` and `email`), matching backend guards in `panels/admin_services.py`. Self-edit rows mark `data-is-self="true"` so `openEditUserModal` locks the Role field to read-only `ADMIN (Active Self Account — Protected)` with a hidden `role="ADMIN"`.

## 11. Zero-Lag Caching, Cache-Busting & SPA-Smooth Navigation (Rule 19)
- **Process-Once Startup & Short-TTL Cache:** Never run DB seeding, index creation, or password-hash verification on every request; use process-once startup guards and `core/db.py` short-TTL caching (`get_cached` / `invalidate_cache` cleared on every mutation).
- **Cache-Busted Assets & SPA Page Swaps:** Append `?v=` query versions (`?v=8`) to CSS/JS assets in `templates/base.html` and `templates/accounts/auth.html`, and use `static/js/nav.js` (`sessionStorage` GET cache + hover prefetch, invalidated on form `POST`) to swap `#app-shell-main` and `#page-extra-js` smoothly and invoke `window.reinitEduPredictUI()`.

## 12. Strict Role Sidebar Isolation & Ultra-Simple Marks Ingestion (Rule 20)
- **Strict Role Sidebar Isolation:** Never render all roles inside one panel's sidebar. Each role (`ADMIN`, `TEACHER`, `STUDENT`, `ANALYST`) renders strictly its own dedicated navigation group(s) plus `Settings & Theme` in `templates/components/sidebar.html`. Panel responsibilities are cleanly distributed so teachers manage classes/marks, students view personal academic status, analysts manage pipelines/models, and admins manage institutional entities.
- **Ultra-Simple Marks & Attendance Ingestion:** Marks entry and sheet upload must be frictionless and jargon-free for teachers. The manual entry widget requires only 4 core inputs (Student ID with datalist autocomplete & suggested next ID, Student Name, Course, Marks 0-100, Attendance % 0-100) with secondary parameters defaulted cleanly. File upload accepts standard 3-column CSV/Excel files (`student_id`, `marks`, `attendance`) with flexible column aliases (`roll_no`, `score`, `att`), sample CSV template download (`?template=csv`), and a 1.2s cancelable auto-upload grace window.

## 13. Theme Live Studio, My Profile, Password Toggles & Cancelable Upload UX (Rule 21)
- **Theme & Appearance Live Studio (`theme_studio_modal.html`, `theme_studio.js`, `core/theme_services.py`):** Per-user & per-panel customization scoped to `ep_theme_prefs:<user_id>:<role>` + MongoDB `users.theme_prefs.<ROLE>` (and guest `PORTAL` synced on `/auth/` login). Supports 2 Appearance Modes (`light`, `dark`), 6 Header & Sidebar Chrome Themes (`dark`, `red`, `dark-green`, `green`, `blue`, `white`), 13 Brand Accent Swatches, 6 Surface Presets (`neutral`, `butter`, `matcha`, `chocolate`, `stone`, `gothic`), Comfortable/Compact Density, and Accent Auto-Sync. Sidebar always stays fixed on the left (no LTR/RTL flip).
- **My Profile & Unified Password Toggles:** All logged-in roles share `/profile/` (`user_profile.html`) with protected read-only role badge, optional fields (`Department`, `Batch`, `Phone`, `Bio`), and optional password change. Every password input across `/auth/`, `/profile/`, and `form_modal.html` (`createFieldNode` + `[data-password-toggle]`) provides a Show/Hide eye icon toggle (`pr-9`).
- **1.2s Cancelable Auto-Upload & Drag-Safe Modals:** `bindSmartFileUploads()` gives `input[type="file"][data-auto-submit="true"]` a 1200ms toast grace window (`"Auto-uploading <filename> in 1.2s..."` + clickable `"Cancel"` button via `window.eduPredictCancelUpload`, cleared on SPA swap). Global modals use `pointerdown` target checks for drag-safe backdrop dismissal.