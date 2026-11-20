import hashlib
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Verify a backup file against its SHA-256 sidecar manifest."

    def add_arguments(self, parser):
        parser.add_argument("backup_file", help="Path to the backup file to verify.")
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress informational stdout output.",
        )

    def handle(self, *args, **options):
        backup_path = Path(str(options["backup_file"]).strip())
        quiet = bool(options.get("quiet"))
        if not backup_path.is_file():
            raise CommandError(f"Backup file not found: {backup_path}")
        manifest_path = backup_path.with_name(f"{backup_path.name}.sha256")
        if not manifest_path.is_file():
            raise CommandError(f"Checksum manifest not found: {manifest_path}")

        manifest_text = manifest_path.read_text(encoding="utf-8").strip()
        expected = manifest_text.split()[0].lower() if manifest_text else ""
        if len(expected) != 64:
            raise CommandError(f"Checksum manifest is malformed: {manifest_path}")

        actual = hashlib.sha256(backup_path.read_bytes()).hexdigest()
        if actual != expected:
            raise CommandError(
                f"Checksum mismatch for {backup_path.name}: expected {expected}, got {actual}."
            )

        if not quiet:
            self.stdout.write(self.style.SUCCESS(f"OK: {backup_path.name} matches SHA-256 {actual}"))
        return actual
