import os
import sys
import time
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse
from core.db import support_tickets_col, users_col


class Command(BaseCommand):
    help = "Simulates complete user journey across all 4 roles using Django test client"

    def _build_role_client(self, role, user_id, full_name, email, student_id=""):
        client = Client()
        session = client.session
        session["user"] = {
            "user_id": user_id,
            "student_id": student_id,
            "email": email,
            "full_name": full_name,
            "role": role,
            "department": "Computer Science & IT",
            "batch": "2026-A",
            "is_active": True,
        }
        session.save()
        return client

    def _format_pass(self, step_no, title, detail, elapsed):
        return f"[PASS] Step {step_no}: {title} ({detail}) [{elapsed:.2f}s]"

    def _run_step_1_health(self, client):
        t0 = time.monotonic()
        last_err = ""
        for attempt in range(3):
            try:
                resp = client.get("/health/")
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "healthy":
                        latency = data.get("latency_ms", 0.0)
                        return self._format_pass(1, "Health & System Diagnostics", f"status=healthy, latency={latency}ms", time.monotonic() - t0)
                last_err = f"HTTP {resp.status_code}"
            except Exception as exc:
                last_err = str(exc)
            if attempt < 2:
                time.sleep(0.5)
        raise CommandError(f"Health check failed after 3 attempts: {last_err}")

    def _run_step_2_auth(self, client):
        t0 = time.monotonic()
        admin_email = (os.getenv("ADMIN_EMAIL") or "admin@gmail.com").strip().lower()
        admin_password = os.getenv("ADMIN_PASSWORD") or "admin123"
        login_resp = client.post(
            reverse("accounts:auth_view"),
            {"action": "login", "email": admin_email, "password": admin_password},
        )
        if login_resp.status_code != 302:
            raise CommandError(f"Admin login failed with status {login_resp.status_code}")
        session_user = client.session.get("user")
        if not session_user or session_user.get("role") != "ADMIN":
            raise CommandError("Session user not populated as ADMIN after login")
        prof_resp = client.post(
            reverse("panels:user_profile"),
            {
                "full_name": "System Administrator",
                "email": admin_email,
                "department": "Administration",
                "batch": "ALL",
                "phone": "03001234567",
                "bio": "UAT Verified Admin",
            },
        )
        if prof_resp.status_code not in (200, 302):
            raise CommandError(f"Profile update failed with status {prof_resp.status_code}")
        return self._format_pass(2, "Auth & RBAC", "Admin login 302 redirect, session populated, profile updated", time.monotonic() - t0)

    def _run_step_3_admin(self, admin_client):
        t0 = time.monotonic()
        users_resp = admin_client.get(reverse("panels:admin_users"))
        if users_resp.status_code != 200:
            raise CommandError(f"Admin users list failed with status {users_resp.status_code}")
        admin_uid = admin_client.session.get("user", {}).get("user_id") or "USR-1000"
        del_resp = admin_client.post(
            reverse("panels:admin_users"),
            {"action": "delete", "user_id": admin_uid},
        )
        if del_resp.status_code != 302:
            raise CommandError(f"Self-delete request failed with status {del_resp.status_code}")
        admin_doc = users_col().find_one({"user_id": admin_uid})
        if admin_doc is None:
            raise CommandError("Self-protection guard failed: admin deleted self")
        courses_resp = admin_client.get(reverse("panels:admin_courses"))
        if courses_resp.status_code != 200:
            raise CommandError(f"Admin courses list failed with status {courses_resp.status_code}")
        return self._format_pass(3, "Admin Operations", "Users 200, self-delete guard verified, courses 200", time.monotonic() - t0)

    def _run_step_4_teacher(self):
        t0 = time.monotonic()
        teacher_client = self._build_role_client("TEACHER", "USR-TCH-UAT", "Dr. Teacher UAT", "teacher.uat@edupredict.edu")
        roster_resp = teacher_client.get(reverse("panels:teacher_students"))
        if roster_resp.status_code != 200:
            raise CommandError(f"Teacher student roster failed with status {roster_resp.status_code}")
        entry_resp = teacher_client.post(
            reverse("panels:teacher_students"),
            {
                "action": "manual_entry",
                "student_id": "STD-2026-001",
                "full_name": "Zainab Raza",
                "batch": "2026-A",
                "course_code": "CS-101",
                "attendance_pct": "88.0",
                "internal_marks": "85.0",
            },
        )
        if entry_resp.status_code != 302:
            raise CommandError(f"Teacher mark entry failed with status {entry_resp.status_code}")
        pdf_resp = teacher_client.get(reverse("panels:teacher_roster_pdf"))
        if pdf_resp.status_code != 200:
            raise CommandError(f"Teacher roster PDF failed with status {pdf_resp.status_code}")
        if "application/pdf" not in str(pdf_resp.get("Content-Type", "")):
            raise CommandError("Teacher roster PDF Content-Type is not application/pdf")
        if not pdf_resp.content.startswith(b"%PDF-"):
            raise CommandError("Teacher roster PDF content missing %PDF- header")
        return self._format_pass(4, "Teacher Operations", "Roster 200, manual entry 302, PDF export 200 %PDF-", time.monotonic() - t0)

    def _run_step_5_analyst(self):
        t0 = time.monotonic()
        analyst_client = self._build_role_client("ANALYST", "USR-ANA-UAT", "Data Analyst UAT", "analyst.uat@edupredict.edu")
        dash_resp = analyst_client.get(reverse("panels:analyst_dashboard"))
        if dash_resp.status_code != 200:
            raise CommandError(f"Analyst dashboard failed with status {dash_resp.status_code}")
        eval_resp = analyst_client.get(reverse("analytics:model_evaluation"))
        if eval_resp.status_code != 200:
            raise CommandError(f"Analyst evaluation failed with status {eval_resp.status_code}")
        return self._format_pass(5, "Analyst Operations", "Analytics dashboard 200, model evaluation 200", time.monotonic() - t0)

    def _run_step_6_student(self):
        t0 = time.monotonic()
        student_client = self._build_role_client("STUDENT", "USR-STD-UAT", "Zainab Raza", "student.uat@edupredict.edu", student_id="STD-2026-001")
        dash_resp = student_client.get(reverse("panels:student_dashboard"))
        if dash_resp.status_code != 200:
            raise CommandError(f"Student overview failed with status {dash_resp.status_code}")
        rpt_resp = student_client.get(reverse("panels:student_report"))
        if rpt_resp.status_code != 200:
            raise CommandError(f"Student report card failed with status {rpt_resp.status_code}")
        pdf_resp = student_client.get(reverse("panels:student_report_pdf"))
        if pdf_resp.status_code != 200:
            raise CommandError(f"Student report PDF failed with status {pdf_resp.status_code}")
        if "application/pdf" not in str(pdf_resp.get("Content-Type", "")):
            raise CommandError("Student report PDF Content-Type is not application/pdf")
        if not pdf_resp.content.startswith(b"%PDF-"):
            raise CommandError("Student report PDF content missing %PDF- header")
        return self._format_pass(6, "Student Operations", "Overview 200, report card 200, PDF download 200 %PDF-", time.monotonic() - t0)

    def _run_step_7_support_theme(self, admin_client):
        t0 = time.monotonic()
        student_client = self._build_role_client("STUDENT", "USR-STD-UAT", "Zainab Raza", "student.uat@edupredict.edu", student_id="STD-2026-001")
        sub_resp = student_client.post(
            reverse("panels:submit_support_ticket"),
            {"subject": "UAT Verification Ticket", "message": "Simulated UAT message for end-to-end check."},
        )
        if sub_resp.status_code != 302:
            raise CommandError(f"Support ticket submission failed with status {sub_resp.status_code}")
        tkt = support_tickets_col().find_one({"subject": "UAT Verification Ticket"}, sort=[("created_at", -1)])
        if not tkt:
            raise CommandError("Support ticket not found in database after submission")
        tkt_id = tkt["ticket_id"]
        res_resp = admin_client.post(
            reverse("panels:admin_tickets"),
            {"action": "toggle_status", "ticket_id": tkt_id},
        )
        if res_resp.status_code != 302:
            raise CommandError(f"Admin ticket resolution failed with status {res_resp.status_code}")
        updated_tkt = support_tickets_col().find_one({"ticket_id": tkt_id})
        if not updated_tkt or updated_tkt.get("status") != "RESOLVED":
            raise CommandError("Support ticket status was not updated to RESOLVED")
        support_tickets_col().delete_one({"ticket_id": tkt_id})
        theme_get = student_client.get(reverse("panels:theme_preferences"))
        if theme_get.status_code != 200 or not theme_get.json().get("ok"):
            raise CommandError(f"Theme preferences GET failed with status {theme_get.status_code}")
        theme_post = student_client.post(
            reverse("panels:theme_preferences"),
            {"theme_mode": "dark", "accent": "violet", "sync_shell": "true"},
        )
        if theme_post.status_code not in (200, 302):
            raise CommandError(f"Theme preferences POST failed with status {theme_post.status_code}")
        return self._format_pass(7, "Support & Theme Studio", "Ticket submitted, Admin resolved, Theme GET/POST 200", time.monotonic() - t0)

    def handle(self, *args, **options):
        try:
            call_command("migrate", verbosity=0, interactive=False)
        except Exception:
            pass
        started = time.monotonic()
        banner_line = "=" * 70
        self.stdout.write(banner_line)
        self.stdout.write("  EduPredict End-to-End User Acceptance Test (UAT) Suite")
        self.stdout.write(banner_line)
        admin_client = Client()
        steps = [
            lambda: self._run_step_1_health(admin_client),
            lambda: self._run_step_2_auth(admin_client),
            lambda: self._run_step_3_admin(admin_client),
            lambda: self._run_step_4_teacher(),
            lambda: self._run_step_5_analyst(),
            lambda: self._run_step_6_student(),
            lambda: self._run_step_7_support_theme(admin_client),
        ]
        results = []
        for step_fn in steps:
            msg = step_fn()
            results.append(msg)
            self.stdout.write(self.style.SUCCESS(msg))
        total_time = time.monotonic() - started
        self.stdout.write("-" * 70)
        self.stdout.write(
            self.style.SUCCESS(
                f"UAT Results: {len(results)}/7 passed in {total_time:.2f}s - System 100% Operational"
            )
        )
        self.stdout.write(banner_line)
        return
