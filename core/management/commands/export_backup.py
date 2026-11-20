import hashlib
import shutil
import time
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from panels.admin_seed import build_backup_payload
from core.backup_crypto import encrypt_bytes, get_fernet

MIN_BACKUP_FREE_BYTES = 50 * 1024 * 1024


class Command(BaseCommand):
    help = "Export full MongoDB database backup in JSON or CSV format."

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=["json", "csv"],
            default="json",
            help="Backup output format (json or csv).",
        )
        parser.add_argument(
            "--output-dir",
            default="backups",
            help="Directory path where backup file is saved.",
        )
        parser.add_argument(
            "--filename",
            default="",
            help="Custom filename for the exported backup.",
        )
        parser.add_argument(
            "--retention-days",
            type=int,
            default=0,
            help="Purge backup files older than specified days (0 to disable).",
        )
        parser.add_argument(
            "--encrypt",
            action="store_true",
            help="Encrypt the backup with BACKUP_ENCRYPTION_KEY and save it with a .enc extension.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress informational stdout output.",
        )

    def _check_disk_space(self, target_dir, required_bytes=MIN_BACKUP_FREE_BYTES):
        target_dir.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(target_dir)
        if usage.free < required_bytes:
            raise CommandError(
                f"Insufficient disk space in {target_dir}: {usage.free} bytes free, "
                f"minimum {required_bytes} bytes required."
            )
        return usage.free

    def handle(self, *args, **options):
        fmt = str(options.get("format") or "json").strip().lower()
        if fmt not in ("json", "csv"):
            raise CommandError(f"Unsupported backup format: {fmt}")
        output_dir = Path(str(options.get("output_dir") or "backups").strip())
        custom_name = str(options.get("filename") or "").strip()
        quiet = bool(options.get("quiet"))
        retention_days = int(options.get("retention_days") or 0)
        encrypt = bool(options.get("encrypt"))
        if encrypt:
            get_fernet()

        free_bytes = self._check_disk_space(output_dir)

        try:
            content, mime_type, default_name = build_backup_payload(fmt=fmt)
        except Exception as exc:
            raise CommandError(f"Backup payload generation failed: {exc}") from exc

        data = content.encode("utf-8")
        if encrypt:
            data = encrypt_bytes(data)
        payload_bytes = len(data)
        if free_bytes < payload_bytes + (5 * 1024 * 1024):
            raise CommandError(
                f"Insufficient disk space for {payload_bytes} byte backup in {output_dir}."
            )

        target_name = custom_name if custom_name else default_name
        if encrypt and not target_name.endswith(".enc"):
            target_name = f"{target_name}.enc"
        target_path = output_dir / target_name
        temp_path = output_dir / f"{target_name}.tmp.{int(time.time())}"

        try:
            temp_path.write_bytes(data)
            if temp_path.stat().st_size == 0 and len(data) > 0:
                raise CommandError("Backup file write resulted in 0 bytes.")
            temp_path.replace(target_path)
        except Exception as exc:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            if isinstance(exc, CommandError):
                raise
            raise CommandError(f"Failed to write backup to {output_dir}: {exc}") from exc

        digest = hashlib.sha256(target_path.read_bytes()).hexdigest()
        checksum_path = output_dir / f"{target_name}.sha256"
        try:
            checksum_path.write_text(f"{digest}  {target_name}\n", encoding="utf-8")
        except OSError as exc:
            raise CommandError(f"Failed to write checksum manifest {checksum_path}: {exc}") from exc

        if not quiet:
            byte_size = target_path.stat().st_size
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully generated {fmt.upper()} backup{' (encrypted)' if encrypt else ''} ({byte_size} bytes): {target_path.resolve()}"
                )
            )
            self.stdout.write(self.style.SUCCESS(f"SHA-256: {digest} ({checksum_path.name})"))

        purged_count = 0
        if retention_days > 0 and output_dir.exists():
            cutoff_ts = time.time() - (retention_days * 86400)
            for file_item in output_dir.glob("edupredict_backup_*"):
                try:
                    if file_item.is_file() and file_item.stat().st_mtime < cutoff_ts:
                        file_item.unlink()
                        purged_count += 1
                except OSError:
                    pass
            if not quiet and purged_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Purged {purged_count} backup file(s) exceeding {retention_days} days retention."
                    )
                )

        return str(target_path.resolve())
