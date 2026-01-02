from datetime import time

from django import forms

from accounts.models import User
from .models import Availability, VolunteerConstraint, VolunteerProfile

MIN_TIME = time(7, 0)
MAX_TIME = time(22, 0)
TIME_CHOICES = [("", "--:--")]
for hour in range(7, 23):
    for minute in (0, 15, 30, 45):
        if hour == 22 and minute > 0:
            continue
        value = f"{hour:02d}:{minute:02d}:00"
        label = f"{hour:02d}:{minute:02d}"
        TIME_CHOICES.append((value, label))
TIME_SELECT_WIDGET = forms.Select(choices=TIME_CHOICES)


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]
        labels = {
            "email": "Mail",
            "first_name": "Prenom",
            "last_name": "Nom",
        }
        widgets = {
            "email": forms.EmailInput(attrs={"type": "email"}),
        }


class VolunteerProfileForm(forms.ModelForm):
    class Meta:
        model = VolunteerProfile
        fields = ["short_name", "phone"]
        labels = {
            "short_name": "Prenom court",
            "phone": "Telephone",
        }


class VolunteerConstraintForm(forms.ModelForm):
    class Meta:
        model = VolunteerConstraint
        fields = [
            "max_days_per_week",
            "max_expeditions_per_week",
            "max_expeditions_per_day",
            "max_wait_hours",
        ]
        labels = {
            "max_days_per_week": "Nombre de jours max / semaine",
            "max_expeditions_per_week": "Nombre de mises a bord max / semaine",
            "max_expeditions_per_day": "Nombre de mises a bord max / jour",
            "max_wait_hours": "Attente max (heures)",
        }


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ["date", "start_time", "end_time"]
        labels = {
            "date": "Date",
            "start_time": "Heure premier vol",
            "end_time": "Heure dernier vol",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": TIME_SELECT_WIDGET,
            "end_time": TIME_SELECT_WIDGET,
        }

    def __init__(self, *args, volunteer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.volunteer = volunteer
        if volunteer is not None:
            self.instance.volunteer = volunteer
        self.fields["start_time"].input_formats = ["%H:%M", "%H:%M:%S"]
        self.fields["end_time"].input_formats = ["%H:%M", "%H:%M:%S"]

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get("date")
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if not date or not start or not end:
            return cleaned
        if start.minute % 15 != 0:
            self.add_error("start_time", "Les minutes doivent etre par tranche de 15 minutes.")
        if end.minute % 15 != 0:
            self.add_error("end_time", "Les minutes doivent etre par tranche de 15 minutes.")
        if start < MIN_TIME or start > MAX_TIME:
            self.add_error("start_time", "L'heure doit etre entre 07:00 et 22:00.")
        if end < MIN_TIME or end > MAX_TIME:
            self.add_error("end_time", "L'heure doit etre entre 07:00 et 22:00.")
        if self.errors:
            return cleaned
        if start >= end:
            raise forms.ValidationError("L'heure de fin doit etre apres l'heure de debut.")

        if self.volunteer:
            overlaps = Availability.objects.filter(
                volunteer=self.volunteer,
                date=date,
                start_time__lt=end,
                end_time__gt=start,
            )
            if self.instance.pk:
                overlaps = overlaps.exclude(pk=self.instance.pk)
            if overlaps.exists():
                raise forms.ValidationError("Cette plage horaire chevauche une disponibilite existante.")

        return cleaned


class AvailabilityWeekForm(forms.Form):
    availability = forms.ChoiceField(
        choices=[("unavailable", "Indisponible"), ("available", "Disponible")],
        widget=forms.RadioSelect,
        initial="unavailable",
    )
    date = forms.DateField(widget=forms.HiddenInput)
    start_time = forms.TimeField(
        required=False,
        widget=TIME_SELECT_WIDGET,
    )
    end_time = forms.TimeField(
        required=False,
        widget=TIME_SELECT_WIDGET,
    )

    def __init__(self, *args, volunteer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.volunteer = volunteer
        self.day_label = ""
        self.fields["start_time"].input_formats = ["%H:%M", "%H:%M:%S"]
        self.fields["end_time"].input_formats = ["%H:%M", "%H:%M:%S"]

    def clean(self):
        cleaned = super().clean()
        availability = cleaned.get("availability")
        date = cleaned.get("date")
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")

        if availability != "available":
            cleaned["start_time"] = None
            cleaned["end_time"] = None
            return cleaned

        missing = False
        if not start:
            self.add_error("start_time", "Champ obligatoire.")
            missing = True
        if not end:
            self.add_error("end_time", "Champ obligatoire.")
            missing = True
        if missing:
            return cleaned

        if start.minute % 15 != 0:
            self.add_error("start_time", "Les minutes doivent etre par tranche de 15 minutes.")
        if end.minute % 15 != 0:
            self.add_error("end_time", "Les minutes doivent etre par tranche de 15 minutes.")
        if start < MIN_TIME or start > MAX_TIME:
            self.add_error("start_time", "L'heure doit etre entre 07:00 et 22:00.")
        if end < MIN_TIME or end > MAX_TIME:
            self.add_error("end_time", "L'heure doit etre entre 07:00 et 22:00.")
        if self.errors:
            return cleaned
        if start >= end:
            self.add_error("end_time", "L'heure de fin doit etre apres l'heure de debut.")
            return cleaned

        if self.volunteer and date:
            overlaps = Availability.objects.filter(
                volunteer=self.volunteer,
                date=date,
                start_time__lt=end,
                end_time__gt=start,
            )
            if overlaps.exists():
                raise forms.ValidationError("Cette plage horaire chevauche une disponibilite existante.")

        return cleaned
