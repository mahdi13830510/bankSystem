from .models import User


class UserService:

    @staticmethod
    def register_user(data):
        return User.objects.create_user(**data)

    @staticmethod
    def get_user(user_id):
        return User.objects.get(id=user_id)

    @staticmethod
    def block_user(user):
        user.status = "blocked"
        user.save()

    @staticmethod
    def verify_user(user):
        user.is_verified = True
        user.status = "active"
        user.save()

    @staticmethod
    def change_password(user, new_password):
        user.set_password(new_password)
        user.save()