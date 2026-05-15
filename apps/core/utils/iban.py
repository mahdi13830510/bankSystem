import random
import string


class IBANGenerator:

    @staticmethod
    def generate(country_code="IR"):

        body = "".join(random.choices(string.digits, k=18))
        return f"{country_code}{body}"