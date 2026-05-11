from rest_framework import serializers


class LoginSerializer(serializers.Serializer):

    phone = serializers.CharField()
    password = serializers.CharField()


class VerifyOTPSerializer(serializers.Serializer):

    phone = serializers.CharField()
    code = serializers.CharField()


class RefreshSerializer(serializers.Serializer):

    refresh_token = serializers.CharField()