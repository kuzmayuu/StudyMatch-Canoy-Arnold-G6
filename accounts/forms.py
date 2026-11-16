from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Profile, User
from .validators import validate_institutional_email

MAX_PHOTO_BYTES = 2 * 1024 * 1024  # 2 MB


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 8 characters, with at least one letter and one number.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "student_id_no", "email")
        labels = {"student_id_no": "Student ID number", "email": "CIT-U email"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name", "student_id_no", "email"):
            self.fields[name].required = True

    def clean_student_id_no(self):
        student_id = self.cleaned_data["student_id_no"].strip().upper()
        if User.objects.filter(student_id_no__iexact=student_id).exists():
            raise ValidationError("An account with this student ID number already exists.")
        return student_id

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        validate_institutional_email(email)
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", "The two passwords do not match.")
            else:
                candidate = User(
                    first_name=cleaned.get("first_name", ""),
                    last_name=cleaned.get("last_name", ""),
                    email=cleaned.get("email", ""),
                )
                try:
                    validate_password(password2, candidate)
                except ValidationError as error:
                    self.add_error("password2", error)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.set_password(self.cleaned_data["password1"])  # hashed, never plain text
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}))
    password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email = (cleaned.get("email") or "").strip().lower()
        password = cleaned.get("password")
        if not email or not password:
            return cleaned

        account = User.objects.filter(email__iexact=email).first()
        if account is not None and account.is_locked():
            minutes = max(1, int((account.locked_until - timezone.now()).total_seconds() // 60) + 1)
            raise ValidationError(
                f"Too many failed login attempts. Please try again in about {minutes} minute(s)."
            )

        user = authenticate(self.request, username=email, password=password)
        if user is None:
            if account is not None:
                if account.status != User.Status.ACTIVE and account.check_password(password):
                    raise ValidationError(
                        "This account is suspended or deactivated. Please contact an administrator."
                    )
                account.register_failed_login()
            raise ValidationError("Invalid email or password. Please try again.")

        user.reset_failed_logins()
        self.user = user
        return cleaned


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {"email": "CIT-U email"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        validate_institutional_email(email)
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Another account already uses this email address.")
        return email


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("program", "year_level", "contact_number", "bio", "profile_photo")
        labels = {"program": "Program / course", "profile_photo": "Profile photo"}
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"year_level": "1 to 5", "contact_number": "Example: 0917 123 4567"}

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo and hasattr(photo, "size") and photo.size > MAX_PHOTO_BYTES:
            raise ValidationError("The image is too large. Please upload a file under 2 MB.")
        return photo
