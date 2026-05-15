import uuid


class ReferenceGenerator:

    @staticmethod
    def generate():
        return uuid.uuid4().hex.upper()