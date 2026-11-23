"""Panels that show the matching feature on the role dashboards."""
from django import template

from ..models import AvailabilitySlot, StudyPreference, Subject, UserSubject

register = template.Library()


@register.inclusion_tag("matching/_student_panel.html", takes_context=True)
def student_matching_panel(context):
    user = context["request"].user
    data = {
        "subject_count": UserSubject.objects.filter(user=user).count(),
        "slot_count": AvailabilitySlot.objects.filter(user=user).count(),
        "has_preference": StudyPreference.objects.filter(user=user).exists(),
    }
    data["ready"] = data["subject_count"] > 0 and data["slot_count"] > 0
    return data


@register.inclusion_tag("matching/_admin_panel.html")
def admin_matching_panel():
    data = {
        "subject_total": Subject.objects.count(),
        "subject_active": Subject.objects.filter(is_active=True).count(),
    }
    return data
