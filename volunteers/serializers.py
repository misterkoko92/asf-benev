from rest_framework import serializers

from .models import Availability, VolunteerConstraint, VolunteerProfile


class VolunteerConstraintSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerConstraint
        fields = [
            "max_days_per_week",
            "max_expeditions_per_week",
            "max_expeditions_per_day",
            "max_wait_hours",
        ]


class VolunteerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    full_name = serializers.SerializerMethodField()
    constraints = serializers.SerializerMethodField()

    class Meta:
        model = VolunteerProfile
        fields = [
            "volunteer_id",
            "first_name",
            "last_name",
            "full_name",
            "short_name",
            "email",
            "phone",
            "constraints",
        ]

    def get_full_name(self, obj):
        return obj.user.full_name

    def get_constraints(self, obj):
        try:
            constraints = obj.constraints
        except VolunteerConstraint.DoesNotExist:
            return None
        return VolunteerConstraintSerializer(constraints).data


class AvailabilitySerializer(serializers.ModelSerializer):
    volunteer_id = serializers.IntegerField(source="volunteer.volunteer_id")

    class Meta:
        model = Availability
        fields = ["volunteer_id", "date", "start_time", "end_time"]
