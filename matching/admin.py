from django.contrib import admin

from .models import AvailabilitySlot, StudyPreference, Subject, UserSubject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("subject_code", "subject_name", "is_active")
    search_fields = ("subject_code", "subject_name")


@admin.register(UserSubject)
class UserSubjectAdmin(admin.ModelAdmin):
    list_display = ("user", "subject", "added_at")


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ("user", "day_of_week", "start_time", "end_time")


@admin.register(StudyPreference)
class StudyPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "study_style", "preferred_group_size", "preferred_venue")


