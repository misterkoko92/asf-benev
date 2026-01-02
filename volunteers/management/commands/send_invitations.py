import os

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.models import User
from volunteers.models import VolunteerProfile


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
        parser.add_argument(
            "--create-missing",
            action="store_true",
            help="Creer les comptes manquants (requiert --emails et --volunteer-ids).",
        )

    def handle(self, *args, **options):
        domain = options["domain"] or os.getenv("RENDER_EXTERNAL_HOSTNAME")
        if not domain:
            raise CommandError("Le domaine est requis via --domain ou RENDER_EXTERNAL_HOSTNAME.")

        def parse_volunteer_id(value):
            try:
                return int(value)
            except ValueError:
                raise CommandError(f"Identifiant benevole invalide: {value}")

        protocol = options["protocol"]
        emails = [email.strip().lower() for email in (options.get("emails") or []) if email.strip()]
        volunteer_ids = [value.strip() for value in (options.get("volunteer_ids") or []) if value.strip()]
        create_missing = options["create_missing"]
        dry_run = options["dry_run"]

        if create_missing and not emails:
            raise CommandError("--create-missing requiert --emails.")
        if create_missing and (not volunteer_ids or len(volunteer_ids) != len(emails)):
            raise CommandError("--create-missing requiert --volunteer-ids avec le meme nombre que --emails.")

        if volunteer_ids:
            volunteer_ids = [parse_volunteer_id(value) for value in volunteer_ids]

        volunteer_id_map = {}
        if emails and volunteer_ids and len(volunteer_ids) == len(emails):
            for email, volunteer_id in zip(emails, volunteer_ids):
                volunteer_id_map[email] = volunteer_id

        if dry_run:
            with transaction.atomic():
                sent = self._send_invites(protocol, domain, emails, volunteer_ids, volunteer_id_map, create_missing, True)
                transaction.set_rollback(True)
        else:
            sent = self._send_invites(protocol, domain, emails, volunteer_ids, volunteer_id_map, create_missing, False)

        if sent == 0:
            self.stdout.write(self.style.WARNING("Aucun utilisateur a inviter."))
            return

        self.stdout.write(self.style.SUCCESS(f"Invitations traitees: {sent}"))

    def _send_invites(self, protocol, domain, emails, volunteer_ids, volunteer_id_map, create_missing, dry_run):
        users = []
        seen_emails = set()

        def get_profile(user):
            try:
                return user.volunteer_profile
            except VolunteerProfile.DoesNotExist:
                return None

        if emails:
            for email in emails:
                if email in seen_emails:
                    continue
                seen_emails.add(email)

                user = (
                    User.objects.filter(email__iexact=email)
                    .select_related("volunteer_profile")
                    .first()
                )
                profile = get_profile(user) if user else None
                if user and profile:
                    expected_id = volunteer_id_map.get(email)
                    if expected_id and profile.volunteer_id != expected_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"{email}: volunteer_id attendu {expected_id} mais trouve {profile.volunteer_id}."
                            )
                        )
                    users.append(user)
                    continue

                if user and create_missing and not profile:
                    volunteer_id = volunteer_id_map.get(email)
                    if not volunteer_id:
                        self.stdout.write(self.style.WARNING(f"{email}: volunteer_id manquant."))
                        continue
                    if VolunteerProfile.objects.filter(volunteer_id=volunteer_id).exists():
                        self.stdout.write(self.style.WARNING(f"{email}: volunteer_id {volunteer_id} deja utilise."))
                        continue
                    VolunteerProfile.objects.create(user=user, volunteer_id=volunteer_id)
                    user.refresh_from_db()
                    users.append(user)
                    continue

                if not create_missing:
                    self.stdout.write(self.style.WARNING(f"{email}: utilisateur introuvable."))
                    continue

                volunteer_id = volunteer_id_map.get(email)
                if not volunteer_id:
                    self.stdout.write(self.style.WARNING(f"{email}: volunteer_id manquant."))
                    continue
                if VolunteerProfile.objects.filter(volunteer_id=volunteer_id).exists():
                    self.stdout.write(self.style.WARNING(f"{email}: volunteer_id {volunteer_id} deja utilise."))
                    continue

                user = User.objects.create_user(email=email, password=None)
                VolunteerProfile.objects.create(user=user, volunteer_id=volunteer_id)
                user.refresh_from_db()
                users.append(user)
        else:
            users = list(
                User.objects.filter(is_active=True, volunteer_profile__isnull=False)
                .select_related("volunteer_profile")
            )
            if volunteer_ids:
                users = [user for user in users if user.volunteer_profile.volunteer_id in volunteer_ids]

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

            if dry_run:
                self.stdout.write(f"{user.email} -> {invite_link}")
                sent += 1
                continue

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
            sent += 1

        return sent
