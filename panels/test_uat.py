from io import StringIO
from unittest.mock import MagicMock, patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase
from django.urls import reverse


class SystemHealthEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check_live_success(self):
        response = self.client.get(reverse("system_health"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("database"), "connected")
        self.assertIn("latency_ms", data)
        self.assertIn("counts", data)
        self.assertIn("users", data["counts"])
        self.assertIn("student_records", data["counts"])
        self.assertIn("cache", data)
        self.assertIn("memory", data)

    @patch("core.views_health.get_client")
    def test_health_check_db_ping_failure(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.admin.command.side_effect = RuntimeError("Atlas ping timeout")
        mock_get_client.return_value = mock_client

        response = self.client.get(reverse("system_health"))
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "unhealthy")
        self.assertEqual(data.get("database"), "disconnected")
        self.assertIn("Atlas ping timeout", data.get("error", ""))

    @patch("core.views_health.get_client")
    def test_health_check_client_none(self, mock_get_client):
        mock_get_client.return_value = None

        response = self.client.get(reverse("system_health"))
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "unhealthy")
        self.assertEqual(data.get("database"), "disconnected")
        self.assertEqual(data.get("error"), "MongoDB client unavailable")


class VerifyUATManagementCommandTests(TestCase):
    def test_verify_uat_command_full_run(self):
        out = StringIO()
        call_command("verify_uat", stdout=out)
        output_str = out.getvalue()
        self.assertIn("EduPredict End-to-End User Acceptance Test (UAT) Suite", output_str)
        self.assertIn("[PASS] Step 1: Health & System Diagnostics", output_str)
        self.assertIn("[PASS] Step 2: Auth & RBAC", output_str)
        self.assertIn("[PASS] Step 3: Admin Operations", output_str)
        self.assertIn("[PASS] Step 4: Teacher Operations", output_str)
        self.assertIn("[PASS] Step 5: Analyst Operations", output_str)
        self.assertIn("[PASS] Step 6: Student Operations", output_str)
        self.assertIn("[PASS] Step 7: Support & Theme Studio", output_str)
        self.assertIn("7/7 passed", output_str)
        self.assertIn("System 100% Operational", output_str)

    @patch("core.management.commands.verify_uat.Client.get")
    def test_verify_uat_health_failure_raises_command_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.json.return_value = {"status": "unhealthy"}
        mock_get.return_value = mock_resp

        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("verify_uat", stdout=out)
        self.assertIn("Health check failed", str(ctx.exception))

    @patch("core.management.commands.verify_uat.Client.post")
    def test_verify_uat_auth_failure_raises_command_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("verify_uat", stdout=out)
        self.assertIn("Admin login failed", str(ctx.exception))
