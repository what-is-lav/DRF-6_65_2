import random
from django.core.cache import cache

def generate_and_save_code(user_id):
    code = str(random.randint(100000, 999999))
    key = f"confirm_code:{user_id}"
    cache.set(key, code, timeout=300)
    return code

def verify_and_delete_code(user_id, input_code):
    key = f"confirm_code:{user_id}"
    saved_code = cache.get(key)

    if saved_code is None:
        return False, "Срок действия кода истек."

    if saved_code != str(input_code):
        return False, " Код подтверждения неверный."

    cache.delete(key)
    return True, "Код подтвержден!."