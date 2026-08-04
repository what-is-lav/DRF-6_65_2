from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ["id", "email", "is_active"]
    list_editable = ["is_active"]
    list_display_links = ["id", "email"]

    # Страница редактирования существующего пользователя
    fieldsets = (
        ("User_info", {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("is_active", "is_staff", "last_login")}),
    )

    add_fieldsets = (
        (None, { "classes": ("wide",), "fields": ("email", "password1", "password2"),},),
    )

    ordering = ("email",)
    search_fields = ["email"]