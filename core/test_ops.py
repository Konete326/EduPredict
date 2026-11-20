import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import JsonResponse
from django.test import RequestFactory, TestCase
from cryptography.fernet import Fernet
from core.backup_crypto import decrypt_bytes
from core.decorators import _clear_rate_limit_buckets, rate_limit
from core.views_health import _build_memory_payload, _get_cgroup_memory_limit_mb


class OperationsToolingTests(TestCase):
    def test_export_backup_management_command_execution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = call_command("export_backup", format="json", output_dir=tmp_dir, filename="snap.json")
            target = Path(out_path)
            self.assertTrue(target.exists())
            self.assertEqual(target.name, "snap.json")
            parsed = json.loads(target.read_text(encoding="utf-8"))
            self.assertIn("exported_at", parsed)
            self.assertIn("collections", parsed)
            self.assertIn("users", parsed["collections"])

            out_csv = call_command("export_backup", format="csv", output_dir=tmp_dir, filename="snap.csv", quiet=True)
            target_csv = Path(out_csv)
            self.assertTrue(target_csv.exists())
            self.assertGreater(target_csv.stat().st_size, 0)
            self.assertEqual(len(list(Path(tmp_dir).glob("*.tmp*"))), 0)

    def test_export_backup_command_invalid_format_raises_error(self):
        with self.assertRaises(CommandError):
            call_command("export_backup", format="invalid_format")

    @patch("core.management.commands.export_backup.shutil.disk_usage")
    def test_export_backup_insufficient_disk_space_raises_error(self, mock_disk_usage):
        mock_disk_usage.return_value = MagicMock(total=1000000, used=999000, free=1024)
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesMessage(CommandError, "Insufficient disk space"):
                call_command("export_backup", format="json", output_dir=tmp_dir, quiet=True)

    def test_export_backup_retention_days_purges_old_backups(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            old_backup = Path(tmp_dir) / "edupredict_backup_old.json"
            old_backup.write_text("{}", encoding="utf-8")
            old_ts = time.time() - (45 * 86400)
            os.utime(str(old_backup), (old_ts, old_ts))
            self.assertTrue(old_backup.exists())

            call_command("export_backup", format="json", output_dir=tmp_dir, retention_days=30, quiet=True)
            self.assertFalse(old_backup.exists())

    def test_rate_limit_decorator_blocks_burst_traffic(self):
        _clear_rate_limit_buckets()
        rf = RequestFactory()

        @rate_limit(max_requests=2, window_seconds=60)
        def sample_view(request):
                return JsonResponse({"ok": True})

        req1 = rf.get("/test/", HTTP_ACCEPT="application/json")
        req2 = rf.get("/test/", HTTP_ACCEPT="application/json")
        req3 = rf.get("/test/", HTTP_ACCEPT="application/json")

        self.assertEqual(sample_view(req1).status_code, 200)
        self.assertEqual(sample_view(req2).status_code, 200)
        resp3 = sample_view(req3)
        self.assertEqual(resp3.status_code, 429)
        self.assertIn("Retry-After", resp3)
        self.assertTrue(int(resp3["Retry-After"]) >= 1)
        self.assertIn(b"retry_after_seconds", resp3.content)
        _clear_rate_limit_buckets()

    def test_rate_limit_decorator_emits_limit_and_remaining_headers(self):
        _clear_rate_limit_buckets()

        @rate_limit(max_requests=2, window_seconds=60)
        def sample_view(request):
            return JsonResponse({"ok": True})

        rf = RequestFactory()
        r1 = sample_view(rf.get("/t/", HTTP_ACCEPT="application/json"))
        r2 = sample_view(rf.get("/t/", HTTP_ACCEPT="application/json"))
        r3 = sample_view(rf.get("/t/", HTTP_ACCEPT="application/json"))
        self.assertEqual((r1["X-RateLimit-Limit"], r1["X-RateLimit-Remaining"]), ("2", "1"))
        self.assertEqual(r2["X-RateLimit-Remaining"], "0")
        self.assertEqual((r3.status_code, r3["X-RateLimit-Remaining"], r3["X-RateLimit-Limit"]), (429, "0", "2"))
        _clear_rate_limit_buckets()

    def test_export_backup_writes_sha256_checksum_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(call_command("export_backup", format="json", output_dir=tmp_dir, filename="snap.json", quiet=True))
            manifest = Path(tmp_dir) / "snap.json.sha256"
            self.assertTrue(manifest.exists())
            expected = hashlib.sha256(out_path.read_bytes()).hexdigest()
            self.assertEqual(manifest.read_text(encoding="utf-8").strip(), f"{expected}  snap.json")

    def test_verify_backup_command_detects_match_tamper_and_missing_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(call_command("export_backup", format="json", output_dir=tmp_dir, filename="snap.json", quiet=True))
            digest = call_command("verify_backup", str(out_path), quiet=True)
            self.assertEqual(len(digest), 64)
            out_path.write_text(out_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with self.assertRaisesMessage(CommandError, "Checksum mismatch"):
                call_command("verify_backup", str(out_path), quiet=True)
            (Path(tmp_dir) / "snap.json.sha256").unlink()
            with self.assertRaisesMessage(CommandError, "Checksum manifest not found"):
                call_command("verify_backup", str(out_path), quiet=True)
            with self.assertRaisesMessage(CommandError, "Backup file not found"):
                call_command("verify_backup", str(Path(tmp_dir) / "missing.json"), quiet=True)

    def test_encrypted_backup_roundtrip_and_key_failures(self):
        key = Fernet.generate_key().decode("utf-8")
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": ""}):
                with self.assertRaisesMessage(CommandError, "BACKUP_ENCRYPTION_KEY is not set"):
                    call_command("export_backup", format="json", output_dir=tmp_dir, encrypt=True, quiet=True)
            self.assertEqual(list(Path(tmp_dir).iterdir()), [])
            with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": key}):
                out_path = Path(call_command("export_backup", format="json", output_dir=tmp_dir, filename="snap.json", encrypt=True, quiet=True))
                self.assertEqual(out_path.name, "snap.json.enc")
                self.assertTrue((Path(tmp_dir) / "snap.json.enc.sha256").exists())
                raw = out_path.read_bytes()
                self.assertNotIn(b"collections", raw)
                self.assertIn("collections", json.loads(decrypt_bytes(raw).decode("utf-8")))
                self.assertEqual(len(call_command("verify_backup", str(out_path), quiet=True)), 64)
            with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}):
                with self.assertRaisesMessage(CommandError, "decryption failed"):
                    call_command("verify_backup", str(out_path), quiet=True)

    def test_health_cgroup_container_memory_telemetry(self):
        with patch("core.views_health.os.path.exists", side_effect=lambda p: p == "/sys/fs/cgroup/memory.max"):
            with patch("builtins.open", mock_open(read_data="536870912\n")):
                self.assertEqual(_get_cgroup_memory_limit_mb(), 512.0)
                with patch("core.views_health._get_process_memory_mb", return_value=128.0):
                    payload = _build_memory_payload()
                    self.assertEqual(payload["rss_mb"], 128.0)
                    self.assertEqual(payload["container_limit_mb"], 512.0)
                    self.assertEqual(payload["container_usage_pct"], 25.0)
            with patch("builtins.open", mock_open(read_data="max\n")):
                self.assertIsNone(_get_cgroup_memory_limit_mb())
