# Product Requirements Document (PRD) — EduPredict

## 1. Project Overview
- **Project Name:** EduPredict — Big Data & Predictive Analytics Educational Portal
- **Framework & Database:** Python Django (MVT Architecture) + MongoDB Atlas (Cloud Database)
- **Target Audience:** Educational Institutions (Administrators, Teachers, Students, and Data Analysts)
- **Core Objective:** Provide an automated, ultra-simple, beginner-friendly educational portal that ingests student academic/attendance data, stores and processes it in MongoDB Atlas, runs automated Machine Learning predictions (dropout risk, performance trends, course demand), and displays insights via clean, interactive dashboards with Light/Dark mode support.

## 2. Core Philosophy: Ultra-Simple & Automated UX
- **Zero Technical Friction for Users:** End-users (Students, Teachers, Admins, Analysts) will never configure complex parameters. Uploads are 1-click CSV/Excel drops; predictions run automatically upon data upload or via a single "Run Prediction" button.
- **Unified Global Shell:** Every panel uses the exact same `@efferd/app-shell-3` layout structure (Collapsible Left Sidebar + Top Header + Main Content Area) so all team members' work looks like a single, unified system.
- **Global Reusable Components:** Modals, Cards, Tables, Badges, Toast Notifications, and Forms are created once inside `templates/components/` and included everywhere via Django `{% include %}`.

## 3. User Roles & Dedicated Panels

### 3.1. Administrator Panel (`/admin-panel/`)
- **Overview Dashboard:** 4 KPI metric cards (Total Students, Active Teachers, High Dropout Risk Count, System Uptime Status) + 2 Chart.js charts (Department-wise Enrolment & Monthly Attendance Trend).
- **User Management:** View, Add, Edit, and Deactivate users (Admin, Teacher, Student, Analyst) using a global searchable table and global Confirmation Modal.
- **Course & Batch Management:** Simple CRUD for courses, subjects, and academic batches.
- **System Logs & Backups:** 1-click "Export MongoDB Backup (JSON/CSV)" and automated system health status indicator.
- **Support Ticket Resolution:** View user feedback/issues and change status (`Open` -> `Resolved`) with 1 click.

### 3.2. Teacher Panel (`/teacher-panel/`)
- **Class Overview Dashboard:** Summary of assigned classes, average class score, and automated list of "At-Risk Students" requiring attention.
- **1-Click Data Ingestion (CSV/Excel Upload & Quick Entry):**
  - Upload attendance or marks sheet (CSV/Excel) which automatically validates, cleans missing values, and saves to MongoDB Atlas.
  - Simple inline table for manual attendance or marks update.
- **Student Performance Tracker:** Filter students by batch/subject and view automatically generated performance badges (`Excellent`, `Stable`, `Needs Help`, `High Dropout Risk`).
- **Send Alert:** 1-click button to send an automated warning notification to a struggling student.

### 3.3. Student Panel (`/student-panel/`)
- **Personal Learning Dashboard:** Clean summary of current Attendance %, GPA/Grade Prediction, Earned Credits, and Upcoming Deadlines.
- **AI Performance & Risk Insight Card:** Automated, encouraging plain-language insight showing predicted final score and simple actionable tips (e.g., "Attend next 4 lectures to boost attendance above 85%").
- **Subject-wise Progress & Visuals:** Radar/Bar chart comparing student's marks with class average, plus downloadable report card.
- **Notifications & Support Center:** View alerts from teachers/system and submit a quick support/feedback form.

### 3.4. Data Analyst Panel (`/analyst-panel/`)
- **Big Data & Ingestion Hub:** Upload historical or real-time educational datasets (demographics, LMS logs, academic records, attendance). Automatic missing-data imputation and schema validation report.
- **Automated ML Prediction Engine:**
  - **Dropout Risk Model:** Predicts probability (`Low`, `Medium`, `High`) of student dropout.
  - **Grade/Performance Forecaster:** Predicts next semester GPA based on historical trends.
  - **Course Demand Predictor:** Forecasts upcoming semester course enrollments.
  - **Anomaly Detection:** Automatically flags unusual attendance drops or grade spikes.
- **Interactive Visual Explorer:** Filterable Chart.js visualizations (Correlation Scatter Plot, Dropout Distribution Doughnut, Trend Line Graph) with 1-click CSV report export.

## 4. Global Features (Shared Across All Panels)
1. **Authentication & Role Routing (`/auth/`):** Single clean Sign-In / Sign-Up page. Upon login, Django automatically redirects the user to their respective role dashboard (`/admin-panel/`, `/teacher-panel/`, `/student-panel/`, or `/analyst-panel/`).
2. **Real-Time Notification Bell:** Topbar notification dropdown displaying unread alerts with a "Mark all as read" button.
3. **Light / Dark Theme Toggle:** Persistent theme switcher in the Topbar that updates the entire UI, tables, modals, and Chart.js graphs smoothly without any broken overlays.
4. **Feedback & Support Drawer/Modal:** Accessible from the sidebar footer across all roles to submit queries or bug reports.

## 5. Strict Scope & Anti-Bloat Rules
- **Reject MERN/React Completely:** No React, Vite, Next.js, or JSX files. Everything is Pure Django + HTML5 Templates + Tailwind CSS + Vanilla JS.
- **One Feature Per Execution:** Coding agents must implement only the single feature/module requested by the user, test it, sync with Git, and ask before starting the next feature.