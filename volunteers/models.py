from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from django.utils import timezone

from .utils import generate_short_name


class VolunteerProfile(models.Model):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="volunteer_profile")
    volunteer_id = models.PositiveIntegerField(unique=True)
    short_name = models.CharField(max_length=30, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    geo_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geo_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        name = self.user.full_name
        return f"{self.volunteer_id} - {name}" if name else str(self.volunteer_id)

    def save(self, *args, **kwargs):
        if not self.volunteer_id:
            max_id = self.__class__.objects.aggregate(Max("volunteer_id")).get("volunteer_id__max") or 0
            self.volunteer_id = max_id + 1
        if self.user_id:
            self.short_name = generate_short_name(self.user.first_name)
        super().save(*args, **kwargs)


class VolunteerConstraint(models.Model):
    volunteer = models.OneToOneField(VolunteerProfile, on_delete=models.CASCADE, related_name="constraints")
    max_days_per_week = models.PositiveSmallIntegerField(null=True, blank=True)
    max_expeditions_per_week = models.PositiveSmallIntegerField(null=True, blank=True)
    max_expeditions_per_day = models.PositiveSmallIntegerField(null=True, blank=True)
    max_wait_hours = models.PositiveSmallIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Contraintes {self.volunteer.volunteer_id}"


class Availability(models.Model):
    volunteer = models.ForeignKey(VolunteerProfile, on_delete=models.CASCADE, related_name="availabilities")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self) -> str:
        return f"{self.volunteer.volunteer_id} {self.date} {self.start_time}-{self.end_time}"

    def clean(self) -> None:
        if self.start_time >= self.end_time:
            raise ValidationError("L'heure de fin doit etre apres l'heure de debut.")

        overlaps = Availability.objects.filter(
            volunteer=self.volunteer,
            date=self.date,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)
        if overlaps.exists():
            raise ValidationError("Cette plage horaire chevauche une disponibilite existante.")


class Unavailability(models.Model):
    volunteer = models.ForeignKey(VolunteerProfile, on_delete=models.CASCADE, related_name="unavailabilities")
    date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["volunteer", "date"], name="unique_unavailability_per_day"),
        ]
        ordering = ["date"]

    def __str__(self) -> str:
        return f"Indisponible {self.volunteer.volunteer_id} {self.date}"
