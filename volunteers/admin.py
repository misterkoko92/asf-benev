from django.contrib import admin

from .models import Availability, VolunteerConstraint, VolunteerProfile


class VolunteerConstraintInline(admin.StackedInline):
    model = VolunteerConstraint
    extra = 0
    can_delete = False


@admin.register(VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    list_display = ("volunteer_id", "user", "short_name", "phone")
    search_fields = ("volunteer_id", "user__email", "user__first_name", "user__last_name")
    inlines = [VolunteerConstraintInline]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("volunteer_id", "short_name")
        return ()


@admin.register(VolunteerConstraint)
class VolunteerConstraintAdmin(admin.ModelAdmin):
    list_display = (
        "volunteer",
        "max_days_per_week",
        "max_expeditions_per_week",
        "max_expeditions_per_day",
        "max_wait_hours",
    )
    search_fields = ("volunteer__volunteer_id", "volunteer__user__email")


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("volunteer", "date", "start_time", "end_time")
    list_filter = ("date",)
    search_fields = ("volunteer__volunteer_id", "volunteer__user__email")
