from datetime import time, timedelta

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import MAX_SUBJECTS, AvailabilitySlot, StudyPreference, Subject, UserSubject

PASSWORD = "StudyPass123"


def make_student(n, **extra):
    return User.objects.create_user(
        email=f"s{n}@cit.edu",
        password=PASSWORD,
        first_name=f"First{n}",
        last_name=f"Last{n}",
        student_id_no=f"21-0000-{n:03d}",
        **extra,
    )


def make_admin():
    return User.objects.create_superuser(email="admin@cit.edu", password=PASSWORD, first_name="Ada", last_name="Admin")


def make_subject(code="IT317", name="Project Management"):
    return Subject.objects.create(subject_code=code, subject_name=name)


def add_slot(user, day=1, start="09:00", end="11:00"):
    return AvailabilitySlot.objects.create(
        user=user, day_of_week=day, start_time=time.fromisoformat(start), end_time=time.fromisoformat(end)
    )


def choose(user, subject):
    return UserSubject.objects.create(user=user, subject=subject)


class SubjectCatalogTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_student(1)

    def test_student_cannot_open_catalog(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse("matching:subject_list")).status_code, 403)

    def test_logged_out_user_is_sent_to_login(self):
        response = self.client.get(reverse("matching:subject_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_admin_creates_subject_with_uppercase_code(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("matching:subject_create"), {"subject_code": "it317", "subject_name": "Project Management", "is_active": "on"}
        )
        self.assertRedirects(response, reverse("matching:subject_list"))
        self.assertTrue(Subject.objects.filter(subject_code="IT317").exists())

    def test_duplicate_code_is_rejected(self):
        make_subject()
        self.client.force_login(self.admin)
        response = self.client.post(reverse("matching:subject_create"), {"subject_code": "it317", "subject_name": "Other"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("subject_code", response.context["form"].errors)

    def test_admin_edits_and_deletes_subject(self):
        subject = make_subject()
        self.client.force_login(self.admin)
        self.client.post(reverse("matching:subject_edit", args=[subject.pk]), {"subject_code": "IT317", "subject_name": "Renamed"})
        subject.refresh_from_db()
        self.assertEqual(subject.subject_name, "Renamed")
        self.assertFalse(subject.is_active)  # checkbox left unticked
        self.client.post(reverse("matching:subject_delete", args=[subject.pk]))
        self.assertFalse(Subject.objects.filter(pk=subject.pk).exists())


class MySubjectTests(TestCase):
    def setUp(self):
        self.student = make_student(1)
        self.other = make_student(2)
        self.subject = make_subject()
        self.client.force_login(self.student)

    def test_add_subject(self):
        response = self.client.post(reverse("matching:my_subjects"), {"subject": self.subject.pk})
        self.assertRedirects(response, reverse("matching:my_subjects"))
        self.assertTrue(UserSubject.objects.filter(user=self.student, subject=self.subject).exists())

    def test_same_subject_cannot_be_added_twice(self):
        choose(self.student, self.subject)
        response = self.client.post(reverse("matching:my_subjects"), {"subject": self.subject.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserSubject.objects.filter(user=self.student).count(), 1)

    def test_inactive_subject_cannot_be_added(self):
        self.subject.is_active = False
        self.subject.save()
        response = self.client.post(reverse("matching:my_subjects"), {"subject": self.subject.pk})
        self.assertEqual(UserSubject.objects.count(), 0)
        self.assertIn("subject", response.context["form"].errors)

    def test_maximum_subjects(self):
        for i in range(MAX_SUBJECTS):
            choose(self.student, make_subject(code=f"SUB{i}", name=f"Subject {i}"))
        extra = make_subject(code="EXTRA", name="One too many")
        response = self.client.post(reverse("matching:my_subjects"), {"subject": extra.pk})
        self.assertEqual(UserSubject.objects.filter(user=self.student).count(), MAX_SUBJECTS)
        self.assertEqual(response.status_code, 200)

    def test_remove_own_subject(self):
        link = choose(self.student, self.subject)
        self.client.post(reverse("matching:my_subject_remove", args=[link.pk]))
        self.assertFalse(UserSubject.objects.filter(pk=link.pk).exists())

    def test_cannot_remove_another_students_subject(self):
        link = choose(self.other, self.subject)
        response = self.client.post(reverse("matching:my_subject_remove", args=[link.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(UserSubject.objects.filter(pk=link.pk).exists())

    def test_admin_cannot_open_student_pages(self):
        self.client.force_login(make_admin())
        self.assertEqual(self.client.get(reverse("matching:my_subjects")).status_code, 403)


class AvailabilityTests(TestCase):
    def setUp(self):
        self.student = make_student(1)
        self.other = make_student(2)
        self.client.force_login(self.student)
        self.url = reverse("matching:availability_list")

    def post_slot(self, day=1, start="09:00", end="11:00"):
        return self.client.post(self.url, {"day_of_week": day, "start_time": start, "end_time": end})

    def test_add_slot(self):
        self.assertRedirects(self.post_slot(), self.url)
        self.assertEqual(AvailabilitySlot.objects.filter(user=self.student).count(), 1)

    def test_end_must_be_after_start(self):
        response = self.post_slot(start="11:00", end="09:00")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AvailabilitySlot.objects.count(), 0)

    def test_overlapping_slots_are_rejected(self):
        add_slot(self.student, 1, "09:00", "11:00")
        response = self.post_slot(start="10:00", end="12:00")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AvailabilitySlot.objects.filter(user=self.student).count(), 1)

    def test_back_to_back_slots_are_allowed(self):
        add_slot(self.student, 1, "09:00", "11:00")
        self.post_slot(start="11:00", end="12:00")
        self.assertEqual(AvailabilitySlot.objects.filter(user=self.student).count(), 2)

    def test_same_time_on_another_day_is_allowed(self):
        add_slot(self.student, 1, "09:00", "11:00")
        self.post_slot(day=2)
        self.assertEqual(AvailabilitySlot.objects.filter(user=self.student).count(), 2)

    def test_edit_own_slot(self):
        slot = add_slot(self.student)
        self.client.post(reverse("matching:availability_edit", args=[slot.pk]), {"day_of_week": 3, "start_time": "13:00", "end_time": "15:00"})
        slot.refresh_from_db()
        self.assertEqual(slot.day_of_week, 3)
        self.assertEqual(slot.start_time, time(13, 0))

    def test_edit_keeps_own_time_without_overlap_error(self):
        slot = add_slot(self.student, 1, "09:00", "11:00")
        self.client.post(reverse("matching:availability_edit", args=[slot.pk]), {"day_of_week": 1, "start_time": "09:00", "end_time": "12:00"})
        slot.refresh_from_db()
        self.assertEqual(slot.end_time, time(12, 0))

    def test_cannot_edit_or_delete_another_students_slot(self):
        slot = add_slot(self.other)
        self.assertEqual(self.client.get(reverse("matching:availability_edit", args=[slot.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("matching:availability_delete", args=[slot.pk])).status_code, 404)
        self.assertTrue(AvailabilitySlot.objects.filter(pk=slot.pk).exists())

    def test_delete_own_slot_requires_post(self):
        slot = add_slot(self.student)
        self.assertEqual(self.client.get(reverse("matching:availability_delete", args=[slot.pk])).status_code, 405)
        self.client.post(reverse("matching:availability_delete", args=[slot.pk]))
        self.assertFalse(AvailabilitySlot.objects.filter(pk=slot.pk).exists())

    def test_database_rejects_end_before_start(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AvailabilitySlot.objects.create(user=self.student, day_of_week=1, start_time=time(11), end_time=time(9))


class PreferenceTests(TestCase):
    def setUp(self):
        self.student = make_student(1)
        self.client.force_login(self.student)
        self.url = reverse("matching:preferences")

    def data(self, **overrides):
        data = {"study_style": "DISCUSSION", "preferred_group_size": 3, "preferred_venue": "LIBRARY"}
        data.update(overrides)
        return data

    def test_create_then_update_keeps_one_record(self):
        self.assertRedirects(self.client.post(self.url, self.data()), self.url)
        self.client.post(self.url, self.data(study_style="MIXED", preferred_group_size=5))
        self.assertEqual(StudyPreference.objects.filter(user=self.student).count(), 1)
        self.assertEqual(StudyPreference.objects.get(user=self.student).preferred_group_size, 5)

    def test_group_size_must_be_between_2_and_8(self):
        response = self.client.post(self.url, self.data(preferred_group_size=9))
        self.assertIn("preferred_group_size", response.context["form"].errors)
        self.assertEqual(StudyPreference.objects.count(), 0)


class DashboardPanelTests(TestCase):
    def test_student_dashboard_shows_matching_panel(self):
        student = make_student(1)
        self.client.force_login(student)
        response = self.client.get(reverse("accounts:student_dashboard"))
        self.assertContains(response, "Study partner matching")

    def test_admin_dashboard_shows_subject_panel(self):
        make_subject()
        self.client.force_login(make_admin())
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertContains(response, "Manage subjects")


