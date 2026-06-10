import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Session


class JWTBearerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None

        token = header.split(" ", 1)[1]

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token expired")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid access token")

        if payload.get("type") != "access":
            raise AuthenticationFailed("Not an access token")

        session = (
            Session.objects
            .filter(access_token=token, status=Session.Status.ACTIVE)
            .select_related("user")
            .first()
        )
        if not session:
            raise AuthenticationFailed("Session not found or revoked")

        return (session.user, token)
