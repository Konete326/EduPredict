from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from core.backup_crypto import decrypt_bytes


class Command(BaseCommand):
    help = "Decrypt an encrypted .enc backup into a plain backup file using BACKUP_ENCRYPTION_KEY."

    def add_arguments(self, parser):
        parser.add_argument("encrypted_file", help="Path to the .enc backup file.")
        parser.add_argument(
            "--output",
            default="",
            help="Output path for the decrypted file (default: same name without .enc).",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace the output file if it already exists.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress informational stdout output.",
        )

    def handle(self, *args, **options):
        source = Path(str(options["encrypted_file"]).strip())
        quiet = bool(options.get("quiet"))
        if not source.is_file():
            raise CommandError(f"Encrypted backup not found: {source}")
        if source.suffix != ".enc" and not options.get("output"):
            raise CommandError("Input is not a .enc file; pass --output to choose a target path.")

        output_value = str(options.get("output") or "").strip()
        target = Path(output_value) if output_value else source.with_suffix("")
        if target.resolve() == source.resolve():
            raise CommandError("Output path must differ from the encrypted input file.")
        if target.exists() and not options.get("overwrite"):
            raise CommandError(f"Output file already exists: {target}. Use --overwrite to replace it.")

        plain = decrypt_bytes(source.read_bytes())
        temp_path = target.with_name(f"{target.name}.tmp")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_bytes(plain)
            temp_path.replace(target)
        except OSError as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise CommandError(f"Failed to write decrypted backup to {target}: {exc}") from exc

        if not quiet:
            self.stdout.write(self.style.SUCCESS(f"Decrypted {source.name} -> {target} ({len(plain)} bytes)"))
        return str(target.resolve())
