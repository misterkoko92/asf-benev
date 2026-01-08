import csv
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.exceptions import ValidationError

from .models import Availability, IntegrationDirection, IntegrationEvent, IntegrationStatus, VolunteerConstraint, VolunteerProfile
from .serializers import AvailabilitySerializer, IntegrationEventSerializer, IntegrationEventStatusSerializer, VolunteerProfileSerializer


class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        api_key = getattr(settings, "INTEGRATION_API_KEY", "").strip()
        request_key = request.headers.get("X-ASF-Integration-Key", "").strip()
        if api_key and request_key == api_key:
            return True
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


class IntegrationEventViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = IntegrationEventSerializer
    permission_classes = [IsStaffUser]
    queryset = IntegrationEvent.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        direction = (self.request.query_params.get("direction") or "").strip()
        if direction:
            queryset = queryset.filter(direction=direction)
        status_value = (self.request.query_params.get("status") or "").strip()
        if status_value:
            queryset = queryset.filter(status=status_value)
        source = (self.request.query_params.get("source") or "").strip()
        if source:
            queryset = queryset.filter(source=source)
        event_type = (self.request.query_params.get("event_type") or "").strip()
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        return queryset

    def get_serializer_class(self):
        if self.action in {"update", "partial_update"}:
            return IntegrationEventStatusSerializer
        return IntegrationEventSerializer

    def perform_create(self, serializer):
        source = (serializer.validated_data.get("source") or "").strip()
        if not source:
            source = (self.request.headers.get("X-ASF-Source") or "").strip()
        if not source:
            raise ValidationError({"source": "source is required"})
        target = (serializer.validated_data.get("target") or "").strip()
        if not target:
            target = (self.request.headers.get("X-ASF-Target") or "").strip()
        serializer.save(
            source=source,
            target=target,
            direction=IntegrationDirection.INBOUND,
            status=IntegrationStatus.PENDING,
        )

    def perform_update(self, serializer):
        status_value = serializer.validated_data.get("status")
        processed_at = serializer.validated_data.get("processed_at")
        if status_value == IntegrationStatus.PROCESSED and processed_at is None:
            serializer.save(processed_at=timezone.now())
        else:
            serializer.save()


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
