from unittest.mock import DEFAULT, MagicMock, patch
from django.test import Client, TestCase
from django.urls import reverse
from core.context_processors import _build_notification_query, _fetch_unread_notifications
from core.db import invalidate_cache
from panels.admin_services import mark_notifications_read
import panels.student_alert_services as student_alert_svc
from panels.student_alert_services import _load_recent_alerts, get_student_alerts_context
from panels.student_services import _batch_rank, _build_tips, _fetch_batch_docs, _load_student_overview


def _login_client(user_data):
    client = Client()
    session = client.session
    session["user"] = dict(user_data)
    session.save()
    return client


def _mock_notifs_col():
    col = MagicMock()
    col.count_documents.return_value = 0
    col.find.return_value.sort.return_value.limit.return_value = []
    return col


def _teacher_payloads():
    badge = {"text": "Needs Help", "status": "warning"}
    action_btn = {
        "actions": [{
            "label": "Send Alert",
            "icon": "fa-solid fa-bell",
            "variant": "primary",
            "title": "Send alert",
            "onclick": "openSendAlertModal(this)",
            "attrs": {"data-student-id": "STD-2026-001", "data-full-name": "Zainab Raza", "data-course-code": "CS-101"},
        }]
    }
    dash_ctx = {
        "kpis": {"total_students": 2, "avg_attendance": 81.5, "avg_marks": 75.0, "at_risk_count": 1, "courses_count": 1},
        "chart_data": {"course_summary": {"labels": ["CS-101"], "attendance": [81.5], "marks": [75.0]}, "badge_breakdown": {"labels": ["Excellent", "Stable", "Needs Help", "High Risk"], "counts": [1, 0, 1, 0]}},
        "at_risk_headers": ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"],
        "at_risk_rows": [["STD-2026-001", "Zainab Raza", "CS-101", "68.0%", "64.0", badge, action_btn]],
    }
    students_ctx = {
        "filter_options": {"batches": ["2026-A"], "courses": ["CS-101"], "statuses": ["Excellent", "Stable", "Needs Help", "High Risk"]},
        "student_headers": ["Student ID", "Name", "Batch", "Course", "Attendance", "Marks", "Pred GPA", "Status", "Actions"],
        "student_rows": [["STD-2026-001", "Zainab Raza", "2026-A", "CS-101", "68.0%", "64.0", "2.60", badge, action_btn]],
        "export_rows": [{"student_id": "STD-2026-001", "full_name": "Zainab Raza", "batch": "2026-A", "course_code": "CS-101", "attendance_pct": "68.0", "internal_marks": "64.0", "predicted_gpa": "2.60", "status": "Needs Help"}],
    }
    alerts_ctx = {
        "kpis": {"at_risk_count": 1, "high_risk_count": 0, "medium_risk_count": 1, "alerts_sent": 1, "unread_alerts": 1},
        "roster_headers": ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"],
        "roster_rows": [["STD-2026-001", "Zainab Raza", "CS-101", "68.0%", "64.0", badge, action_btn]],
        "history_headers": ["Title", "Student", "Message", "Level", "Read", "Date"],
        "history_rows": [["Teacher Alert (CS-101)", "STD-2026-001", "Attend class", {"text": "WARNING", "status": "warning"}, {"text": "Unread", "status": "warning"}, "2026-11-18 10:00"]],
        "students_picker": [{"student_id": "STD-2026-001", "full_name": "Zainab Raza", "course_code": "CS-101"}],
    }
    ingest_ctx = {
        "roster_headers": ["Student ID", "Name", "Batch", "Course", "Attendance", "Marks", "GPA", "Actions"],
        "roster_rows": [["STD-2026-001", "Zainab Raza", "2026-A", "CS-101", "68.0%", "64.0", "2.60", {"actions": []}]],
        "log_headers": ["File Name", "Rows", "Fixed", "Status", "Uploaded"],
        "log_rows": [["marks.csv", 10, 0, {"text": "COMPLETED", "status": "success"}, "2026-11-18 10:00"]],
        "courses_list": ["CS-101"],
        "students_picker": [{"student_id": "STD-2026-001", "full_name": "Zainab Raza", "course_code": "CS-101"}],
        "required_columns": ["student_id", "marks", "attendance"],
    }
    return dash_ctx, students_ctx, alerts_ctx, ingest_ctx


def _student_payloads():
    overview_ctx = {
        "record": {
            "student_id": "STD-2026-001", "full_name": "Zainab Raza", "batch": "2026-A",
            "courses": [{"course_code": "CS-101", "attendance_pct": 88.0, "internal_marks": 82.0, "assignment_score": 85.0, "lms_hours_weekly": 8.0}],
            "avg_attendance": 88.0, "avg_marks": 82.0, "avg_assignment": 85.0, "lms_hours_weekly": 8.0,
            "previous_gpa": 3.4, "predicted_gpa": 3.55, "risk_level": "LOW", "risk_score": 0.12,
            "is_anomaly": False, "anomaly_reason": "", "recommendation": "Keep steady practice.", "generated_at": "2026-11-18 10:00",
        },
        "subject_rows": [{
            "course_code": "CS-101", "my_marks": 82.0, "class_marks": 76.0, "my_attendance": 88.0,
            "class_attendance": 81.0, "diff": 6.0, "status": {"text": "Excellent", "status": "success"},
        }],
        "chart": {"labels": ["CS-101"], "mine": [82.0], "class_avg": [76.0]},
        "rank": {"rank": 3, "total": 25},
        "tips": [{"icon": "fa-solid fa-circle-check", "status": "success", "title": "You are on track", "text": "Keep your study routine steady."}],
        "insight": {"summary": "Great work!", "status": "success", "points": ["Attendance: 88.0%", "Predicted GPA: 3.55"]},
        "unread_alerts": 1,
        "active_courses": 4,
        "credits": 3.0,
        "teacher_alerts": [{"id": "507f1f77bcf86cd799439011", "title": "Teacher Alert", "message": "Well done", "severity": "INFO", "is_read": False, "created": "2026-11-18 10:00", "status": "info"}],
    }
    alerts_ctx = {
        "alerts": [{"id": "507f1f77bcf86cd799439011", "title": "Teacher Alert", "message": "Attend lab session", "severity": "WARNING", "is_read": False, "created": "2026-11-18 10:00", "status": "warning"}],
        "my_tickets": [{"ticket_id": "TKT-1001", "subject": "Schedule", "message": "Check lab hours", "status": "OPEN", "status_badge": {"text": "Open", "status": "warning"}, "created": "2026-11-18 09:00"}],
        "unread": 1,
        "total": 1,
    }
    return overview_ctx, alerts_ctx


class TeacherPanelTests(TestCase):
    def setUp(self):
        invalidate_cache()

    @patch("panels.views_teacher.get_teacher_ingest_context")
    @patch("panels.views_teacher.get_teacher_alerts_context")
    @patch("panels.views_teacher.get_teacher_students_context")
    @patch("panels.views_teacher.get_teacher_dashboard_context")
    @patch("core.db.MongoDBClient.check_health")
    @patch("core.context_processors.notifications_col")
    def test_teacher_pages_csv_exports_and_sidebar_isolation(
        self, mock_notifs, mock_health, mock_dash, mock_students, mock_alerts, mock_ingest
    ):
        mock_notifs.return_value = _mock_notifs_col()
        mock_health.return_value = {"connected": True, "error": None}
        mock_dash.return_value, mock_students.return_value, mock_alerts.return_value, mock_ingest.return_value = _teacher_payloads()

        client = _login_client({"user_id": "USR-T1", "role": "TEACHER", "email": "t@edupredict.edu", "full_name": "Dr. Ayesha Khan"})
        for path, marker in (
            ("/teacher-panel/", "teacher-at-risk-table"),
            ("/teacher-panel/students/", "teacher-students-table"),
            ("/teacher-panel/alerts/", "teacher-alert-roster-table"),
            ("/teacher-panel/ingest/", "teacher-roster-table"),
        ):
            resp = client.get(path)
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode("utf-8")
            self.assertIn(marker, html)
            self.assertIn('data-nav-group="teacher"', html)
            self.assertNotIn('data-nav-group="admin"', html)
            self.assertNotIn('data-nav-group="student"', html)

        students_csv = client.get("/teacher-panel/students/?export=csv")
        self.assertEqual(students_csv.status_code, 200)
        self.assertTrue(students_csv["Content-Type"].startswith("text/csv"))
        self.assertIn("student_id,full_name,batch,course_code", students_csv.content.decode("utf-8"))
        self.assertIn("STD-2026-001", students_csv.content.decode("utf-8"))

        template_csv = client.get("/teacher-panel/ingest/?template=csv")
        self.assertEqual(template_csv.status_code, 200)
        self.assertTrue(template_csv["Content-Type"].startswith("text/csv"))
        self.assertIn("student_id,full_name,course_code,marks,attendance", template_csv.content.decode("utf-8"))

    @patch("panels.views_teacher.send_student_alert", return_value=({"title": "Teacher Alert"}, None))
    def test_teacher_post_send_alert_and_rbac_redirects(self, mock_send):
        teacher = _login_client({"user_id": "USR-T1", "role": "TEACHER", "email": "t@edupredict.edu", "full_name": "Dr. Ayesha Khan"})
        resp = teacher.post(
            reverse("panels:teacher_alerts"),
            {"action": "send_alert", "student_id": "STD-2026-001", "full_name": "Zainab", "course_code": "CS-101", "severity": "WARNING", "message": "Attend class"},
        )
        self.assertRedirects(resp, reverse("panels:teacher_alerts"), fetch_redirect_response=False)
        mock_send.assert_called_once_with("STD-2026-001", "Zainab", "CS-101", "WARNING", "Attend class", "Dr. Ayesha Khan")

        for role, expected_dash in (("STUDENT", "panels:student_dashboard"), ("ANALYST", "panels:analyst_dashboard")):
            client = _login_client({"user_id": f"USR-{role}", "role": role, "email": f"{role.lower()}@edupredict.edu", "full_name": f"Test {role.title()}"})
            for route_name in ("panels:teacher_dashboard", "panels:teacher_alerts"):
                self.assertRedirects(client.get(reverse(route_name)), reverse(expected_dash), fetch_redirect_response=False)


class StudentPanelTests(TestCase):
    def setUp(self):
        invalidate_cache()

    @patch("panels.views_student.get_student_alerts_context")
    @patch("panels.views_student.get_student_overview_context")
    @patch("core.db.MongoDBClient.check_health")
    @patch("core.context_processors.notifications_col")
    def test_student_pages_csv_download_and_sidebar_isolation(
        self, mock_notifs, mock_health, mock_overview, mock_alerts
    ):
        mock_notifs.return_value = _mock_notifs_col()
        mock_health.return_value = {"connected": True, "error": None}
        mock_overview.return_value, mock_alerts.return_value = _student_payloads()

        client = _login_client({"user_id": "USR-1003", "student_id": "STD-2026-001", "role": "STUDENT", "email": "s@edupredict.edu", "full_name": "Zainab Raza"})
        for path, marker in (
            ("/student-panel/", "student-subject-table"),
            ("/student-panel/report/", "student-report-table"),
            ("/student-panel/tips/", "My Study Tips"),
            ("/student-panel/notifications/", "My Sent Feedback &amp; Replies"),
        ):
            resp = client.get(path)
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode("utf-8")
            self.assertIn(marker, html)
            self.assertIn('data-nav-group="student"', html)
            self.assertNotIn('data-nav-group="admin"', html)
            self.assertNotIn('data-nav-group="teacher"', html)

        report_csv = client.get("/student-panel/report/download/")
        self.assertEqual(report_csv.status_code, 200)
        self.assertTrue(report_csv["Content-Type"].startswith("text/csv"))
        csv_text = report_csv.content.decode("utf-8")
        self.assertIn("full_name,student_id,batch,course_code", csv_text)
        self.assertIn("STD-2026-001", csv_text)

    @patch("panels.views_student.mark_notifications_read", return_value=2)
    def test_student_mark_notifications_and_rbac_redirects(self, mock_mark):
        student = _login_client({"user_id": "USR-1003", "student_id": "STD-2026-001", "role": "STUDENT", "email": "s@edupredict.edu", "full_name": "Zainab Raza"})
        resp = student.post(reverse("panels:student_notifications"), {"action": "mark_all"})
        self.assertRedirects(resp, reverse("panels:student_notifications"), fetch_redirect_response=False)
        mock_mark.assert_called_once_with({"user_id": "USR-1003", "student_id": "STD-2026-001", "role": "STUDENT"})

        for role, expected_dash in (("TEACHER", "panels:teacher_dashboard"), ("ANALYST", "panels:analyst_dashboard")):
            client = _login_client({"user_id": f"USR-{role}", "role": role, "email": f"{role.lower()}@edupredict.edu", "full_name": f"Test {role.title()}"})
            for route_name in ("panels:student_dashboard", "panels:student_report"):
                self.assertRedirects(client.get(reverse(route_name)), reverse(expected_dash), fetch_redirect_response=False)

    @patch("panels.student_services.student_records_col")
    def test_batch_rank_aggregates_distinct_students_on_marks_scale(self, mock_records_col):
        mock_records_col.return_value.find.return_value = [
            {"student_id": "STD-1", "internal_marks": 90},
            {"student_id": "STD-1", "internal_marks": 80},
            {"student_id": "STD-2", "internal_marks": 78},
            {"student_id": "STD-2", "internal_marks": 72},
            {"student_id": "STD-3", "internal_marks": 60},
        ]
        self.assertEqual(_batch_rank("STD-2", "2026-A", 75.0), {"rank": 2, "total": 3})
        self.assertEqual(_batch_rank("STD-1", "2026-A", 85.0), {"rank": 1, "total": 3})
        self.assertEqual(_batch_rank("STD-3", "2026-A", 60.0), {"rank": 3, "total": 3})
        self.assertIsNone(_batch_rank("STD-2", None, 75.0))
        mock_records_col.return_value.find.assert_called_with({"batch": "2026-A"}, {"_id": 0, "student_id": 1, "internal_marks": 1})
        tips = _build_tips({"avg_attendance": 78.0, "avg_marks": 80.0, "risk_level": "LOW", "lms_hours_weekly": 8.0}, None, 75.0, 82.0, min_att=80.0)
        self.assertEqual(tips[0]["title"], "Raise your attendance above 90%")
        self.assertTrue(callable(get_student_alerts_context))

    @patch("panels.student_alert_services.notifications_col")
    @patch.multiple("panels.student_services", _resolve_runtime_settings=DEFAULT, student_records_col=DEFAULT, predictions_col=DEFAULT, notifications_col=DEFAULT, courses_col=DEFAULT)
    def test_single_query_recent_alerts_and_dynamic_excellent_threshold(self, mock_notifs, _resolve_runtime_settings, student_records_col, predictions_col, notifications_col, courses_col):
        mock_notifs.return_value.find.return_value.sort.return_value.limit.return_value = [
            {"_id": "a1", "title": "Alert 1", "message": "Check attendance", "severity": "WARNING", "is_read": False},
            {"_id": "a2", "title": "Alert 2", "message": "Great quiz", "severity": "INFO", "is_read": True},
        ]
        res = _load_recent_alerts("STD-1", "USR-1", "STUDENT", limit=5)
        self.assertEqual(len(res), 2)
        self.assertEqual(mock_notifs.return_value.find.call_count, 1)
        self.assertEqual(mock_notifs.return_value.find_one.call_count, 0)
        self.assertTrue(hasattr(student_alert_svc, "_alert_targets"))
        self.assertFalse(hasattr(student_alert_svc, "_load_alert_detail"))
        mock_notifs.return_value.find.assert_called_once_with({"$or": student_alert_svc._alert_targets("STD-1", "USR-1", "STUDENT")})
        _resolve_runtime_settings.return_value = {"min_attendance_pct": 90}
        docs = [
            {"student_id": "STD-1", "full_name": "Ali", "batch": "2026-A", "course_code": "CS-101", "internal_marks": 85.0, "attendance_pct": 86.0},
            {"student_id": "STD-1", "full_name": "Ali", "batch": "2026-A", "course_code": "CS-102", "internal_marks": 85.0, "attendance_pct": 96.0},
        ]
        rec_cur = MagicMock()
        rec_cur.sort.return_value = docs
        rec_cur.__iter__.side_effect = lambda: iter(docs)
        student_records_col.return_value.find.return_value = rec_cur
        predictions_col.return_value.find_one.return_value = None
        notifications_col.return_value = _mock_notifs_col()
        courses_col.return_value.count_documents.return_value = 2
        courses_col.return_value.find.return_value = [{"credits": 3.0}, {"credits": 3.0}]
        statuses = {r["course_code"]: r["status"]["text"] for r in _load_student_overview("STD-1", "USR-1", "STUDENT")["subject_rows"]}
        self.assertEqual(student_records_col.return_value.find.call_count, 2)
        self.assertEqual(statuses["CS-101"], "Needs Help")
        self.assertNotEqual(statuses["CS-101"], "Excellent")
        self.assertEqual(statuses["CS-102"], "Excellent")
        notifications_col.return_value.count_documents.assert_called_once_with({"is_read": False, "$or": student_alert_svc._alert_targets("STD-1", "USR-1", "STUDENT")})
        _fetch_batch_docs("", course_codes=["CS-101", "CS-102"])
        student_records_col.return_value.find.assert_called_with({"course_code": {"$in": ["CS-101", "CS-102"]}}, {"_id": 0, "student_id": 1, "course_code": 1, "attendance_pct": 1, "internal_marks": 1, "assignment_score": 1})
        with patch("panels.admin_services.notifications_col") as mock_admin_notifs:
            mock_admin_notifs.return_value.update_many.return_value.modified_count = 1
            self.assertEqual(mark_notifications_read({"user_id": "USR-1", "student_id": "STD-1", "role": "STUDENT"}), 1)
            or_list = mock_admin_notifs.return_value.update_many.call_args[0][0]["$or"]
            self.assertTrue({"target_user_id": "USR-1"} in or_list and {"target_user_id": "STD-1"} in or_list and {"target_user_id": ""} not in or_list)
            mark_notifications_read({"user_id": "USR-2", "student_id": "", "role": "ADMIN"})
            self.assertNotIn({"target_user_id": ""}, mock_admin_notifs.return_value.update_many.call_args[0][0]["$or"])
        student_records_col.return_value.find.reset_mock()
        empty_cur = MagicMock(**{"sort.return_value": []})
        empty_cur.__iter__.side_effect = lambda: iter([])
        student_records_col.return_value.find.return_value = empty_cur
        _load_student_overview("STD-EMPTY", "USR-EMPTY", "STUDENT")
        self.assertEqual(student_records_col.return_value.find.call_count, 1)
        clean_targets = student_alert_svc._alert_targets("", "USR-1", "STUDENT")
        self.assertNotIn({"target_user_id": ""}, clean_targets)
        self.assertIn({"target_user_id": "USR-1"}, clean_targets)
        q1 = _build_notification_query("USR-1", "STUDENT", student_id="STD-1")
        self.assertTrue({"target_user_id": "USR-1"} in q1["$or"] and {"target_user_id": "STD-1"} in q1["$or"])
        q2 = _build_notification_query("USR-1", "ADMIN", student_id="")
        self.assertNotIn({"target_user_id": ""}, q2["$or"])
        with patch("core.context_processors.notifications_col") as mock_topbar_notifs:
            mock_cur = MagicMock()
            mock_cur.sort.return_value.limit.return_value = [{"_id": "n1", "title": "Alert 1"}]
            mock_topbar_notifs.return_value.find.return_value = mock_cur
            mock_topbar_notifs.return_value.count_documents.return_value = 1
            invalidate_cache()
            items, count = _fetch_unread_notifications({"user_id": "USR-1", "student_id": "STD-1"}, "STUDENT")
            self.assertEqual(count, 1)
            self.assertEqual(items[0]["id"], "n1")
            topbar_or = mock_topbar_notifs.return_value.find.call_args[0][0]["$or"]
            self.assertIn({"target_user_id": "STD-1"}, topbar_or)
            self.assertNotIn({"target_user_id": ""}, topbar_or)
