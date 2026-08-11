import time
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def generate_user_report_task(user_id):
    print(f"[START] Генерация отчета для пользователя ID={user_id}...")
    time.sleep(5)  # Имитация длительной работы
    print(f"[SUCCESS] Отчет для ID={user_id} сформирован!")
    return f"Report_{user_id}_ready"



@shared_task
def cleanup_expired_codes_task():
    print("[CRONTAB] Запуск автоматической очистки устаревших данных в БД...")
    # Здесь логика удаления из БД/кэша
    print("[CRONTAB] Очистка успешно завершена!")
    return "Cleaned"


@shared_task(bind=True, max_retries=3)
def send_welcome_email_task(self, user_email, username):
    subject = "Добро пожаловать!"
    message = f"Привет, {username}! Твой аккаунт успешно создан."
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user_email],
            fail_silently=False,
        )
        print(f"[SMTP] Письмо отправлено на {user_email}")
    except Exception as exc:
        print(f"[SMTP ERROR] Ошибка отправки: {exc}. Повтор...")
        raise self.retry(exc=exc, countdown=60)