import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cree un superuser si les variables d'environnement sont definies."

    def handle(self, *args, **options):
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        if not email or not password:
            self.stdout.write("Superuser ignore (variables manquantes).")
            return

        first_name = os.getenv("DJANGO_SUPERUSER_FIRST_NAME", "")
        last_name = os.getenv("DJANGO_SUPERUSER_LAST_NAME", "")

        User = get_user_model()
        existing = User.objects.filter(email=email).first()
        if existing:
            updated = False
            if not existing.is_staff:
                existing.is_staff = True
                updated = True
            if not existing.is_superuser:
                existing.is_superuser = True
                updated = True
            if updated:
                existing.save(update_fields=["is_staff", "is_superuser"])
                self.stdout.write("Superuser mis a jour.")
            else:
                self.stdout.write("Superuser deja present.")
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        self.stdout.write("Superuser cree.")
