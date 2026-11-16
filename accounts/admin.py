from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from .models import Profile, User


class AdminUserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "role")


class AdminUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    ordering = ("-created_at",)
    list_display = ("email", "first_name", "last_name", "role", "status", "student_id_no")
    list_filter = ("role", "status")
    search_fields = ("email", "first_name", "last_name", "student_id_no")
    readonly_fields = ("created_at", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "student_id_no")}),
        ("Role and status", {"fields": ("role", "status", "failed_login_count", "locked_until")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "role", "password1", "password2")}),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "program", "year_level", "contact_number")
    search_fields = ("user__email", "program")
