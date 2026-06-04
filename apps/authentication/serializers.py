from rest_framework import serializers
from .models import Session, OTPCode


# ─────────────────────────────────────────
#  Auth flows
# ─────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField()


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField(max_length=6, min_length=6)


class RefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


# ─────────────────────────────────────────
#  Session
# ─────────────────────────────────────────

class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = [
            "id",
            "user",
            "device_name",
            "ip_address",
            "status",
            "created_at",
            "expires_at",
            "last_used",
        ]
        read_only_fields = fields


class SessionListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Session
        fields = [
            "id",
            "device_name",
            "ip_address",
            "status",
            "created_at",
            "expires_at",
            "last_used",
        ]
        read_only_fields = fields


# ─────────────────────────────────────────
#  OTP
# ─────────────────────────────────────────

class OTPCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPCode
        fields = [
            "id",
            "user",
            "code",
            "created_at",
            "expires_at",
            "is_used",
        ]
        read_only_fields = fields


# ─────────────────────────────────────────
#  Admin filters
# ─────────────────────────────────────────

class AdminSessionFilterSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(
        choices=Session.Status.choices, required=False
    )
    ip_address = serializers.IPAddressField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
