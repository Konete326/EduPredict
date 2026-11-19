import time
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from panels.admin_seed import build_backup_payload


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
            "--quiet",
            action="store_true",
            help="Suppress informational stdout output.",
        )

    def handle(self, *args, **options):
        fmt = str(options.get("format") or "json").strip().lower()
        if fmt not in ("json", "csv"):
            raise CommandError(f"Unsupported backup format: {fmt}")
        output_dir = Path(str(options.get("output_dir") or "backups").strip())
        custom_name = str(options.get("filename") or "").strip()
        quiet = bool(options.get("quiet"))
        retention_days = int(options.get("retention_days") or 0)

        try:
            content, mime_type, default_name = build_backup_payload(fmt=fmt)
        except Exception as exc:
            raise CommandError(f"Backup payload generation failed: {exc}") from exc

        target_name = custom_name if custom_name else default_name
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / target_name
        temp_path = output_dir / f"{target_name}.tmp.{int(time.time())}"

        try:
            temp_path.write_text(content, encoding="utf-8")
            if temp_path.stat().st_size == 0 and len(content) > 0:
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

        if not quiet:
            byte_size = target_path.stat().st_size
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully generated {fmt.upper()} backup ({byte_size} bytes): {target_path.resolve()}"
                )
            )

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
