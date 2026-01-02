from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import IntegrationAvailabilityViewSet, IntegrationVolunteerViewSet, availabilities_csv, volunteers_csv

router = DefaultRouter()
router.register("integrations/volunteers", IntegrationVolunteerViewSet, basename="integration-volunteers")
router.register("integrations/availabilities", IntegrationAvailabilityViewSet, basename="integration-availabilities")

urlpatterns = [
    path("", include(router.urls)),
    path("integrations/volunteers.csv", volunteers_csv, name="integration-volunteers-csv"),
    path("integrations/availabilities.csv", availabilities_csv, name="integration-availabilities-csv"),
]
