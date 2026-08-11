import time
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def generate_user_report_task(user_id):
    print(f"[START] генерация отчета для пользователя ID={user_id}...")
    time.sleep(5)  
    print(f"[SUCCESS] Отчет для ID={user_id} сформирован!")
    return f"Report_{user_id}_ready"



@shared_task
def cleanup_expired_codes_task():
    print("[CRONTAB] начало очистки ...")
    print("[CRONTAB] очистка успешно завершена!")
    return "Cleaned"


@shared_task(bind=True, max_retries=3)
def send_welcome_email_task(self, user_email, username):
    subject = "добро пожаловать!"
    message = f"Здравствуйте, {username}! ваш аккаунт успешно создан."
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user_email],
            fail_silently=False,
        )
        print(f"[SMTP] Письмо  было отправлено на {user_email}")
    except Exception as exc:
        print(f"[SMTP ERROR] Ошибка отправки: {exc}. Повторная попытка...")
        raise self.retry(exc=exc, countdown=60)