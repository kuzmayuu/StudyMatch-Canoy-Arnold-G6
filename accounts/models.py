from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)  # hashes the password
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Account table (SDD: users). Roles: STUDENT and ADMIN."""

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        ADMIN = "ADMIN", "Administrator"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        DEACTIVATED = "DEACTIVATED", "Deactivated"

    student_id_no = models.CharField(
        "student ID number",
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[RegexValidator(r"^[A-Za-z0-9-]{5,20}$", "Enter a valid student ID number (letters, numbers, dashes).")],
    )
    email = models.EmailField(max_length=100, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    is_staff = models.BooleanField(default=False)
    failed_login_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return self.email

    @property
    def is_active(self):
        # Django's auth backend refuses to log in users whose is_active is False (BR-05).
        return self.status == self.Status.ACTIVE

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.first_name

    # --- BR-04: lock after repeated failed logins ---
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def register_failed_login(self):
        self.failed_login_count += 1
        if self.failed_login_count >= settings.MAX_FAILED_LOGINS:
            self.locked_until = timezone.now() + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
            self.failed_login_count = 0
        self.save(update_fields=["failed_login_count", "locked_until"])

    def reset_failed_logins(self):
        if self.failed_login_count or self.locked_until:
            self.failed_login_count = 0
            self.locked_until = None
            self.save(update_fields=["failed_login_count", "locked_until"])


class Profile(models.Model):
    """Profile table (SDD: profiles). One profile per user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    program = models.CharField(max_length=100, blank=True)
    year_level = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    contact_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r"^\+?[0-9 ()-]{7,20}$", "Enter a valid contact number.")],
    )
    bio = models.CharField(max_length=300, blank=True)
    profile_photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.email}"

    @property
    def missing_fields(self):
        checks = [
            ("program", self.program),
            ("year level", self.year_level),
            ("contact number", self.contact_number),
            ("bio", self.bio),
            ("profile photo", self.profile_photo),
        ]
        return [label for label, value in checks if not value]

    @property
    def completion_percent(self):
        return int((5 - len(self.missing_fields)) / 5 * 100)
