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
3. @efferd/app-shell-3 Layout Architecture in Django (templates/base.html)
Since this is a Pure Django project, the @efferd/app-shell-3 structure is implemented natively in templates/base.html using Tailwind CSS:

Desktop Left Sidebar (w-64 fixed inset-y-0 left-0 z-30):

Top Brand Header: EduPredict Logo + Role Badge (Admin, Teacher, Student, or Analyst).

Navigation Groups: Clean single-line links (truncate) with fa-solid icons. Active route gets bg-[var(--accent-soft)] text-[var(--accent-primary)] font-medium.

Sidebar Footer: Logged-in user name, email, Support button, and Logout button (triggers global confirm modal).

Mobile Navigation Drawer (lg:hidden):

Slides out smoothly over a backdrop (z-40) when the hamburger menu button is clicked; closes on Esc key or outside tap.

Sticky Topbar (h-16 sticky top-0 z-20 backdrop-blur):

Breadcrumb / Current Page Title on the left.

Quick Search input, Notification Bell dropdown, and Light/Dark Theme Toggle on the right.

Main Content Area (`lg:pl-64 min-h-screen flex flex-col`):

- **Full-Width Fluid Container (No Centered Box):** Do NOT wrap panels in centered `max-w-* mx-auto` containers. Use `<main class="flex-1 w-full min-w-0"><div class="w-full px-3 py-4 sm:px-5 sm:py-5 lg:px-6 lg:py-6 xl:px-8 space-y-6">` so large desktop screens span the full available width beside the sidebar.
- **Responsive Grid Splits (`320px+` Mobile to Large Desktop):** Use responsive splits (`grid-cols-1 sm:grid-cols-2 xl:grid-cols-4` for KPI cards and `grid-cols-1 xl:grid-cols-12` for split workbenches), apply `min-w-0` on grid/flex columns, and wrap tables in `overflow-x-auto` so mobile screens (`320px+`) stack cleanly with zero horizontal overflow.

4. Strict Z-Index & Overlay Hierarchy (Zero Broken Overlays)
To guarantee overlays, dropdowns, and modals never clash or clip across panels:

z-10: Sticky table headers & inline cards

z-20: Sticky Topbar (topbar.html)

z-30: Fixed Desktop Sidebar (sidebar.html)

z-40: Mobile Off-Canvas Sidebar Drawer & Topbar Dropdowns (Notifications)

z-50: Global Modal Dialogs (confirm_modal.html, form_modal.html) with overflow-hidden locked on <body> while open

z-60: Global Toast Notifications (toast.html) in bottom-right corner

5. Typography & Modern Web Guidance Standards
Font Family: Inter or Plus Jakarta Sans (body/UI) + JetBrains Mono (Student IDs, percentages, GPA scores, dataset metrics).

Tabular Numbers: Apply tabular-nums on all numeric table columns and KPI counters so numbers align vertically.

Form Usability: Show validation error styling only after user interaction (:user-invalid), never preemptively on page load.

Responsive Data Tables: Wrap all tables inside overflow-x-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] with sticky headers and clean mobile horizontal scroll.