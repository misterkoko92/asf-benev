from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="volunteer-dashboard"),
    path("profile/", views.profile_view, name="volunteer-profile"),
    path("constraints/", views.constraints_view, name="volunteer-constraints"),
    path("availabilities/", views.availability_list, name="volunteer-availabilities"),
    path("availabilities/new/", views.availability_create, name="volunteer-availability-create"),
    path("availabilities/recap/", views.availability_recap, name="volunteer-availability-recap"),
    path("availabilities/<int:pk>/edit/", views.availability_update, name="volunteer-availability-edit"),
    path("availabilities/<int:pk>/delete/", views.availability_delete, name="volunteer-availability-delete"),
]
