# EduPredict Single-Institute Sample Datasets

This folder provides a ready-to-use dataset pack for running a complete end-to-end EduPredict workflow across **Admin**, **Teacher**, and **Student** panels.

## Files Included

| File | Rows | Course / Scope | Columns |
| --- | ---: | --- | --- |
| `admin_master_training_dataset.csv` | 200 | Historical multi-department training data (`LOW`: 70, `MEDIUM`: 65, `HIGH`: 65) | `student_id,full_name,birth_date,department,course_code,attendance_pct,internal_marks,assignment_score,lms_hours_per_week,previous_gpa,final_gpa,dropout_risk` |
| `teacher_cs101_class.csv` | 18 | `CS-101` (Computer Science) | `student_id,full_name,birth_date,course_code,marks,attendance` |
| `teacher_ds301_class.csv` | 18 | `DS-301` (Data Science) | `student_id,full_name,birth_date,course_code,marks,attendance` |
| `teacher_se210_class.csv` | 18 | `SE-210` (Software Engineering) | `student_id,full_name,birth_date,course_code,marks,attendance` |
| `teacher_ml401_class.csv` | 18 | `ML-401` (Machine Learning) | `student_id,full_name,birth_date,course_code,marks,attendance` |
| `teacher_ai205_class.csv` | 18 | `AI-205` (Artificial Intelligence) | `student_id,full_name,birth_date,course_code,marks,attendance` |
| `teacher_la110_class.csv` | 18 | `LA-110` (Mathematics) | `student_id,full_name,birth_date,course_code,marks,attendance` |

---

## Step 1: Admin — Upload Master Training Dataset (One-Time)

1. Sign in as **Admin** and open `/admin-panel/`.
2. Locate the **Upload Master Training CSV** card.
3. Upload `admin_master_training_dataset.csv`.
4. EduPredict ingests the 200 historical records and trains the ML suite (**RandomForest** dropout risk classifier, **Ridge** GPA regressor, and **IsolationForest** anomaly detector).
5. Confirm the status badge shows the ML model is trained and ready.

---

## Step 2: Teachers — Upload Class CSV Files

1. Sign in as an approved **Teacher** and open `/teacher-panel/`.
2. Upload your assigned class file (for example, `teacher_cs101_class.csv` for `CS-101`).
3. EduPredict automatically:
   - Tags every uploaded student record to your teacher account (strict teacher data isolation).
   - Creates or updates each student's login account in the portal.
   - Runs live GPA and dropout risk predictions using the trained ML models.
   - Displays a **Class Login Credentials Ready** summary so you can share login details with students.

---

## Step 3: Students — Sign In to the Portal

Students sign in at `/auth/` using their institute **Student ID** and auto-generated password:

- **Username (Email or Student ID field):** `student_id` (exact ID from the class CSV)
- **Password:** `<first_name_lowercase>@<birth_date>`
  - `<first_name_lowercase>` is the first word of `full_name` in lowercase.
  - `<birth_date>` is in `YYYY-MM-DD` format from the CSV.

### Sample Student Logins (1 per Class)

| Course | Student Name | Username (`student_id`) | Password |
| --- | --- | --- | --- |
| `CS-101` | Maham Iqbal | `EDU-2026-101` | `maham@2005-03-19` |
| `DS-301` | Rabia Hayes | `EDU-2026-201` | `rabia@2006-12-14` |
| `SE-210` | Farhan Foster | `EDU-2026-301` | `farhan@2005-06-11` |
| `ML-401` | Omar Ahmed | `EDU-2026-401` | `omar@2007-08-26` |
| `AI-205` | Asad Raza | `EDU-2026-501` | `asad@2004-08-12` |
| `LA-110` | Rizwan Kazmi | `EDU-2026-601` | `rizwan@2003-08-20` |
