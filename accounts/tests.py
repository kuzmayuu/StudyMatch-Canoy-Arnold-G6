from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Profile, User

PASSWORD = "StudyPass123"


def make_student(email="juan@cit.edu", student_id="21-1234-567", **extra):
    return User.objects.create_user(
        email=email, password=PASSWORD, first_name="Juan", last_name="Dela Cruz", student_id_no=student_id, **extra
    )


def make_admin(email="admin@cit.edu"):
    return User.objects.create_superuser(email=email, password=PASSWORD, first_name="Ada", last_name="Admin")


def register_data(**overrides):
    data = {
        "first_name": "Maria",
        "last_name": "Santos",
        "student_id_no": "22-0001-111",
        "email": "maria@cit.edu",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data


@override_settings(ALLOWED_EMAIL_DOMAIN="cit.edu")
class RegistrationTests(TestCase):
    url = "/register/"

    def test_successful_registration(self):
        response = self.client.post(self.url, register_data())
        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(email="maria@cit.edu")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(Profile.objects.filter(user=user).exists())
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("created successfully" in m for m in messages))

    def test_password_is_hashed(self):
        self.client.post(self.url, register_data())
        user = User.objects.get(email="maria@cit.edu")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertTrue(user.check_password(PASSWORD))

    def test_required_fields(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        for field in ("first_name", "last_name", "student_id_no", "email", "password1", "password2"):
            self.assertIn(field, response.context["form"].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_invalid_email_format(self):
        response = self.client.post(self.url, register_data(email="not-an-email"))
        self.assertIn("email", response.context["form"].errors)

    def test_email_must_use_school_domain(self):
        response = self.client.post(self.url, register_data(email="maria@gmail.com"))
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        make_student(email="maria@cit.edu", student_id="21-9999-999")
        response = self.client.post(self.url, register_data(email="MARIA@cit.edu"))
        self.assertIn("email", response.context["form"].errors)

    def test_duplicate_student_id_is_rejected(self):
        make_student(student_id="22-0001-111")
        response = self.client.post(self.url, register_data())
        self.assertIn("student_id_no", response.context["form"].errors)

    def test_password_confirmation_must_match(self):
        response = self.client.post(self.url, register_data(password2="Different123"))
        self.assertIn("password2", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_password_needs_letter_and_number(self):
        response = self.client.post(self.url, register_data(password1="onlyletters", password2="onlyletters"))
        self.assertIn("password2", response.context["form"].errors)

    def test_short_password_is_rejected(self):
        response = self.client.post(self.url, register_data(password1="ab1", password2="ab1"))
        self.assertIn("password2", response.context["form"].errors)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.login_url = reverse("accounts:login")

    def test_student_login_goes_to_student_dashboard(self):
        response = self.client.post(self.login_url, {"email": "juan@cit.edu", "password": PASSWORD})
        self.assertRedirects(response, reverse("accounts:student_dashboard"))

    def test_admin_login_goes_to_admin_dashboard(self):
        make_admin()
        response = self.client.post(self.login_url, {"email": "admin@cit.edu", "password": PASSWORD})
        self.assertRedirects(response, reverse("accounts:admin_dashboard"))

    def test_invalid_credentials_show_error(self):
        response = self.client.post(self.login_url, {"email": "juan@cit.edu", "password": "WrongPass123"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_account_locks_after_five_failed_attempts(self):
        for _ in range(5):
            self.client.post(self.login_url, {"email": "juan@cit.edu", "password": "WrongPass123"})
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_locked())
        response = self.client.post(self.login_url, {"email": "juan@cit.edu", "password": PASSWORD})
        self.assertContains(response, "Too many failed login attempts")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_lock_expires(self):
        self.student.locked_until = timezone.now() - timedelta(minutes=1)
        self.student.save()
        response = self.client.post(self.login_url, {"email": "juan@cit.edu", "password": PASSWORD})
        self.assertRedirects(response, reverse("accounts:student_dashboard"))

    def test_suspended_account_cannot_log_in(self):
        self.student.status = User.Status.SUSPENDED
        self.student.save()
        response = self.client.post(self.login_url, {"email": "juan@cit.edu", "password": PASSWORD})
        self.assertContains(response, "suspended")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_ends_session(self):
        self.client.login(username="juan@cit.edu", password=PASSWORD)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, self.login_url)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        self.client.login(username="juan@cit.edu", password=PASSWORD)
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)


class ProtectedPageTests(TestCase):
    def test_logged_out_user_is_sent_to_login(self):
        for name in ("student_dashboard", "admin_dashboard", "profile", "profile_edit", "dashboard"):
            url = reverse(f"accounts:{name}")
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}", fetch_redirect_response=False)


class RoleAccessTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.admin = make_admin()

    def test_student_cannot_open_admin_dashboard(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse("accounts:admin_dashboard")).status_code, 403)

    def test_admin_cannot_open_student_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts:student_dashboard")).status_code, 403)

    def test_dashboard_redirects_by_role(self):
        self.client.force_login(self.student)
        self.assertRedirects(self.client.get(reverse("accounts:dashboard")), reverse("accounts:student_dashboard"))
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(reverse("accounts:dashboard")), reverse("accounts:admin_dashboard"))

    def test_student_cannot_suspend_users(self):
        other = make_student(email="other@cit.edu", student_id="21-5555-555")
        self.client.force_login(self.student)
        response = self.client.post(reverse("accounts:toggle_user_status", args=[other.pk]))
        self.assertEqual(response.status_code, 403)
        other.refresh_from_db()
        self.assertEqual(other.status, User.Status.ACTIVE)

    def test_admin_can_suspend_and_restore_student(self):
        self.client.force_login(self.admin)
        url = reverse("accounts:toggle_user_status", args=[self.student.pk])
        self.client.post(url)
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, User.Status.SUSPENDED)
        self.client.post(url)
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, User.Status.ACTIVE)


@override_settings(ALLOWED_EMAIL_DOMAIN="cit.edu")
class ProfileTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.other = make_student(email="other@cit.edu", student_id="21-5555-555")
        self.client.force_login(self.student)

    def update_data(self, **overrides):
        data = {
            "first_name": "Juan",
            "last_name": "Dela Cruz",
            "email": "juan@cit.edu",
            "program": "BS Information Technology",
            "year_level": "3",
            "contact_number": "0917 123 4567",
            "bio": "Loves studying with others.",
        }
        data.update(overrides)
        return data

    def test_view_own_profile(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "juan@cit.edu")
        self.assertNotContains(response, "other@cit.edu")

    def test_update_own_profile(self):
        response = self.client.post(reverse("accounts:profile_edit"), self.update_data())
        self.assertRedirects(response, reverse("accounts:profile"))
        self.student.refresh_from_db()
        profile = Profile.objects.get(user=self.student)
        self.assertEqual(profile.program, "BS Information Technology")
        self.assertEqual(profile.year_level, 3)

    def test_update_does_not_touch_other_users(self):
        self.client.post(reverse("accounts:profile_edit"), self.update_data())
        self.assertEqual(Profile.objects.get(user=self.other).program, "")

    def test_cannot_take_another_users_email(self):
        response = self.client.post(reverse("accounts:profile_edit"), self.update_data(email="other@cit.edu"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["user_form"].errors)

    def test_invalid_year_level_is_rejected(self):
        response = self.client.post(reverse("accounts:profile_edit"), self.update_data(year_level="9"))
        self.assertIn("year_level", response.context["profile_form"].errors)
