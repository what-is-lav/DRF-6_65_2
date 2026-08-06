from datetime import date
from rest_framework.exceptions import ValidationError

def validate_user_age_from_token(request):
    token_data = request.auth

    if not token_data or 'birthdate' not in token_data or not token_data['birthdate']:
        raise ValidationError("Укажите дату рождения, чтобы создать продукт.")
    try:
        birthdate = date.fromisoformat(token_data['birthdate'])
    except (ValueError, TypeError):
        raise ValidationError("Укажите дату рождения, чтобы создать продукт.")

    today = date.today()
    
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    if age < 18:
        raise ValidationError("Вам должно быть 18 лет, чтобы создать продукт.")