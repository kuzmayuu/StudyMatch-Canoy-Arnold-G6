from django import forms
from django.core.exceptions import ValidationError

from .models import (
    MAX_SUBJECTS,
    AvailabilitySlot,
    StudyPreference,
    Subject,
    UserSubject,
)


class SubjectForm(forms.ModelForm):
    """Administrators manage the subject catalog."""

    class Meta:
        model = Subject
        fields = ("subject_code", "subject_name", "is_active")
        labels = {"subject_code": "Subject code", "subject_name": "Subject name", "is_active": "Active (students can select it)"}

    def clean_subject_code(self):
        code = self.cleaned_data["subject_code"].strip().upper()
        if Subject.objects.filter(subject_code__iexact=code).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A subject with this code already exists.")
        return code


class AddSubjectForm(forms.Form):
    """A student adds a subject to their list (BR-07)."""

    subject = forms.ModelChoiceField(queryset=Subject.objects.none(), empty_label="Choose a subject...")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        chosen = UserSubject.objects.filter(user=user).values_list("subject_id", flat=True)
        self.fields["subject"].queryset = Subject.objects.filter(is_active=True).exclude(pk__in=chosen)

    def clean(self):
        cleaned = super().clean()
        if UserSubject.objects.filter(user=self.user).count() >= MAX_SUBJECTS:
            raise ValidationError(f"You can select at most {MAX_SUBJECTS} subjects. Remove one first.")
        return cleaned

    def save(self):
        return UserSubject.objects.create(user=self.user, subject=self.cleaned_data["subject"])


class AvailabilitySlotForm(forms.ModelForm):
    class Meta:
        model = AvailabilitySlot
        fields = ("day_of_week", "start_time", "end_time")
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }
        labels = {"day_of_week": "Day", "start_time": "From", "end_time": "To"}


class StudyPreferenceForm(forms.ModelForm):
    class Meta:
        model = StudyPreference
        fields = ("study_style", "preferred_group_size", "preferred_venue")
        labels = {
            "study_style": "How do you like to study?",
            "preferred_group_size": "Preferred group size",
            "preferred_venue": "Preferred place",
        }


