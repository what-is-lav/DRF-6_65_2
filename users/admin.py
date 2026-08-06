from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ["id", "email", "is_active"]
    list_editable = ["is_active"]
    list_display_links = ["id", "email"]

    fieldsets = (
        ("Users_info", {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("birthdate", "is_active", "is_staff", "last_login")}),
    )

    add_fieldsets = (
        (None, { "classes": ("wide",), "fields": ("email", "birthdate", "password1", "password2"),},),
    )

    ordering = ("email",)
    search_fields = ["email"]