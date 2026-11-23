import django
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

MAX_SUBJECTS = 10  # BR-07
MIN_OVERLAP_MINUTES = 30  # BR-11


def check_constraint(condition, name):
    """CheckConstraint that works on Django 5.0 (check=) and 5.1+ (condition=)."""
    if django.VERSION >= (5, 1):
        return models.CheckConstraint(condition=condition, name=name)
    return models.CheckConstraint(check=condition, name=name)


class Subject(models.Model):
    """Catalog of subjects (SDD: subjects). Managed by administrators."""

    subject_code = models.CharField(max_length=20, unique=True)
    subject_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="UserSubject", related_name="subjects", blank=True
    )

    class Meta:
        ordering = ["subject_code"]

    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"


class UserSubject(models.Model):
    """Subjects a student wants to study (SDD: user_subjects, many-to-many link)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="user_subjects")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "subject"], name="unique_user_subject")]

    def __str__(self):
        return f"{self.user} - {self.subject}"


class AvailabilitySlot(models.Model):
    """Weekly time window when a student is free (SDD: availability_slots)."""

    class Day(models.IntegerChoices):
        MONDAY = 1, "Monday"
        TUESDAY = 2, "Tuesday"
        WEDNESDAY = 3, "Wednesday"
        THURSDAY = 4, "Thursday"
        FRIDAY = 5, "Friday"
        SATURDAY = 6, "Saturday"
        SUNDAY = 7, "Sunday"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability_slots")
    day_of_week = models.PositiveSmallIntegerField(choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["day_of_week", "start_time"]
        constraints = [check_constraint(Q(end_time__gt=F("start_time")), "slot_end_after_start")]

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time:%H:%M}-{self.end_time:%H:%M}"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "The end time must be later than the start time."})  # BR-09
        if self.user_id and self.day_of_week and self.start_time and self.end_time:
            overlapping = AvailabilitySlot.objects.filter(
                user_id=self.user_id,
                day_of_week=self.day_of_week,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError("This time slot overlaps with another slot on the same day.")  # BR-09


class StudyPreference(models.Model):
    """How a student likes to study (SDD: study_preferences). One per student (BR-10)."""

    class Style(models.TextChoices):
        DISCUSSION = "DISCUSSION", "Discussion"
        PRACTICE_PROBLEMS = "PRACTICE_PROBLEMS", "Practice problems"
        QUIET_REVIEW = "QUIET_REVIEW", "Quiet review"
        MIXED = "MIXED", "Mixed"

    class Venue(models.TextChoices):
        LIBRARY = "LIBRARY", "Library"
        CLASSROOM = "CLASSROOM", "Classroom"
        CAFETERIA = "CAFETERIA", "Cafeteria"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_preference")
    study_style = models.CharField(max_length=20, choices=Style.choices)
    preferred_group_size = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2), MaxValueValidator(8)], help_text="Between 2 and 8 people."
    )
    preferred_venue = models.CharField(max_length=12, choices=Venue.choices)

    def __str__(self):
        return f"Preferences of {self.user}"


