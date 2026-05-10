from rest_framework import serializers
from .models import User, UserProfile


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "phone",
            "email",
            "password",
            "fullname",
            "national_code"
        ]


class UserDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        exclude = ["password"]


class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        fields = "__all__"