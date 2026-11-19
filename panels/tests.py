import json
from unittest.mock import MagicMock, patch
from django.contrib.auth.hashers import check_password
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from accounts.services import serialize_session_user
from analytics.data_pipeline import generate_sample_dataset_df
from analytics.tests import _build_genuine_labelled_records
from core.db import invalidate_cache
from core.theme_services import get_theme_studio_catalog, get_user_theme_prefs, sync_theme_prefs_on_login
from panels.admin_services import build_user_table_data


class AnalystDashboardEvaluationTests(TestCase):
    def setUp(self):
        invalidate_cache()
        settings = {"high_risk_threshold": 70, "medium_risk_threshold": 35, "anomaly_drop_pct": 25, "min_attendance_pct": 75, "passing_gpa": 2.0, "auto_student_alerts": True, "auto_teacher_alerts": True}
        for target in ("panels.views_analyst._resolve_runtime_settings", "analytics.model_health._resolve_runtime_settings"):
            p = patch(target, return_value=dict(settings))
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

        logs_col.count_documents.return_value = 0
        with patch("analytics.model_health.student_records_col", return_value=records_col), patch("analytics.model_health.predictions_col", return_value=preds_col), patch("analytics.model_health.datasets_log_col", return_value=logs_col):
            acc_resp = client.get(reverse("panels:analyst_accuracy"))
        self.assertEqual(acc_resp.status_code, 200)
        acc_html = acc_resp.content.decode("utf-8")
        self.assertIn("Min Att 75% &middot; Pass GPA 2.0 &middot; High Risk &ge;70%", acc_html)
        self.assertIn("High &ge;70% / Med &ge;35%", acc_html)

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


class ThemePreferencesTests(TestCase):
    def setUp(self):
        invalidate_cache()

    def _set_user(self, client, role, user_id):
        session = client.session
        session["user"] = {"user_id": user_id, "role": role, "email": f"{role.lower()}@edupredict.edu", "full_name": f"Test {role.title()}"}
        session.save()

    @patch("core.theme_services.users_col")
    def test_get_theme_preferences_defaults_and_path_fallback(self, mock_users_col):
        catalog = get_theme_studio_catalog()
        self.assertEqual((len(catalog["modes"]), len(catalog["shell_themes"]), len(catalog["swatches"]), len(catalog["presets"])), (2, 6, 13, 6))
        self.assertEqual(catalog["save_url"], "/theme/preferences/")

        resp = Client().get(reverse("panels:theme_preferences"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        prefs = data["theme_prefs"]
        self.assertEqual((prefs["role"], prefs["user_id"], prefs["mode"], prefs["shell_theme"], prefs["accent"], prefs["preset"], prefs["density"]), ("PORTAL", "guest", "light", "white", "indigo", "neutral", "comfortable"))
        self.assertTrue(prefs["sync_shell"])
        self.assertEqual(prefs["tokens"]["accent_primary"], "#4f46e5")
        self.assertEqual(mock_users_col.call_count, 0)

        req = RequestFactory().get("/teacher-panel/")
        self.assertEqual(get_user_theme_prefs(req)["role"], "TEACHER")
        self.assertEqual(serialize_session_user({"user_id": "USR-T1", "role": "TEACHER", "email": "t@e.edu", "theme_prefs": {"TEACHER": {"mode": "dark"}}})["theme_prefs"]["TEACHER"]["mode"], "dark")

    @patch("core.theme_services.invalidate_cache")
    @patch("core.theme_services.users_col")
    def test_post_theme_preferences_persists_resets_and_isolates_roles(self, mock_users_col, mock_invalidate):
        client = Client()
        self._set_user(client, "TEACHER", "USR-T1")

        post_resp = client.post(
            reverse("panels:theme_preferences"),
            data=json.dumps({"mode": "dark", "shell_theme": "blue", "accent": "ocean", "preset": "matcha", "density": "compact", "sync_shell": True}),
            content_type="application/json",
        )
        self.assertEqual(post_resp.status_code, 200)
        t_prefs = post_resp.json()["theme_prefs"]
        self.assertEqual((t_prefs["role"], t_prefs["mode"], t_prefs["shell_theme"], t_prefs["accent"], t_prefs["preset"], t_prefs["density"]), ("TEACHER", "dark", "blue", "ocean", "matcha", "compact"))
        self.assertEqual(t_prefs["tokens"]["accent_primary"], "#2563eb")
        mock_users_col.return_value.update_one.assert_called_with({"user_id": "USR-T1"}, {"$set": {"theme_prefs.TEACHER": t_prefs}})
        self.assertGreaterEqual(mock_invalidate.call_count, 1)

        merge_resp = client.post(reverse("panels:theme_preferences"), {"mode": "light"}, HTTP_X_REQUESTED_WITH="EduPredict-Theme")
        self.assertEqual(merge_resp.status_code, 200)
        self.assertEqual((merge_resp.json()["theme_prefs"]["mode"], merge_resp.json()["theme_prefs"]["shell_theme"], merge_resp.json()["theme_prefs"]["preset"]), ("light", "blue", "matcha"))

        form_resp = client.post(reverse("panels:theme_preferences"), {"density": "comfortable"}, HTTP_REFERER="/teacher-panel/")
        self.assertRedirects(form_resp, "/teacher-panel/", fetch_redirect_response=False)

        self._set_user(client, "ADMIN", "USR-T1")
        admin_get = client.get(reverse("panels:theme_preferences")).json()["theme_prefs"]
        self.assertEqual((admin_get["role"], admin_get["mode"], admin_get["shell_theme"], admin_get["accent"], admin_get["preset"]), ("ADMIN", "light", "white", "indigo", "neutral"))

        admin_post = client.post(
            reverse("panels:theme_preferences"),
            data=json.dumps({"mode": "dark", "shell_theme": "red", "accent": "crimson", "preset": "gothic", "sync_shell": False}),
            content_type="application/json",
        ).json()["theme_prefs"]
        self.assertEqual((admin_post["role"], admin_post["shell_theme"], admin_post["accent"], admin_post["preset"], admin_post["sync_shell"]), ("ADMIN", "red", "crimson", "gothic", False))

        self._set_user(client, "TEACHER", "USR-T1")
        reset_resp = client.post(reverse("panels:theme_preferences"), data=json.dumps({"action": "reset"}), content_type="application/json")
        self.assertEqual(reset_resp.status_code, 200)
        reset_prefs = reset_resp.json()["theme_prefs"]
        self.assertEqual((reset_prefs["role"], reset_prefs["mode"], reset_prefs["shell_theme"], reset_prefs["accent"], reset_prefs["preset"], reset_prefs["density"]), ("TEACHER", "light", "white", "indigo", "neutral", "comfortable"))
        self.assertEqual(client.session["theme_prefs_by_role"]["ADMIN"]["shell_theme"], "red")

    @patch("core.theme_services.invalidate_cache")
    @patch("core.theme_services.record_audit_log")
    @patch("core.theme_services.student_records_col")
    @patch("core.theme_services.users_col")
    @patch("panels.views_theme.users_col")
    @patch("core.context_processors.notifications_col")
    @patch("core.db.MongoDBClient.check_health", return_value={"connected": True, "error": None})
    def test_profile_get_and_post_updates_fields_while_preserving_role(self, mock_health, mock_notifs, mock_view_users, mock_svc_users, mock_sr, mock_audit, mock_inv):
        self.assertEqual(Client().get(reverse("panels:user_profile")).status_code, 302)
        mock_notifs.return_value = MagicMock(**{"count_documents.return_value": 0, "find.return_value.sort.return_value.limit.return_value": []})
        client = Client()
        s = client.session
        s["user"] = {"user_id": "USR-1003", "student_id": "STD-2026-001", "role": "STUDENT", "email": "zainab@edupredict.edu", "full_name": "Zainab Raza", "is_active": True}
        s.save()
        mock_view_users.return_value.find_one.return_value = {"user_id": "USR-1003", "student_id": "STD-2026-001", "full_name": "Zainab Raza", "email": "zainab@edupredict.edu", "role": "STUDENT", "department": "CS", "batch": "2026-A", "phone": "0300-111", "bio": "CS Scholar", "is_active": True}
        get_resp = client.get(reverse("panels:user_profile"))
        self.assertEqual(get_resp.status_code, 200)
        html = get_resp.content.decode("utf-8")
        for marker in ('name="full_name"', 'name="phone"', 'name="bio"', 'name="new_password"', "0300-111", "CS Scholar"):
            self.assertIn(marker, html)
        mock_svc_users.return_value.find_one.return_value = None
        bad_resp = client.post(reverse("panels:user_profile"), {"full_name": "Zainab", "email": "z@e.edu", "new_password": "secret1", "confirm_password": "diff"})
        self.assertRedirects(bad_resp, reverse("panels:user_profile"), fetch_redirect_response=False)
        mock_svc_users.return_value.update_one.assert_not_called()
        post_resp = client.post(reverse("panels:user_profile"), {"full_name": "Zainab Updated", "email": "zainab.new@edupredict.edu", "department": "AI", "batch": "2027-A", "phone": "0321-999", "bio": "AI Track", "new_password": "newpass123", "confirm_password": "newpass123", "role": "ADMIN", "is_active": "false"})
        self.assertRedirects(post_resp, reverse("panels:user_profile"), fetch_redirect_response=False)
        updates = mock_svc_users.return_value.update_one.call_args[0][1]["$set"]
        self.assertEqual((updates["full_name"], updates["email"], updates["phone"], updates["bio"]), ("Zainab Updated", "zainab.new@edupredict.edu", "0321-999", "AI Track"))
        self.assertTrue(check_password("newpass123", updates["password_hash"]) and "role" not in updates and "is_active" not in updates)
        mock_sr.return_value.update_many.assert_called_once_with({"student_id": "STD-2026-001"}, {"$set": {"full_name": "Zainab Updated"}})
        self.assertEqual((client.session["user"]["role"], client.session["user"]["full_name"], client.session["user"]["phone"]), ("STUDENT", "Zainab Updated", "0321-999"))
        ser = serialize_session_user({"user_id": "USR-1", "role": "ADMIN", "email": "a@e.edu", "phone": "123", "bio": "Lead"})
        self.assertEqual((ser["phone"], ser["bio"]), ("123", "Lead"))
        _, rows = build_user_table_data([{"user_id": "USR-1", "full_name": "Root Admin", "email": "a@e.edu", "role": "ADMIN", "department": "Admin", "batch": "ALL", "is_active": True}], "ALL", "USR-1", "a@e.edu")
        self.assertEqual((rows[0][1], rows[0][6]["actions"][0]["attrs"].get("data-is-self")), ("Root Admin (You)", "true"))

    @patch("core.theme_services.users_col")
    def test_sync_theme_prefs_on_login_merges_portal_and_hydrates_db_roles(self, mock_users_col):
        client = Client()
        client.post(reverse("panels:theme_preferences"), data=json.dumps({"mode": "dark", "shell_theme": "blue", "accent": "ocean"}), content_type="application/json")
        req = RequestFactory().get("/")
        req.session = client.session
        synced = sync_theme_prefs_on_login(req, {"user_id": "USR-T9", "role": "TEACHER", "theme_prefs": {"ADMIN": {"mode": "dark", "accent": "crimson"}}})
        self.assertEqual((synced["TEACHER"]["mode"], synced["TEACHER"]["accent"], synced["TEACHER"]["user_id"]), ("dark", "ocean", "USR-T9"))
        self.assertEqual((synced["ADMIN"]["mode"], synced["ADMIN"]["accent"]), ("dark", "crimson"))
        mock_users_col.return_value.update_one.assert_called_once_with({"user_id": "USR-T9"}, {"$set": {"theme_prefs.TEACHER": synced["TEACHER"]}})
        mock_users_col.return_value.update_one.reset_mock()
        synced_keep = sync_theme_prefs_on_login(req, {"user_id": "USR-T9", "role": "TEACHER", "theme_prefs": {"TEACHER": {"mode": "light", "accent": "emerald"}}})
        self.assertEqual((synced_keep["TEACHER"]["mode"], synced_keep["TEACHER"]["accent"]), ("light", "emerald"))
        mock_users_col.return_value.update_one.assert_not_called()
