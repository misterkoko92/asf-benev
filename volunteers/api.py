import csv
from datetime import datetime

from django.http import HttpResponse
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from .models import Availability, VolunteerConstraint, VolunteerProfile
from .serializers import AvailabilitySerializer, VolunteerProfileSerializer


class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IntegrationVolunteerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VolunteerProfileSerializer
    permission_classes = [IsStaffUser]

    def get_queryset(self):
        queryset = VolunteerProfile.objects.select_related("user", "constraints").all()
        volunteer_id = self.request.query_params.get("volunteer_id")
        if volunteer_id:
            queryset = queryset.filter(volunteer_id=volunteer_id)
        return queryset


class IntegrationAvailabilityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AvailabilitySerializer
    permission_classes = [IsStaffUser]

    def get_queryset(self):
        queryset = Availability.objects.select_related("volunteer", "volunteer__user")
        volunteer_id = self.request.query_params.get("volunteer_id")
        if volunteer_id:
            queryset = queryset.filter(volunteer__volunteer_id=volunteer_id)

        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            try:
                start_date = datetime.strptime(start, "%Y-%m-%d").date()
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                pass
        if end:
            try:
                end_date = datetime.strptime(end, "%Y-%m-%d").date()
                queryset = queryset.filter(date__lte=end_date)
            except ValueError:
                pass
        return queryset


@api_view(["GET"])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsStaffUser])
def volunteers_csv(_request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=volunteers.csv"
    writer = csv.writer(response)
    writer.writerow(
        [
            "volunteer_id",
            "first_name",
            "last_name",
            "short_name",
            "email",
            "phone",
            "max_days_per_week",
            "max_expeditions_per_week",
            "max_expeditions_per_day",
            "max_wait_hours",
        ]
    )
    for profile in VolunteerProfile.objects.select_related("user", "constraints").all():
        try:
            constraints = profile.constraints
        except VolunteerConstraint.DoesNotExist:
            constraints = None
        writer.writerow(
            [
                profile.volunteer_id,
                profile.user.first_name,
                profile.user.last_name,
                profile.short_name,
                profile.user.email,
                profile.phone,
                constraints.max_days_per_week if constraints else "",
                constraints.max_expeditions_per_week if constraints else "",
                constraints.max_expeditions_per_day if constraints else "",
                constraints.max_wait_hours if constraints else "",
            ]
        )
    return response


@api_view(["GET"])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsStaffUser])
def availabilities_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=availabilities.csv"
    writer = csv.writer(response)
    writer.writerow(["volunteer_id", "date", "start_time", "end_time"])
    queryset = Availability.objects.select_related("volunteer")

    volunteer_id = request.query_params.get("volunteer_id")
    if volunteer_id:
        queryset = queryset.filter(volunteer__volunteer_id=volunteer_id)
    start = request.query_params.get("start")
    end = request.query_params.get("end")
    if start:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            queryset = queryset.filter(date__gte=start_date)
        except ValueError:
            pass
    if end:
        try:
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
            queryset = queryset.filter(date__lte=end_date)
        except ValueError:
            pass

    for availability in queryset:
        writer.writerow(
            [
                availability.volunteer.volunteer_id,
                availability.date.isoformat(),
                availability.start_time.strftime("%H:%M"),
                availability.end_time.strftime("%H:%M"),
            ]
        )
    return response
