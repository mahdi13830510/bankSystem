from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):

    def create_user(self, phone, email, password=None, **extra_fields):

        if not phone:
            raise ValueError("Phone required")

        if not email:
            raise ValueError("Email required")

        user = self.model(
            phone=phone,
            email=self.normalize_email(email),
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, phone, email, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("primary_role", "admin")

        return self.create_user(phone, email, password, **extra_fields)