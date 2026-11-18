from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from django.test import Client, TestCase
from django.urls import reverse
from analytics.data_pipeline import generate_sample_dataset_df
from analytics.tests import _build_genuine_labelled_records
from core.db import _MEMORY_CACHE, invalidate_cache
import panels.admin_audit_services as audit_svc
from panels.admin_services import create_course_record


class AnalystDashboardEvaluationTests(TestCase):
    def setUp(self):
        invalidate_cache()
        p = patch("panels.views_analyst._resolve_runtime_settings", return_value={"high_risk_threshold": 70, "medium_risk_threshold": 35, "anomaly_drop_pct": 25, "min_attendance_pct": 75, "passing_gpa": 2.0, "auto_student_alerts": True, "auto_teacher_alerts": True})
        p.start()
        self.addCleanup(p.stop)

    def _login_as(self, role, user_id="USR-TEST-1"):
        client = Client()
        session = client.session
        session["user"] = {
            "user_id": user_id,
            "role": role,
            "email": f"{role.lower()}@edupredict.edu",
            "full_name": f"Test {role.title()}",
        }
        session.save()
        return client

    @patch("core.context_processors.notifications_col")
    @patch("core.db.MongoDBClient.check_health")
    @patch("panels.views_analyst.datasets_log_col")
    @patch("panels.views_analyst.predictions_col")
    @patch("panels.views_analyst.student_records_col")
    def test_analyst_dashboard_shows_genuine_evaluation_metrics_single_load(
        self, mock_records, mock_preds, mock_logs, mock_health, mock_notifs
    ):
        records = _build_genuine_labelled_records(40, include_anomaly_labels=True)
        records_col = MagicMock()
        records_col.find.return_value = records
        mock_records.return_value = records_col

        preds_col = MagicMock()
        preds_col.find.return_value = [
            {
                "student_id": r["student_id"],
                "predicted_gpa": r["actual_gpa"],
                "dropout_risk_score": 0.8 if r["dropout_label"] else 0.1,
                "risk_level": "HIGH" if r["dropout_label"] else "LOW",
                "is_anomaly": False,
                "anomaly_reason": "",
                "recommendation": "Keep steady progress.",
            }
            for r in records
        ]
        mock_preds.return_value = preds_col

        logs_cursor = MagicMock()
        logs_cursor.sort.return_value.limit.return_value = []
        logs_col = MagicMock()
        logs_col.find.return_value = logs_cursor
        mock_logs.return_value = logs_col
        mock_health.return_value = {"connected": True, "error": None}
        notifs_col = MagicMock()
        notifs_col.count_documents.return_value = 0
        notifs_cursor = MagicMock()
        notifs_cursor.sort.return_value.limit.return_value = []
        notifs_col.find.return_value = notifs_cursor
        mock_notifs.return_value = notifs_col

        client = self._login_as("ANALYST")
        resp = client.get(reverse("panels:analyst_dashboard"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        self.assertEqual(records_col.find.call_count, 1)
        self.assertIn('id="ml-evaluation-section"', html)
        self.assertIn("Dropout Risk Classifier (RandomForestClassifier)", html)
        self.assertIn("GPA Forecaster (Ridge)", html)
        self.assertIn("Anomaly Detector (IsolationForest)", html)
        self.assertIn("COMPLETED", html)
        self.assertIn("EVALUATED", html)
        self.assertIn("Confusion Matrix", html)
        self.assertIn("Accuracy", html)
        self.assertIn("Precision", html)
        self.assertIn("Recall", html)
        self.assertIn("F1-Score", html)
        self.assertIn("MAE", html)
        self.assertIn("MSE", html)
        self.assertIn("RMSE", html)
        self.assertIn("R&sup2; Score", html)
        self.assertIn("32", html)
        self.assertIn("8", html)
        self.assertIn("Data &amp; Predictions Hub", html)
        self.assertIn("Student Predictions", html)
        self.assertIn('href="/analyst-panel/#ml-evaluation-section"', html)
        self.assertNotIn('data-coming-title="AI Accuracy"', html)
        self.assertIn('High &ge;70% &middot; Med &ge;35% &middot; Drop &gt;25%', html)

        with patch("analytics.ml_engine.student_records_col") as mock_ml_records:
            eval_resp = client.get(reverse("analytics:model_evaluation"))
            self.assertEqual(eval_resp.status_code, 200)
            self.assertEqual(mock_ml_records.call_count, 0)

    @patch("core.context_processors.notifications_col")
    @patch("core.db.MongoDBClient.check_health")
    @patch("panels.views_analyst.datasets_log_col")
    @patch("panels.views_analyst.predictions_col")
    @patch("panels.views_analyst.student_records_col")
    def test_analyst_dashboard_handles_unlabelled_data_honestly(
        self, mock_records, mock_preds, mock_logs, mock_health, mock_notifs
    ):
        sample_records = generate_sample_dataset_df(30).to_dict(orient="records")
        records_col = MagicMock()
        records_col.find.return_value = sample_records
        mock_records.return_value = records_col

        preds_col = MagicMock()
        preds_col.find.return_value = []
        mock_preds.return_value = preds_col

        logs_cursor = MagicMock()
        logs_cursor.sort.return_value.limit.return_value = []
        logs_col = MagicMock()
        logs_col.find.return_value = logs_cursor
        mock_logs.return_value = logs_col
        mock_health.return_value = {"connected": True, "error": None}
        notifs_col = MagicMock()
        notifs_col.count_documents.return_value = 0
        notifs_cursor = MagicMock()
        notifs_cursor.sort.return_value.limit.return_value = []
        notifs_col.find.return_value = notifs_cursor
        mock_notifs.return_value = notifs_col

        client = self._login_as("ANALYST")
        resp = client.get(reverse("panels:analyst_dashboard"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        self.assertIn("NO_GENUINE_LABELS", html)
        self.assertIn("UNAVAILABLE", html)
        self.assertIn("UNSUPERVISED", html)
        self.assertIn("Metrics Unavailable", html)
        self.assertIn("Unsupervised Mode", html)
        self.assertNotIn("Confusion Matrix", html)
        self.assertIn("did not manufacture accuracy scores", html)

    @patch("core.context_processors.notifications_col")
    @patch("core.db.MongoDBClient.check_health")
    @patch("panels.views_analyst.evaluate_models", side_effect=RuntimeError("Eval engine test failure"))
    @patch("panels.views_analyst.datasets_log_col")
    @patch("panels.views_analyst.predictions_col")
    @patch("panels.views_analyst.student_records_col")
    def test_dashboard_survives_evaluation_error_gracefully(
        self, mock_records, mock_preds, mock_logs, mock_eval, mock_health, mock_notifs
    ):
        records_col = MagicMock()
        records_col.find.return_value = []
        mock_records.return_value = records_col
        mock_preds.return_value.find.return_value = []
        mock_logs.return_value.find.return_value.sort.return_value.limit.return_value = []
        mock_health.return_value = {"connected": True, "error": None}
        notifs_col = MagicMock()
        notifs_col.count_documents.return_value = 0
        notifs_col.find.return_value.sort.return_value.limit.return_value = []
        mock_notifs.return_value = notifs_col

        client = self._login_as("ANALYST")
        resp = client.get(reverse("panels:analyst_dashboard"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertIn("Could not evaluate models: Eval engine test failure", html)
        self.assertIn("Data &amp; Predictions Hub", html)

    def test_unauthorized_users_cannot_access_analyst_evaluation(self):
        anon = Client()
        self.assertEqual(anon.get(reverse("panels:analyst_dashboard")).status_code, 302)
        self.assertEqual(anon.get(reverse("analytics:model_evaluation")).status_code, 302)

        student = self._login_as("STUDENT")
        self.assertRedirects(
            student.get(reverse("panels:analyst_dashboard")),
            reverse("panels:student_dashboard"),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            student.get(reverse("analytics:model_evaluation")),
            reverse("panels:student_dashboard"),
            fetch_redirect_response=False,
        )

        teacher = self._login_as("TEACHER")
        self.assertRedirects(
            teacher.get(reverse("analytics:model_evaluation")),
            reverse("panels:teacher_dashboard"),
            fetch_redirect_response=False,
        )


class _MemCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction):
        self._docs.sort(key=lambda d: str(d.get(field) or ""), reverse=(direction == -1))
        return self

    def limit(self, count):
        self._docs = self._docs[:count]
        return self

    def __iter__(self):
        return iter(self._docs)


class _MemCol:
    def __init__(self, docs=None):
        self.docs = [dict(d) for d in (docs or [])]

    def _matches(self, doc, query):
        for k, v in (query or {}).items():
            if k == "$or" and not any(self._matches(doc, sub) for sub in v):
                return False
            elif isinstance(v, dict):
                if ("$in" in v and doc.get(k) not in v["$in"]) or ("$exists" in v and (k in doc) != bool(v["$exists"])):
                    return False
            elif k != "$or" and doc.get(k) != v:
                return False
        return True

    def create_index(self, *args, **kwargs):
        return "idx"

    def count_documents(self, query=None):
        return sum(1 for d in self.docs if self._matches(d, query))

    def find_one(self, query=None, projection=None):
        return next((dict(d) for d in self.docs if self._matches(d, query)), None)

    def find(self, query=None, projection=None):
        return _MemCursor([dict(d) for d in self.docs if self._matches(d, query)])

    def insert_one(self, doc):
        self.docs.append(dict(doc))
        return MagicMock(inserted_id=len(self.docs))

    def update_one(self, query, update, upsert=False):
        for d in self.docs:
            if self._matches(d, query):
                d.update(dict(update.get("$set") or {}))
                return MagicMock(matched_count=1, modified_count=1)
        if upsert:
            self.docs.append({**(query or {}), **dict(update.get("$set") or {})})
        return MagicMock(matched_count=0, modified_count=0)

    def delete_many(self, query):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not self._matches(d, query)]
        return MagicMock(deleted_count=before - len(self.docs))


class AdminLogsAndSettingsTests(TestCase):
    def setUp(self):
        invalidate_cache()
        now = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)
        self.cols = {
            "activity_logs": _MemCol(), "system_settings": _MemCol(), "notifications": _MemCol(),
            "users": _MemCol([{"user_id": "USR-1001", "full_name": "Dr. Ayesha Khan", "role": "TEACHER", "department": "Computer Science", "is_active": True, "created_at": now}]),
            "courses": _MemCol([{"course_code": "CS-101", "title": "Intro to CS", "department": "Computer Science", "instructor": "Dr. Ayesha Khan", "status": "ACTIVE", "created_at": now}]),
            "support_tickets": _MemCol([{"ticket_id": "TKT-1001", "user_name": "Zainab Raza", "role": "STUDENT", "subject": "Attendance check", "status": "OPEN", "created_at": now}]),
            "datasets_log": _MemCol([{"filename": "fall_2026.csv", "uploaded_by": "Saad Farooq", "rows_processed": 40, "missing_values_fixed": 2, "status": "COMPLETED", "uploaded_at": now}]),
        }
        for p in (
            patch("core.db.MongoDBClient.get_collection", side_effect=lambda name: self.cols.setdefault(name, _MemCol())),
            patch("core.db.MongoDBClient.check_health", return_value={"connected": True, "error": None}),
            patch.object(audit_svc, "_AUDIT_SEED_DONE", False),
        ):
            p.start()
            self.addCleanup(p.stop)

    def _login_as(self, role, user_id="USR-ADM-1"):
        client = Client()
        session = client.session
        session["user"] = {"user_id": user_id, "role": role, "email": f"{role.lower()}@edupredict.edu", "full_name": f"Test {role.title()}"}
        session.save()
        return client

    def test_admin_logs_get_filters_csv_and_sidebar_links(self):
        client = self._login_as("ADMIN")
        resp = client.get(reverse("panels:admin_logs"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertIn('id="admin-logs-table"', html)
        for text in ("Total Events", "Admin Actions", "Data & ML Events", "Security Events", "?category=USERS", "?category=COURSES", "?category=TICKETS", "?category=DATA", "?category=SYSTEM", reverse("panels:admin_logs"), reverse("panels:admin_settings")):
            self.assertIn(text, html)
        self.assertNotIn('data-coming-title="Activity Logs"', html)
        self.assertNotIn('data-coming-title="Settings"', html)
        self.assertIn('id="mobile-sidebar-close"', html)
        self.assertNotIn('id="mobile-sidebar-close" type="button" title="Hide menu" class="lg:hidden', html)
        data_resp = client.get(reverse("panels:admin_logs"), {"category": "DATA"})
        self.assertEqual(data_resp.status_code, 200)
        self.assertIn("fall_2026.csv", data_resp.content.decode("utf-8"))
        csv_resp = client.get(reverse("panels:admin_logs"), {"export": "csv"})
        self.assertEqual(csv_resp.status_code, 200)
        self.assertTrue(csv_resp["Content-Type"].startswith("text/csv"))
        self.assertIn("Log ID,Actor,Role,Category,Action,Activity Summary", csv_resp.content.decode("utf-8"))

    def test_admin_logs_post_note_records_and_invalidates_cache(self):
        client = self._login_as("ADMIN")
        client.get(reverse("panels:admin_logs"))
        self.assertIn("admin:logs:ALL", _MEMORY_CACHE)
        post_resp = client.post(reverse("panels:admin_logs"), {"action": "log_note", "filter_category": "ALL", "category": "SYSTEM", "severity": "WARNING", "summary": "Nightly audit note recorded"})
        self.assertRedirects(post_resp, reverse("panels:admin_logs"), fetch_redirect_response=False)
        self.assertNotIn("admin:logs:ALL", _MEMORY_CACHE)
        self.assertTrue(any(d.get("summary") == "Nightly audit note recorded" and d.get("source") == "MANUAL" for d in self.cols["activity_logs"].docs))
        self.assertIn("Nightly audit note recorded", client.get(reverse("panels:admin_logs")).content.decode("utf-8"))
        clear_resp = client.post(reverse("panels:admin_logs"), {"action": "clear_custom"})
        self.assertRedirects(clear_resp, reverse("panels:admin_logs"), fetch_redirect_response=False)
        self.assertNotIn("Nightly audit note recorded", client.get(reverse("panels:admin_logs")).content.decode("utf-8"))
        created_course, err = create_course_record("AI-900", "Deep Learning", "AI", "2026-A", "Dr. Bilal", 3, 50, actor_name="Dr. Admin Lead")
        self.assertIsNone(err)
        self.assertIsNotNone(created_course)
        self.assertTrue(any(d.get("action") == "CREATE_COURSE" and d.get("actor") == "Dr. Admin Lead" and "AI-900" in d.get("summary", "") for d in self.cols["activity_logs"].docs))

    def test_admin_settings_get_update_and_reset_defaults(self):
        client = self._login_as("ADMIN")
        get_resp = client.get(reverse("panels:admin_settings"))
        self.assertEqual(get_resp.status_code, 200)
        html = get_resp.content.decode("utf-8")
        for marker in ('id="admin-settings-table"', 'name="institution_name"', 'value="save_settings"'):
            self.assertIn(marker, html)
        save_resp = client.post(reverse("panels:admin_settings"), {"action": "save_settings", "institution_name": "EduPredict Flagship", "current_term": "Spring 2027", "default_batch": "2027-A", "passing_gpa": "2.5", "min_attendance_pct": "80", "high_risk_threshold": "75", "medium_risk_threshold": "40", "anomaly_drop_pct": "20", "auto_student_alerts": "on"})
        self.assertRedirects(save_resp, reverse("panels:admin_settings"), fetch_redirect_response=False)
        updated_html = client.get(reverse("panels:admin_settings")).content.decode("utf-8")
        for expected in ("EduPredict Flagship", "Spring 2027", "80%", "75%", "Custom"):
            self.assertIn(expected, updated_html)
        reset_resp = client.post(reverse("panels:admin_settings"), {"action": "reset_defaults"})
        self.assertRedirects(reset_resp, reverse("panels:admin_settings"), fetch_redirect_response=False)
        reset_html = client.get(reverse("panels:admin_settings")).content.decode("utf-8")
        for expected in ("EduPredict Academic Portal", "Fall 2026", "75%", "70%"):
            self.assertIn(expected, reset_html)

    def test_non_admin_roles_redirected_from_logs_and_settings(self):
        anon = Client()
        for route_name in ("panels:admin_logs", "panels:admin_settings"):
            self.assertEqual(anon.get(reverse(route_name)).status_code, 302)
        for role, expected_dash in (("STUDENT", "panels:student_dashboard"), ("TEACHER", "panels:teacher_dashboard"), ("ANALYST", "panels:analyst_dashboard")):
            client = self._login_as(role)
            for route_name in ("panels:admin_logs", "panels:admin_settings"):
                self.assertRedirects(client.get(reverse(route_name)), reverse(expected_dash), fetch_redirect_response=False)
