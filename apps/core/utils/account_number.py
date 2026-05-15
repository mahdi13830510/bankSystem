import random


class AccountNumberGenerator:

    @staticmethod
    def generate():
        return str(random.randint(10**11, 10**12 - 1))