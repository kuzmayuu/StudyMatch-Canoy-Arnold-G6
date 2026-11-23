from django.contrib import messages
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms import AddSubjectForm, AvailabilitySlotForm, StudyPreferenceForm, SubjectForm
from .models import AvailabilitySlot, StudyPreference, Subject, UserSubject

student_required = role_required(User.Role.STUDENT)
admin_required = role_required(User.Role.ADMIN)


# ---------------------------------------------------------------- Administrator: subject catalog (CRUD)
@admin_required
def subject_list(request):
    subjects = Subject.objects.annotate(student_count=Count("user_subjects")).order_by("subject_code")
    return render(request, "matching/subject_list.html", {"subjects": subjects})


@admin_required
def subject_create(request):
    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save()
            messages.success(request, f"{subject} was added to the catalog.")
            return redirect("matching:subject_list")
        messages.error(request, "Please fix the errors below and try again.")
    else:
        form = SubjectForm()
    return render(request, "matching/subject_form.html", {"form": form, "title": "Add subject"})


@admin_required
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, f"{subject} was updated.")
            return redirect("matching:subject_list")
        messages.error(request, "Please fix the errors below and try again.")
    else:
        form = SubjectForm(instance=subject)
    return render(request, "matching/subject_form.html", {"form": form, "title": f"Edit {subject.subject_code}"})


@admin_required
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        try:
            subject.delete()
            messages.success(request, f"{subject} was deleted.")
        except ProtectedError:
            messages.error(request, "This subject is used in match requests and cannot be deleted. Mark it inactive instead.")
        return redirect("matching:subject_list")
    return render(request, "matching/subject_confirm_delete.html", {"subject": subject})


# ---------------------------------------------------------------- Student: my subjects
@student_required
def my_subjects(request):
    if request.method == "POST":
        form = AddSubjectForm(request.POST, user=request.user)
        if form.is_valid():
            link = form.save()
            messages.success(request, f"{link.subject} was added to your subjects.")
            return redirect("matching:my_subjects")
        messages.error(request, "Could not add the subject. Please check the errors below.")
    else:
        form = AddSubjectForm(user=request.user)
    mine = UserSubject.objects.filter(user=request.user).select_related("subject").order_by("subject__subject_code")
    return render(request, "matching/my_subjects.html", {"form": form, "mine": mine})


@student_required
@require_POST
def my_subject_remove(request, pk):
    link = get_object_or_404(UserSubject, pk=pk, user=request.user)  # only your own records
    link.delete()
    messages.success(request, f"{link.subject} was removed from your subjects.")
    return redirect("matching:my_subjects")


# ---------------------------------------------------------------- Student: availability (CRUD)
@student_required
def availability_list(request):
    if request.method == "POST":
        form = AvailabilitySlotForm(request.POST, instance=AvailabilitySlot(user=request.user))
        if form.is_valid():
            form.save()
            messages.success(request, "Availability slot added.")
            return redirect("matching:availability_list")
        messages.error(request, "Could not add the slot. Please check the errors below.")
    else:
        form = AvailabilitySlotForm()
    slots = AvailabilitySlot.objects.filter(user=request.user)
    return render(request, "matching/availability_list.html", {"form": form, "slots": slots})


@student_required
def availability_edit(request, pk):
    slot = get_object_or_404(AvailabilitySlot, pk=pk, user=request.user)
    if request.method == "POST":
        form = AvailabilitySlotForm(request.POST, instance=slot)
        if form.is_valid():
            form.save()
            messages.success(request, "Availability slot updated.")
            return redirect("matching:availability_list")
        messages.error(request, "Please fix the errors below and try again.")
    else:
        form = AvailabilitySlotForm(instance=slot)
    return render(request, "matching/availability_form.html", {"form": form})


@student_required
@require_POST
def availability_delete(request, pk):
    slot = get_object_or_404(AvailabilitySlot, pk=pk, user=request.user)
    slot.delete()
    messages.success(request, "Availability slot deleted.")
    return redirect("matching:availability_list")


# ---------------------------------------------------------------- Student: study preferences
@student_required
def preferences(request):
    instance = StudyPreference.objects.filter(user=request.user).first() or StudyPreference(user=request.user)
    if request.method == "POST":
        form = StudyPreferenceForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Your study preferences were saved.")
            return redirect("matching:preferences")
        messages.error(request, "Please fix the errors below and try again.")
    else:
        form = StudyPreferenceForm(instance=instance)
    return render(request, "matching/preferences.html", {"form": form})


