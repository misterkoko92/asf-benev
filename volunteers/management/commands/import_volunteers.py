import csv
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from volunteers.models import VolunteerConstraint, VolunteerProfile

try:
    import openpyxl
except ImportError:  # pragma: no cover - optional dependency
    openpyxl = None


HEADER_MAP = {
    "ID": "volunteer_id",
    "BENEVOLE": "full_name",
    "NOM": "last_name",
    "PRENOM": "first_name",
    "PRENOM_COURT": "short_name",
    "MAX_JOURS_SEMAINE": "max_days_per_week",
    "MAX_EXP_SEMAINE": "max_expeditions_per_week",
    "MAX_EXP_JOUR": "max_expeditions_per_day",
    "ATTENTE_MAX_H": "max_wait_hours",
    "TELEPHONE": "phone",
    "MAIL": "email",
    "EMAIL": "email",
}


def normalize_header(value):
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.upper().replace(" ", "_")


def parse_int(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def normalize_phone(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.replace(" ", "")


class Command(BaseCommand):
    help = "Importe des benevoles depuis un fichier CSV ou XLSX."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Chemin vers le fichier CSV ou XLSX")
        parser.add_argument("--update", action="store_true", help="Mettre a jour les benevoles existants")
        parser.add_argument("--dry-run", action="store_true", help="Afficher sans enregistrer")
        parser.add_argument(
            "--default-password",
            dest="default_password",
            default=None,
            help="Mot de passe par defaut pour les nouveaux comptes",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"Fichier introuvable: {path}")

        rows = self._load_rows(path)
        if not rows:
            raise CommandError("Aucune ligne detectee dans le fichier.")

        created = 0
        updated = 0
        skipped = 0

        with transaction.atomic():
            for row in rows:
                mapped = self._map_row(row)
                volunteer_id = parse_int(mapped.get("volunteer_id"))
                email = (mapped.get("email") or "").strip().lower()
                if not volunteer_id or not email:
                    skipped += 1
                    continue

                first_name = (mapped.get("first_name") or "").strip()
                last_name = (mapped.get("last_name") or "").strip()
                full_name = (mapped.get("full_name") or "").strip()
                if full_name and (not first_name or not last_name):
                    parts = full_name.split()
                    if len(parts) >= 2:
                        last_name = last_name or parts[0]
                        first_name = first_name or " ".join(parts[1:])
                    elif not first_name:
                        first_name = full_name

                profile = VolunteerProfile.objects.filter(volunteer_id=volunteer_id).select_related("user").first()
                was_existing = bool(profile)
                if profile:
                    if not options["update"]:
                        skipped += 1
                        continue
                    user = profile.user
                else:
                    user = User.objects.filter(email=email).first()

                if user and not profile:
                    profile = VolunteerProfile(user=user, volunteer_id=volunteer_id)

                if not user:
                    user = User.objects.create_user(
                        email=email,
                        password=options["default_password"],
                        first_name=first_name,
                        last_name=last_name,
                    )
                else:
                    user.first_name = first_name or user.first_name
                    user.last_name = last_name or user.last_name
                    user.email = email
                    user.save(update_fields=["first_name", "last_name", "email"])

                if not profile:
                    profile = VolunteerProfile(user=user, volunteer_id=volunteer_id)

                profile.short_name = mapped.get("short_name", "")
                profile.phone = normalize_phone(mapped.get("phone"))
                profile.save()

                constraints, _ = VolunteerConstraint.objects.get_or_create(volunteer=profile)
                constraints.max_days_per_week = parse_int(mapped.get("max_days_per_week"))
                constraints.max_expeditions_per_week = parse_int(mapped.get("max_expeditions_per_week"))
                constraints.max_expeditions_per_day = parse_int(mapped.get("max_expeditions_per_day"))
                constraints.max_wait_hours = parse_int(mapped.get("max_wait_hours"))
                constraints.save()

                if was_existing:
                    updated += 1
                else:
                    created += 1

            if options["dry_run"]:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Import termine. Crees: {created}, mis a jour: {updated}, ignores: {skipped}."
            )
        )

    def _load_rows(self, path: Path):
        if path.suffix.lower() == ".csv":
            with path.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                return list(reader)
        if path.suffix.lower() in {".xlsx", ".xlsm"}:
            if openpyxl is None:
                raise CommandError("openpyxl n'est pas installe. Ajoutez-le dans requirements.txt.")
            workbook = openpyxl.load_workbook(path, read_only=True)
            sheet = workbook.active
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                return []
            headers = [normalize_header(value) for value in rows[0]]
            data = []
            for row in rows[1:]:
                data.append({headers[i]: row[i] for i in range(len(headers))})
            return data
        raise CommandError("Format non supporte. Utilisez CSV ou XLSX.")

    def _map_row(self, row):
        mapped = {}
        for key, value in row.items():
            normalized = normalize_header(key)
            target = HEADER_MAP.get(normalized)
            if target:
                mapped[target] = value
        return mapped
