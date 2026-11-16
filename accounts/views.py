from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import LoginForm, ProfileUpdateForm, RegistrationForm, UserUpdateForm
from .models import Profile, User


def dashboard_name_for(user):
    """Name of the dashboard URL that matches the user's role."""
    return "accounts:admin_dashboard" if user.role == User.Role.ADMIN else "accounts:student_dashboard"


def home(request):
    if request.user.is_authenticated:
        return redirect(dashboard_name_for(request.user))
    return redirect("accounts:login")


def register_view(request):
    if request.user.is_authenticated:
        return redirect(dashboard_name_for(request.user))
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account was created successfully. You can now log in.")
            return redirect("accounts:login")
        messages.error(request, "Please fix the errors below and try again.")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(dashboard_name_for(request.user))
    if request.method == "POST":
        form = LoginForm(request, request.POST)
        if form.is_valid():
            login(request, form.user)
            messages.success(request, f"Welcome back, {form.user.first_name}!")
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect(dashboard_name_for(form.user))
    else:
        form = LoginForm(request)
    return render(request, "accounts/login.html", {"form": form, "next": request.GET.get("next", "")})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


@login_required
def dashboard_redirect(request):
    return redirect(dashboard_name_for(request.user))


@role_required(User.Role.STUDENT)
def student_dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "accounts/student_dashboard.html", {"profile": profile})


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    students = User.objects.filter(role=User.Role.STUDENT)
    context = {
        "total_students": students.count(),
        "active_students": students.filter(status=User.Status.ACTIVE).count(),
        "suspended_students": students.filter(status=User.Status.SUSPENDED).count(),
        "users": User.objects.exclude(pk=request.user.pk).order_by("-created_at")[:50],
    }
    return render(request, "accounts/admin_dashboard.html", context)


@role_required(User.Role.ADMIN)
@require_POST
def toggle_user_status(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target.pk == request.user.pk or target.role == User.Role.ADMIN:
        messages.error(request, "You cannot change the status of an administrator account.")
    elif target.status == User.Status.ACTIVE:
        target.status = User.Status.SUSPENDED
        target.save(update_fields=["status"])
        messages.success(request, f"{target.email} has been suspended.")
    else:
        target.status = User.Status.ACTIVE
        target.save(update_fields=["status"])
        messages.success(request, f"{target.email} has been restored.")
    return redirect("accounts:admin_dashboard")


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "accounts/profile.html", {"profile": profile})


@login_required
def profile_edit(request):
    # No user id in the URL: a user can only ever edit their own profile.
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile was updated successfully.")
            return redirect("accounts:profile")
        messages.error(request, "Please fix the errors below and try again.")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
    return render(request, "accounts/profile_edit.html", {"user_form": user_form, "profile_form": profile_form})
