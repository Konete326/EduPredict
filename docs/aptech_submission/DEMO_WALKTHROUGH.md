# EduPredict — 5-Minute Viva & Demo Walkthrough Script

Use this structured 5-minute demonstration script during the **Aptech Project Defense / Viva** to showcase every core, ML, hyper-automation, and security feature cleanly.

---

## Pre-Demo Readiness Checklist (30 Seconds Before Viva)

1. Start server: `.\.venv\Scripts\python.exe manage.py runserver`
2. Keep `docs/aptech_submission/sample_aptech_test_dataset.csv` ready on Desktop or easy file picker path.
3. Open `http://127.0.0.1:8000/auth/` in the browser (Ocean Blue Light mode default; ready to toggle Dark mode anytime).

---

## Minute 1 (0:00 – 1:00): Authentication Stepper & Admin Approval / Rejection

1. **Unified Auth Portal (`/auth/`):**
   - Point out the 2-column enterprise layout, live database indicator, Light/Dark mode toggle, and password Show/Hide + Caps Lock warnings.
   - Click **Create Account** to demonstrate the **3-Step Registration Wizard** (`1. Account -> 2. Profile -> 3. Security`), noting the **Teacher approval notice** and that `ADMIN` cannot self-register publicly.
   - Sign in as Admin using the configured `ADMIN_EMAIL` / `ADMIN_PASSWORD` (or quick-fill button).
2. **Admin User Governance (`/admin-panel/users/`):**
   - Show the **Table-First Compact Directory** with the `[Table | Cards]` toggle and **1-click Copy ID** button.
   - Click the **Pending Approval** filter pill (`?role=PENDING`) and highlight both **Approve** and **Reject** (`openRejectUserModal` requiring an audited reason that blocks rejected login and logs `REJECT_USER`).
3. **Portal Settings & Branding (`/admin-panel/settings/`):**
   - Show dynamic **Portal Name (`institution_name`)** and **Current Term (`current_term`)** fields plus **Theme & Appearance Live Studio** (restricted strictly to Admin).

---

## Minute 2 (1:00 – 2:15): Teacher Hyper-Automation, Smart CSV Mapper & Student 360°

1. **Upload Marks & Smart CSV Auto-Mapper (`/teacher-panel/ingest/`):**
   - Click **Upload Spreadsheet** and choose `docs/aptech_submission/sample_aptech_test_dataset.csv`.
   - Before the 1.2s cancelable auto-upload fires (click **Cancel** on the toast if you want examiners to inspect the preview longer), point out the **Smart CSV Column Auto-Mapper** preview showing non-standard headers (`Roll_No -> student_id`, `Att_% -> attendance_pct`, `Test_Score -> internal_marks`, `Prev_GPA -> previous_gpa`, `LMS_Hours -> lms_hours_weekly`) and the 3-row preview table.
   - Click **Upload & Auto-Process** to show automatic missing-value imputation + zero-click ML prediction + automatic `< 75%` and High-Risk alert generation.
2. **Student 360° Slide-Over Drawer (`/teacher-panel/students/`):**
   - Click any Student name or the `360` action button to slide open the **Student 360° Drawer** showing the animated **SVG Attendance Ring**, Predicted GPA, **AI Risk Reasons**, enrolled courses, and recent alerts.
3. **Risk Alerts Automation (`/teacher-panel/alerts/`):**
   - Show the **Auto-Alert < 75%: On/Off** toggle button.
   - Click **Notify All High-Risk Students** for 1-click batch intervention dispatch, and point out the `Read ✓✓` / `Unread` tracking badges in **Alerts I Sent**.

---

## Minute 3 (2:15 – 3:30): Student Portal, Official PDF Transcript & Instant Alerts

1. **Student Dashboard (`/student-panel/`):**
   - Sign in as a Student (or showcase Student role) showing the Attendance Progress Ring, Predicted GPA, Class Rank, Earned Credits, and Marks vs. Class Average chart.
2. **Report Card & Dynamic Official PDF (`/student-panel/report/`):**
   - Point out the **Portal / Term** metadata row inside the Report Summary card (`institution_name · current_term` synced from Admin Portal Settings).
   - Click **Download PDF Transcript** (`/student-panel/report/download-pdf/`) and open the generated **ReportLab PDF** showing the institutional header branding, subject comparison table, letter grades, and AI advisory block.
3. **Instant Notifications & Feedback (`/student-panel/notifications/`):**
   - Highlight `visibilitychange` instant notification refresh and the global **Need Help** modal supporting `Ctrl+V` screenshot paste and **Cropper.js** aspect cropping.

---

## Minute 4 (3:30 – 4:30): Data Analyst Hub & Live LMS Stream Simulator

1. **Data & Predictions Hub (`/analyst-panel/`):**
   - Switch to the Analyst account and demonstrate the 3 Chart.js visualizations (Dropout Risk Doughnut, Attendance vs. Predicted GPA Scatter Plot, and Course Demand Forecast).
2. **Simulate Live LMS Stream (`/analyst-panel/stream-tick/`):**
   - Click the pulsing **Simulate Live LMS Stream** button in the top header.
   - Show `#live-stream-status-strip` appearing with real-time 5-second streamed events (`student_id`, risk level dot, attendance %) and live KPI counts (`Preds · High · Anom`). Click any streamed student chip to open their **Student 360° Drawer**.
   - Click **Stop Live LMS Stream** to halt polling cleanly.
3. **Leakage-Free Model Evaluation (`/analyst-panel/#ml-evaluation-section`):**
   - Point out `RandomForestClassifier(n_estimators=50, n_jobs=-1)`, `Ridge`, and `IsolationForest` evaluation cards with genuine labels from `sample_aptech_test_dataset.csv` and the Confusion Matrix.

---

## Minute 5 (4:30 – 5:00): Operations, Security & Automated Test Proof

1. Open `/health/` in the browser to demonstrate live MongoDB Atlas ping latency, collection counts, cache status, and memory telemetry.
2. Summarize verification proof in terminal or slide:
   - `manage.py check`: 0 issues
   - `manage.py test`: Full unit & integration suite passing
   - `manage.py verify_uat`: 7/7 end-to-end role checks passing
   - `node --check`: All 11 JavaScript modules syntax-verified
   - Encrypted MongoDB backups via `export_backup --encrypt` and `verify_backup`
