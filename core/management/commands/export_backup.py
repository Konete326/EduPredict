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

        try:
            content, mime_type, default_name = build_backup_payload(fmt=fmt)
        except Exception as exc:
            raise CommandError(f"Backup payload generation failed: {exc}") from exc

        target_name = custom_name if custom_name else default_name
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            target_path = output_dir / target_name
            target_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise CommandError(f"Failed to write backup to {output_dir}: {exc}") from exc

        if not quiet:
            byte_size = target_path.stat().st_size
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully generated {fmt.upper()} backup ({byte_size} bytes): {target_path.resolve()}"
                )
            )

        return str(target_path.resolve())
