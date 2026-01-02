from collections import defaultdict
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Min
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AccountForm,
    AvailabilityForm,
    AvailabilityWeekForm,
    VolunteerConstraintForm,
    VolunteerProfileForm,
)
from .models import Availability, Unavailability, VolunteerConstraint, VolunteerProfile

DAY_NAMES = [
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
]


def _get_profile(user):
    try:
        return user.volunteer_profile
    except VolunteerProfile.DoesNotExist:
        return None


def _next_monday(today):
    days_ahead = (7 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _resolve_week_start(request):
    if request.method == "POST":
        value = request.POST.get("week_start")
        if value:
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                pass

    base = _next_monday(timezone.localdate())
    week_param = request.GET.get("week")
    year_param = request.GET.get("year")
    try:
        year_value = int(year_param) if year_param else base.isocalendar().year
    except ValueError:
        year_value = base.isocalendar().year

    if week_param:
        try:
            week_value = int(week_param)
            if 1 <= week_value <= 52:
                return date.fromisocalendar(year_value, week_value, 1)
        except ValueError:
            pass

    return base


@login_required
def dashboard(request):
    profile = _get_profile(request.user)
    if not profile:
        return render(request, "volunteers/missing_profile.html", status=400)

    recent_availabilities = profile.availabilities.order_by("-date", "-start_time")[:5]
    return render(
        request,
        "volunteers/dashboard.html",
        {
            "profile": profile,
            "recent_availabilities": recent_availabilities,
        },
    )


@login_required
def profile_view(request):
    profile = _get_profile(request.user)
    if not profile:
        return render(request, "volunteers/missing_profile.html", status=400)

    if request.method == "POST":
        account_form = AccountForm(request.POST, instance=request.user)
        profile_form = VolunteerProfileForm(request.POST, instance=profile)
        if account_form.is_valid() and profile_form.is_valid():
            account_form.save()
            profile_form.save()
            messages.success(request, "Coordonnees mises a jour.")
            return redirect("volunteer-profile")
    else:
        account_form = AccountForm(instance=request.user)
        profile_form = VolunteerProfileForm(instance=profile)

    return render(
        request,
        "volunteers/profile.html",
        {
            "profile": profile,
            "account_form": account_form,
            "profile_form": profile_form,
        },
    )


@login_required
def constraints_view(request):
    profile = _get_profile(request.user)
    if not profile:
        return render(request, "volunteers/missing_profile.html", status=400)

    constraints, _created = VolunteerConstraint.objects.get_or_create(volunteer=profile)
    if request.method == "POST":
        form = VolunteerConstraintForm(request.POST, instance=constraints)
        if form.is_valid():
            form.save()
            messages.success(request, "Contraintes mises a jour.")
            return redirect("volunteer-constraints")
    else:
        form = VolunteerConstraintForm(instance=constraints)

    return render(
        request,
        "volunteers/constraints.html",
        {"profile": profile, "form": form},
    )


@login_required
def availability_list(request):
    profile = _get_profile(request.user)
    if not profile:
        return render(request, "volunteers/missing_profile.html", status=400)

    availabilities = profile.availabilities.all()
    return render(
        request,
        "volunteers/availability_list.html",
        {"profile": profile, "availabilities": availabilities},
    )


@login_required
def availability_recap(request):
    week_start = _resolve_week_start(request)
    week_end = week_start + timedelta(days=6)
    week_meta = week_start.isocalendar()
    week_number = week_meta.week
    week_year = week_meta.year

    week_days = []
    for offset in range(7):
        day_date = week_start + timedelta(days=offset)
        week_days.append(
            {
                "date": day_date,
                "label": f"{DAY_NAMES[offset]} {day_date.strftime('%d/%m/%Y')}",
            }
        )

    week_options = []
    for week in range(1, 53):
        start = date.fromisocalendar(week_year, week, 1)
        end = start + timedelta(days=6)
        week_options.append(
            {
                "week": week,
                "start": start,
                "end": end,
                "label": f"Semaine {week} - du lundi {start.strftime('%d/%m/%Y')} au dimanche {end.strftime('%d/%m/%Y')}",
            }
        )

    availability_rows = (
        Availability.objects.filter(date__range=(week_start, week_end))
        .values("volunteer_id", "date")
        .annotate(start=Min("start_time"), end=Max("end_time"))
    )
    availability_map = defaultdict(dict)
    for row in availability_rows:
        availability_map[row["volunteer_id"]][row["date"]] = (row["start"], row["end"])

    unavailability_rows = Unavailability.objects.filter(date__range=(week_start, week_end)).values(
        "volunteer_id",
        "date",
    )
    unavailability_map = defaultdict(set)
    for row in unavailability_rows:
        unavailability_map[row["volunteer_id"]].add(row["date"])

    profiles = VolunteerProfile.objects.select_related("user").order_by("user__last_name", "user__first_name")
    recap_rows = []
    for profile in profiles:
        days = []
        for day in week_days:
            date_value = day["date"]
            availability = availability_map.get(profile.id, {}).get(date_value)
            if availability:
                start_time, end_time = availability
                days.append(
                    {
                        "status": "available",
                        "start": start_time.strftime("%Hh%M"),
                        "end": end_time.strftime("%Hh%M"),
                    }
                )
                continue
            if date_value in unavailability_map.get(profile.id, set()):
                days.append(
                    {
                        "status": "unavailable",
                        "start": "--",
                        "end": "--",
                    }
                )
                continue
            days.append(
                {
                    "status": "empty",
                    "start": "",
                    "end": "",
                }
            )
        recap_rows.append(
            {
                "name": profile.user.full_name,
                "days": days,
            }
        )

    return render(
        request,
        "volunteers/availability_recap.html",
        {
            "profile": _get_profile(request.user),
            "week_start": week_start,
            "week_end": week_end,
            "week_number": week_number,
            "week_year": week_year,
            "week_days": week_days,
            "week_options": week_options,
            "recap_rows": recap_rows,
        },
    )


@login_required
def availability_create(request):
    profile = _get_profile(request.user)
    if not profile:
        return render(request, "volunteers/missing_profile.html", status=400)

    week_start = _resolve_week_start(request)
    week_dates = [week_start + timedelta(days=offset) for offset in range(7)]
    day_labels = [
        f"{DAY_NAMES[index]} {date.strftime('%d/%m/%Y')}"
        for index, date in enumerate(week_dates)
    ]
    week_meta = week_start.isocalendar()
    week_number = week_meta.week
    week_year = week_meta.year
    week_end = week_start + timedelta(days=6)
    week_options = list(range(1, 53))

    AvailabilityWeekFormSet = formset_factory(AvailabilityWeekForm, extra=0)

    if request.method == "POST":
        formset = AvailabilityWeekFormSet(request.POST, form_kwargs={"volunteer": profile})
        if formset.is_valid():
            created = 0
            for form in formset:
                availability_choice = form.cleaned_data.get("availability")
                date_value = form.cleaned_data.get("date")
                if availability_choice != "available":
                    if date_value:
                        Availability.objects.filter(volunteer=profile, date=date_value).delete()
                        Unavailability.objects.update_or_create(volunteer=profile, date=date_value)
                    continue
                if date_value:
                    Availability.objects.filter(volunteer=profile, date=date_value).delete()
                    Unavailability.objects.filter(volunteer=profile, date=date_value).delete()
                Availability.objects.create(
                    volunteer=profile,
                    date=date_value,
                    start_time=form.cleaned_data["start_time"],
                    end_time=form.cleaned_data["end_time"],
                )
                created += 1
            if created:
                messages.success(request, f"{created} disponibilite(s) enregistree(s).")
            else:
                messages.success(request, "Aucune disponibilite enregistree.")
            return redirect("volunteer-availabilities")
    else:
        initial = [{"date": date, "availability": "unavailable"} for date in week_dates]
        formset = AvailabilityWeekFormSet(initial=initial, form_kwargs={"volunteer": profile})

    for form, day_label in zip(formset.forms, day_labels):
        form.day_label = day_label

    return render(
        request,
        "volunteers/availability_week_form.html",
        {
            "profile": profile,
            "formset": formset,
            "week_start": week_start,
            "week_number": week_number,
            "week_year": week_year,
            "week_end": week_end,
            "week_options": week_options,
            "title": "Ajouter une disponibilite",
        },
    )


@login_required
def availability_update(request, pk: int):
    profile = _get_profile(request.user)
    if not profile:
        return render(request, "volunteers/missing_profile.html", status=400)

    availability = get_object_or_404(Availability, pk=pk, volunteer=profile)
    if request.method == "POST":
        form = AvailabilityForm(request.POST, instance=availability, volunteer=profile)
        if form.is_valid():
            availability = form.save()
            Unavailability.objects.filter(volunteer=profile, date=availability.date).delete()
            messages.success(request, "Disponibilite mise a jour.")
            return redirect("volunteer-availabilities")
    else:
        form = AvailabilityForm(instance=availability, volunteer=profile)

    return render(
        request,
        "volunteers/availability_form.html",
        {"profile": profile, "form": form, "title": "Modifier une disponibilite"},
    )


@login_required
def availability_delete(request, pk: int):
    profile = _get_profile(request.user)
    if not profile:
        return render(request, "volunteers/missing_profile.html", status=400)

    availability = get_object_or_404(Availability, pk=pk, volunteer=profile)
    if request.method == "POST":
        availability.delete()
        messages.success(request, "Disponibilite supprimee.")
        return redirect("volunteer-availabilities")

    return render(
        request,
        "volunteers/availability_confirm_delete.html",
        {"profile": profile, "availability": availability},
    )
