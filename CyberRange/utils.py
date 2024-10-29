import random
import string


def generate_code() -> str:
    code = ''.join(random.sample(string.digits, 6))
    return code


def generate_classcode():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


