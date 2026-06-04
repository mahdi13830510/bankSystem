from django.utils import timezone
from rest_framework import serializers
from .models import User, UserProfile, UserDevice


# ─────────────────────────────────────────
#  Auth / Register
# ─────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "phone",
            "email",
            "password",
            "fullname",
            "national_code",
        ]


# ─────────────────────────────────────────
#  User — read
# ─────────────────────────────────────────

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "email",
            "fullname",
            "national_code",
            "status",
            "primary_role",
            "is_verified",
            "date_joined",
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    is_blocked = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        exclude = ["password"]


class MeSerializer(serializers.ModelSerializer):
    is_blocked = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "email",
            "fullname",
            "national_code",
            "status",
            "primary_role",
            "is_verified",
            "last_login",
            "date_joined",
            "is_blocked",
        ]


# ─────────────────────────────────────────
#  User — write
# ─────────────────────────────────────────

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return data


class AdminUserUpdateSerializer(serializers.Serializer):
    primary_role = serializers.ChoiceField(
        choices=User.Role.choices, required=False
    )
    status = serializers.ChoiceField(
        choices=User.Status.choices, required=False
    )
    is_staff = serializers.BooleanField(required=False)


class BlockUserSerializer(serializers.Serializer):
    blocked_until = serializers.DateTimeField(
        required=False,
        help_text="if it is empty> block forever",
    )
    reason = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )


class ChangeRoleSerializer(serializers.Serializer):
    primary_role = serializers.ChoiceField(choices=User.Role.choices)


# ─────────────────────────────────────────
#  Profile
# ─────────────────────────────────────────

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "address",
            "city",
            "postal_code",
            "birth_date",
            "avatar",
        ]
        read_only_fields = ["id", "user"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "address",
            "city",
            "postal_code",
            "birth_date",
            "avatar",
        ]


# ─────────────────────────────────────────
#  Device
# ─────────────────────────────────────────

class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = [
            "id",
            "device_name",
            "ip_address",
            "user_agent",
            "trusted",
            "last_used",
            "created_at",
        ]


# ─────────────────────────────────────────
#  Filter (Admin)
# ─────────────────────────────────────────

class AdminUserFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=User.Status.choices, required=False
    )
    primary_role = serializers.ChoiceField(
        choices=User.Role.choices, required=False
    )
    is_verified = serializers.BooleanField(required=False)
    search = serializers.CharField(
        required=False,
        help_text="search at fullname / phone / email / national_code"
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
