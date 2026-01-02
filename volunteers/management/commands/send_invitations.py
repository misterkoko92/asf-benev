import os

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.models import User


class Command(BaseCommand):
    help = "Envoie un email d'invitation avec lien de creation de mot de passe."

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            default=None,
            help="Domaine public (ex: asf-benev.onrender.com)",
        )
        parser.add_argument(
            "--protocol",
            default="https",
            help="Protocole (https par defaut)",
        )
        parser.add_argument(
            "--emails",
            nargs="*",
            help="Liste d'emails a cibler",
        )
        parser.add_argument(
            "--volunteer-ids",
            nargs="*",
            help="Liste d'identifiants benevoles a cibler",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afficher les emails sans envoyer",
        )

    def handle(self, *args, **options):
        domain = options["domain"] or os.getenv("RENDER_EXTERNAL_HOSTNAME")
        if not domain:
            raise CommandError("Le domaine est requis via --domain ou RENDER_EXTERNAL_HOSTNAME.")

        protocol = options["protocol"]
        emails = options.get("emails") or []
        volunteer_ids = options.get("volunteer_ids") or []

        users = User.objects.filter(is_active=True, volunteer_profile__isnull=False).select_related("volunteer_profile")
        if emails:
            users = users.filter(email__in=emails)
        if volunteer_ids:
            users = users.filter(volunteer_profile__volunteer_id__in=volunteer_ids)

        if not users.exists():
            self.stdout.write(self.style.WARNING("Aucun utilisateur a inviter."))
            return

        sent = 0
        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            path = reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
            invite_link = f"{protocol}://{domain}{path}"
            login_link = f"{protocol}://{domain}{reverse('login')}"
            display_name = user.full_name or user.email

            context = {
                "user": user,
                "display_name": display_name,
                "volunteer_id": user.volunteer_profile.volunteer_id,
                "invite_link": invite_link,
                "login_link": login_link,
            }
            subject = render_to_string("registration/invitation_email_subject.txt", context).strip()
            message = render_to_string("registration/invitation_email.txt", context)

            if options["dry_run"]:
                self.stdout.write(f"{user.email} -> {invite_link}")
                sent += 1
                continue

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Invitations traitees: {sent}"))
