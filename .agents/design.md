# Design System & UI/UX Architecture (`design.md`)

## 1. Visual Aesthetic Philosophy
- **Theme Selection:** Option A — **Modern Educational SaaS Theme** (Clean Slate/Zinc neutrals + **Ocean Blue** `#2563eb` primary accent & Blue Sidebar/Topbar Shell default, paired with an inline Ocean Blue graduation-cap SVG favicon in `base.html` and `auth.html`).
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
  --accent-primary: #2563eb;   /* Ocean Blue 600 - Default primary buttons & active nav */
  --accent-hover: #1d4ed8;     /* Ocean Blue 700 - Primary button hover */
  --accent-soft: #eff6ff;      /* Blue 50 - Active sidebar item bg */
  --status-success: #16a34a;   /* Emerald 600 - Low Risk / High Attendance */
  --status-warning: #d97706;   /* Amber 600 - Medium Risk */
  --status-danger: #dc2626;    /* Red 600 - High Dropout Risk / Anomaly */
  --shell-sidebar-bg: #eff6ff; /* Light Blue Sidebar Shell */
  --shell-topbar-bg: #f5f9ff;  /* Light Blue Topbar Shell */
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
  --accent-primary: #3b82f6;   /* Ocean Blue 500 - High-visibility primary accent */
  --accent-hover: #60a5fa;     /* Ocean Blue 400 - Hover state */
  --accent-soft: rgba(59, 130, 246, 0.16); /* Subtle active nav highlight */
  --status-success: #22c55e;
  --status-warning: #f59e0b;
  --status-danger: #ef4444;
  --shell-sidebar-bg: #0d182b; /* Deep Blue Dark Sidebar Shell */
  --shell-topbar-bg: #112038;  /* Deep Blue Dark Topbar Shell */
}
```

## 3. `@efferd/app-shell-3` Layout Architecture in Django (`templates/base.html`)
Since this is a Pure Django project, the `@efferd/app-shell-3` structure is implemented natively in `templates/base.html` using Tailwind CSS:

- **Collapsible Left Sidebar (`w-64 fixed inset-y-0 left-0 z-30`, `#mobile-sidebar-drawer`):**
  - Top Brand Header: EduPredict Logo + Role Badge (`Admin`, `Teacher`, `Student`, or `Analyst`) + close button (`#mobile-sidebar-close`, visible on both desktop and mobile).
  - Organized Collapsible Navigation Groups: Strictly isolated per logged-in role (`Rule 20`). For `ADMIN`, navigation splits cleanly into `Admin Core` (`data-nav-group="admin"`: Dashboard, Users, Courses) and `Support & Logs` (`data-nav-group="admin_ops"`: Help Tickets, Activity Logs). Teacher, Student, and Analyst retain their isolated single groups (`data-nav-group="teacher"|"student"|"analyst"`). Every logged-in role (`{% if active_role %}`) also receives a dedicated collapsible `Settings & Theme` dropdown (`data-nav-group="settings"`) containing `My Profile` (`/profile/`), `Portal Settings` (`/admin-panel/settings/`, `ADMIN` only), and `Theme & Colors` (`openThemeStudioModal()`). All group states persist in `localStorage` (`edupredict_nav_groups`).
  - Coming Soon Links: Any planned/unbuilt pages appear in the sidebar with a `"Soon"` badge and `data-coming-soon="true"` attributes, opening `#coming-soon-modal` (`openComingSoonModal`) instead of broken links.
  - Sidebar Footer: User identity card showing Cloudinary `current_user.avatar_url` image (or initials fallback) linking directly to `My Profile` (`/profile/`), Need Help button for non-Admin roles (hidden for `ADMIN` per Rule 18), and Logout button (triggers global `confirm_modal.html`). No duplicate Theme Studio button in the footer.
- **Collapsible Sidebar on Both Desktop & Mobile (`#mobile-sidebar-toggle`, `#mobile-sidebar-close`):**
  - Both the topbar sidebar toggle (`#mobile-sidebar-toggle`) and the sidebar close button (`#mobile-sidebar-close`) MUST be visible and active on BOTH desktop (`>= 1024px`) and mobile (`< 1024px`) — never hide them with `lg:hidden`.
  - **Desktop (`>= 1024px`):** Clicking `#mobile-sidebar-toggle` (or `#mobile-sidebar-close`) toggles `sidebar-collapsed` on BOTH `<html>` (`document.documentElement`) and `<body>`, using `@media (min-width: 1024px)` CSS rules (`!important`) so `#mobile-sidebar-drawer` (`w-64`) slides off-canvas (`transform: translateX(-100%)`) and `#app-shell-main` switches left padding (`lg:pl-64` <-> `0`) smoothly (`transition-all duration-200 ease-out`). State restores pre-paint from `localStorage` (`edupredict_sidebar_collapsed`), and a `resize` event fires after transition (~220ms) so Chart.js canvases resize cleanly.
  - **Mobile (`< 1024px`):** Clicking `#mobile-sidebar-toggle` opens/closes the off-canvas drawer over a backdrop (`z-40`); closes via `#mobile-sidebar-close`, `Esc` key, or outside tap.
- **Sticky Topbar (`h-16 sticky top-0 z-20 backdrop-blur`, `header.ep-topbar`) & `#ep-top-progress`:**
  - Top `#ep-top-progress` bar (`z-60`) directly inside `<body>` animates smoothly during SPA navigation and form submissions.
  - Sidebar toggle (`#mobile-sidebar-toggle`) + Current Page Title & Role Badge on the left.
  - Quick Search input (`input[data-table-search]`), Notification Bell dropdown, single Light/Dark Toggle (`#theme-toggle-btn`), and a compact `My Profile` link pill (`/profile/`) displaying `current_user.avatar_url` image (or initials fallback) on the right (NO `"Atlas Ready / Offline"` status pill in the topbar).
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
    1. **Desktop Table (`hidden md:block`):** Sticky-header table inside `overflow-x-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]` with `tbody tr[data-page-item]` and wrapped body cells (`break-words max-w-[18rem]`, reserving `whitespace-nowrap` strictly for compact status pills and `cell.actions` containers so horizontal scrollbars never appear, paired with `html, body { overflow-x: clip; }`).
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
- **Cache-Busted Assets & SPA Page Swaps:** Append `?v=` query versions (`?v=9`) to CSS/JS assets in `templates/base.html` and `templates/accounts/auth.html`, and use `static/js/nav.js` (`sessionStorage` GET cache + hover prefetch + `#ep-top-progress`, invalidated on form `POST`) to swap `#app-shell-main` and `#page-extra-js` smoothly (GPU `.spa-page-enter` with `prefers-reduced-motion`) and invoke `window.reinitEduPredictUI()`.

## 12. Strict Role Sidebar Isolation & Ultra-Simple Marks Ingestion (Rule 20)
- **Strict Role Sidebar Isolation:** Never render all roles inside one panel's sidebar. Each role (`ADMIN`, `TEACHER`, `STUDENT`, `ANALYST`) renders strictly its own dedicated navigation group(s) plus `Settings & Theme` in `templates/components/sidebar.html`. Panel responsibilities are cleanly distributed so teachers manage classes/marks, students view personal academic status, analysts manage pipelines/models, and admins manage institutional entities.
- **Ultra-Simple Marks & Attendance Ingestion:** Marks entry and sheet upload must be frictionless and jargon-free for teachers. The manual entry widget requires only 4 core inputs (Student ID with datalist autocomplete & suggested next ID, Student Name, Course, Marks 0-100, Attendance % 0-100) with secondary parameters defaulted cleanly. File upload accepts standard 3-column CSV/Excel files (`student_id`, `marks`, `attendance`) with flexible column aliases (`roll_no`, `score`, `att`), sample CSV template download (`?template=csv`), and a 1.2s cancelable auto-upload grace window.

## 13. Theme Live Studio, My Profile, Password Toggles & Cancelable Upload UX (Rule 21)
- **Theme & Appearance Live Studio (`theme_studio_modal.html`, `theme_studio.js`, `core/theme_services.py`):** Per-user & per-panel customization scoped to `ep_theme_prefs:<user_id>:<role>` + MongoDB `users.theme_prefs.<ROLE>` (and guest `PORTAL` synced on `/auth/` login), defaulting to Ocean Blue (`shell_theme="blue"`, `accent="ocean"`, `#2563eb`). Supports 2 Appearance Modes (`light`, `dark`), 6 Header & Sidebar Chrome Themes, 13 Brand Accent Swatches, 6 Surface Presets, Comfortable/Compact Density, and Accent Auto-Sync. Sidebar always stays fixed on the left (no LTR/RTL flip).
- **My Profile, Cloudinary Avatars & Change Password Modal (`user_profile.html`, `gradient_file_uploader.html`, `faq_pro.html`):** All logged-in roles share `/profile/` with protected read-only role badge, Cloudinary avatar upload/remove (`<= 5 MB`, `320x320` face crop, URL stored in `users.avatar_url`) via `gradient_file_uploader.html` (`.ep-gradient-upload`), live searchable `faq_pro.html` (`.ep-faq-panel` + safe DOM `<mark>` highlighting), and optional `Department`/`Batch`/`Phone`/`Bio`. Password updates NEVER appear inline on the Profile Details form — use the `"Change Password"` button (`openChangePasswordModal()`) via global `form_modal.html` + `[data-password-toggle]` eye icons.
- **Global Button Loading Lock & Cancelable Auto-Upload:** `static/js/ui_widgets.js` (`initGlobalSubmitGuards`) locks submit buttons with `"Processing..."` spinner + `#ep-top-progress` (12s fallback + `pageshow` reset, skipping `[data-no-lock]`, `[data-no-loading]`, and download forms). `bindSmartFileUploads()` gives `input[type="file"][data-auto-submit="true"]` a 1200ms cancelable toast grace window (`window.eduPredictCancelUpload` cleared on SPA swap). Global modals use `pointerdown` target checks for drag-safe backdrop dismissal.
- **Phases 1–59 Built:** Real-Time Notifications, Admin Feedback Reply CRUD, Card-Grid Directories, Modalized Uploads, Stepper Signup Wizard, Teacher Approval Guard, Official PDF Transcript, and Ops/Security suite are complete.

## 14. Enterprise UI/UX Masterplan — Anti-AI-Slop & Modern Polish (Phases 60–63)

### 14.1. Visual Foundation & 90 / 8 / 2 Color Discipline
- **3-Layer Depth System (No Heavy `shadow-xl`):** Use 1px hairline borders (`1px solid var(--border-subtle)`) to separate surfaces across 3 clean layers:
  - **Canvas:** Light `#f8fafc` / Dark `#090d16`
  - **Surface (Cards, Sidebar, Topbar):** Light `#ffffff` / Dark `#111827`
  - **Elevated (Table Headers, Hover Rows, Inputs):** Light `#f1f5f9` / Dark `#1e293b`
  - **Dark Mode Hairline Border:** Prefer crisp translucent hairline `rgba(255, 255, 255, 0.08)` for `--border-subtle` in dark mode.
- **90 / 8 / 2 Color Rule:** 90% neutral surface/canvas, 8% secondary text & borders, 2% Primary Ocean Blue accent (primary CTA, active nav indicator, focus ring). Reserve Green/Amber/Red strictly for status badges, dots, and chart series — never tint entire cards red or yellow.
- **Native Browser UI Theming:** Enforce `color-scheme: light dark` and `accent-color: var(--accent-primary)` on `:root` so scrollbars, checkboxes, radios, and date inputs match Light/Dark mode natively.
- **Typography & Number Precision:** Inter / Plus Jakarta Sans for UI, JetBrains Mono + `tabular-nums` for all IDs/percentages/GPAs, `text-wrap: balance` on headings, and strict 3-level contrast hierarchy (`600` values, `500` labels, `400` metadata).
- **Ban Generic AI Icon Boxes:** Never render oversized 48x48 colored rounded boxes around card icons. Use crisp inline `14px–16px` muted FontAwesome icons beside titles or `6px` status dots (`● Active`, `● High Risk`).

### 14.2. Global App Shell Polish (Sidebar, Topbar & Instant Help)
- **Slim Left Sidebar (`sidebar.html`):** `240px–256px` expanded (`68px` icon-only collapsed rail with hover tooltips on desktop). Active nav item uses soft tinted background (`rgba(37, 99, 235, 0.10)`), primary blue text, and a `3px` left vertical Ocean Blue indicator bar (no heavy solid blue block). Clean footer: `32x32` circular avatar, single-line truncated name, role pill, and 1-click Logout icon (triggers `confirm_modal.html`). Mobile drawer supports blur backdrop, outside tap, `Esc`, and swipe-left dismiss.
- **Scroll-Aware 4-Item Topbar (`topbar.html`):** Flat/seamless at scroll `y = 0`; smoothly reveals `backdrop-filter: blur(12px)` and 1px bottom border after `10px` scroll. Keep strictly 4 clean controls:
  1. Left: Clean **Breadcrumb** (`Teacher / Students`).
  2. Center-Right: Compact **Quick Search** trigger (`Search... Ctrl+K`) opening a Command/Search modal.
  3. Right 1: **Notification Bell** (unread red dot + viewport-aware dropdown).
  4. Right 2: Single **1-Click Light/Dark Toggle** + compact Profile avatar pill.
- **Admin-Only Theme Studio:** Move full Theme Studio strictly inside **Admin -> Portal Settings (`/admin-panel/settings/`)** so institutions configure one official brand theme while Teachers, Students, and Analysts use clean Ocean Blue + Light/Dark toggle.
- **Instant Contextual Help Popover:** Replace slow typewriter guide animations with an instant `0ms` `?` Help Popover in the topbar showing **3 crisp bullets + 2 quick FAQs** per page.

### 14.3. Global Components Standards
- **Ultra-Clean Clickable KPI Cards (`metric_card.html`):** Remove synthetic 14-column dot-matrix histograms. Structure: Top Row (muted label + 14px muted icon), Middle Row (bold `tabular-nums` value), Bottom Row (compact trend pill or 1-line micro-context). Support clickable filtering (e.g. clicking `"High Risk Students"` filters the page table).
- **Table-First Directories + `[Table | Cards]` Toggle:** Default Admin Users & Teacher Students to a clean **5–6 column Compact Table** (Stacked Avatar+Name+ID, Attendance % with mini inline bar, Predicted GPA, Risk Badge, right-aligned Actions) with a persisted `[Table | Cards]` toolbar toggle, sortable column headers, horizontal scrollability affordance shadows on mobile, and **1-Click Copy ID/Email** (hover copy icon -> `✓ Copied`).
- **Forms, Modals, Drawers & Toasts:** Post-interaction `:user-invalid` validation only; auto-sizing textareas (`field-sizing: content`); width-locked button loading spinner (`Saving...`); consistent motion (`180ms ease-out` modal fade+scale `0.96 -> 1`, `220ms` right-side slide-over drawer, `<body>` scroll lock + `Esc`/backdrop dismiss); stackable bottom-right toasts (max 3) with hover-pausable countdown progress bar.

### 14.4. Global Image Cropper (`Cropper.js` CDN) & Feedback Thread UX
- **Reusable Cropper Modal (`templates/components/image_cropper_modal.html`):**
  - **Avatar Mode (`/profile/`):** 1:1 circular mask, Zoom slider, Rotate 90° L/R, Reset, 48x48 live topbar preview; uploads cropped canvas blob to Cloudinary and deletes previous Cloudinary avatar.
  - **Feedback Screenshot Mode (Support/Report Issue Modal):** Supports Click Browse, Drag & Drop, and direct **`Ctrl+V` Clipboard Paste**; opens Free Crop + `16:9` / `4:3` presets; attaches neat Attachment Chips (thumbnail + filename + size + `×` remove, max 2–3 screenshots).
- **Ticket Thread & Lightbox:** Users see message + thumbnail + Admin reply timeline card; Admin `/admin-panel/tickets/` opens a **Ticket Detail Slide-Over Drawer** with **Full-Screen Image Lightbox** (dark backdrop, zoom toggle, download, `Esc` close) + quick reply & resolve toggle.

### 14.5. Auth & Onboarding (`/auth/`) Polish
- Split-screen restraint: deep Ocean Blue subtle mesh left panel (zero flashy AI blobs), crisp logo, and 3 concise bullets.
- 3-Step Stepper: smooth horizontal progress fill, directional slide transition, live 4-bar Password Strength Meter (`Weak`/`Fair`/`Good`/`Strong`) + Caps Lock badge, and a calm **Teacher Pending Approval Status Card** on teacher registration.

### 14.6. Page-by-Page Blueprint Across All 4 Panels
- **Admin (`/admin-panel/*`):** Overview (4 clickable KPIs + 60/40 charts + 5 latest open tickets + Backup pill); Users (Compact Table + `[Table | Cards]`, Pending Approval red badge, inline Approve & Reject-with-Reason modal); Courses (Capacity progress bar turning amber `>= 90%`); Tickets (thumbnail + Lightbox + Detail Drawer); Logs (Chronological Timeline with category icons + CSV); Settings (Tabbed: `General & Branding | ML Thresholds | Appearance`, syncing live `institution_name` & `current_term` to PDF headers).
- **Teacher (`/teacher-panel/*`):** Class Home (4 KPIs + `"Needs Attention Today"` watchlist + 1-click Upload Marks); Student Directory (Compact Table + click row -> **Student 360° Slide-Over Drawer** with Attendance Ring, Predicted GPA, AI Risk Reasons, 1-click Send Alert & Quick Edit); Upload Marks (clean dashed dropzone + Auto-Column Mapping preview + automatic ML & alert run); Risk Alerts (1-click `"Notify All High-Risk Students"` + auto-alert `< 75%` toggle + Read `✓✓` / Unread badges).
- **Student (`/student-panel/*`):** Dashboard (friendly greeting, Attendance SVG Progress Ring, Predicted GPA, Rank, Credits, Marks vs Class Avg chart, positive AI Insight card); Report Card & PDF (paper-style summary + prominent `"Download Official PDF"` with live Institution Name & Term); Study Tips (3–4 interactive checklist cards with progress bar); Alerts & Support (`visibilitychange` instant refresh + Screenshot `Ctrl+V` feedback).
- **Data Analyst (`/analyst-panel/*`):** Hub (1-line Model Health Strip + `"Simulate Live LMS Stream"` 5s pulsing toggle + 2–3 crisp charts + filterable table); AI Evaluation & Health (sliding underline tabs `Classification | Regression | Anomaly`, color-graded Confusion Matrix Heatmap, `(?)` metric tooltips).

### 14.7. Chart.js 6 Global Visual Defaults (`static/js/charts.js`)
1. **Gridlines:** Vertical `display: false`; horizontal ultra-light dashed `rgba(148, 163, 184, 0.15)`.
2. **Rounded Bars:** `borderRadius: 6`, `borderSkipped: false`, `maxBarThickness: 36`.
3. **Clean Doughnut:** `cutout: '72%'`, `borderWidth: 0`, centered total/percentage label.
4. **Modern Tooltips:** Dark slate rounded tooltip (`padding: 10`, `cornerRadius: 8`, `displayColors: true`, mono numbers).
5. **Minimal Legends:** Top-right circular point style (`usePointStyle: true`, `boxWidth: 8`).
6. **Zero-Reload Theme Sync:** Light/Dark toggle immediately updates all active `Chart.instances`.

### 14.8. Micro-Interactions, Mobile Touch & Rollout Phases (60–63)
- Minimum `40px–44px` touch targets on mobile buttons/pills/links; `overflow-x: clip`; positive illustrated empty states with 1 CTA; strict `@media (prefers-reduced-motion: reduce)` support; `visibilitychange` instant notification sync.
- **4 Risk-Free Rollout Phases:**
  - **Phase 60 (26A — Visual Polish):** Clean KPI cards, Chart.js 6 global defaults, Scroll-aware 4-item Topbar + `Ctrl+K` Search + Admin-Only Theme Studio + Instant 3-Bullet Help Popover + Slim Sidebar 3px active bar.
  - **Phase 61 (26B — Global Image Cropper & Ticket Lightbox):** `image_cropper_modal.html` (`Cropper.js` CDN) for Profile Avatar (1:1 circle + old Cloudinary delete) & Feedback Screenshots (`Ctrl+V` paste + Free/16:9/4:3 crop + Attachment Chips) + Admin Ticket Detail Drawer & Full-Screen Lightbox.
  - **Phase 62 (26C — Table-First Directories, Student 360° & Teacher Reject):** Default Compact Table + `[Table | Cards]` toggle + 1-Click Copy ID + Student 360° Slide-Over Drawer (`/students/<student_id>/summary/`) + Teacher Reject with Reason Modal (`REJECT_USER`).
  - **Phase 63 (26D — Hyper-Automation & Aptech Pack):** Zero-Click Auto-ML (`RandomForest(n_estimators=50, n_jobs=-1)`) + Auto-Alert escalation, Smart CSV Auto-Mapper + preview, 1-Click `"Notify All High-Risk Students"`, `visibilitychange` sync, Dynamic Institution/Term PDF Branding, Live LMS Stream Simulator (`/analyst-panel/stream-tick/`), and Aptech Final Submission Pack (`docs/aptech_submission/`).