"""Faculty account management (admin only)."""

from django.test import TestCase
from django.urls import reverse

from college.models import FacultyProfile

from .factories import (
    make_admin,
    make_department,
    make_faculty,
    make_student_user,
)


class FacultyAccessTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()

    def test_admin_can_open_the_faculty_list(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("faculty_list"))
        self.assertEqual(response.status_code, 200)

    def test_faculty_cannot_open_the_faculty_list(self):
        self.client.force_login(make_faculty())
        response = self.client.get(reverse("faculty_list"))
        self.assertEqual(response.status_code, 403)

    def test_a_student_cannot_open_the_faculty_list(self):
        self.client.force_login(make_student_user()[1])
        response = self.client.get(reverse("faculty_list"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_visitors_are_sent_to_the_login_page(self):
        response = self.client.get(reverse("faculty_list"))
        self.assertEqual(response.status_code, 302)


class FacultyCreateTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()
        self.client.force_login(self.admin)

    def payload(self, **overrides):
        data = {
            "first_name": "Meera",
            "last_name": "Iyer",
            "email": "meera@college.edu",
            "username": "meera",
            "employee_id": "EMP-042",
            "designation": "Associate Professor",
            "phone": "9876543210",
            "departments": [self.department.pk],
            "password1": "Faculty-pass-456",
            "password2": "Faculty-pass-456",
        }
        data.update(overrides)
        return data

    def test_admin_can_create_a_faculty_account(self):
        response = self.client.post(reverse("faculty_create"), self.payload())
        self.assertEqual(response.status_code, 302)

        profile = FacultyProfile.objects.get(employee_id="EMP-042")
        self.assertEqual(profile.user.username, "meera")
        self.assertEqual(profile.user.first_name, "Meera")
        self.assertTrue(profile.user.check_password("Faculty-pass-456"))
        self.assertEqual(list(profile.departments.all()), [self.department])
        self.assertIn("Faculty", [g.name for g in profile.user.groups.all()])

    def test_the_new_account_does_not_get_admin_rights(self):
        self.client.post(reverse("faculty_create"), self.payload())
        profile = FacultyProfile.objects.get(employee_id="EMP-042")
        self.assertFalse(profile.user.is_superuser)
        self.assertFalse(profile.user.is_staff)
        self.assertNotIn("Admin", [g.name for g in profile.user.groups.all()])

    def test_a_duplicate_username_is_rejected(self):
        make_faculty(username="meera", employee_id="EMP-100")
        response = self.client.post(reverse("faculty_create"), self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "username is already taken")
        self.assertFalse(FacultyProfile.objects.filter(employee_id="EMP-042").exists())

    def test_a_duplicate_employee_id_is_rejected(self):
        make_faculty(username="other", employee_id="EMP-042")
        response = self.client.post(reverse("faculty_create"), self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "employee ID is already in use")
        self.assertEqual(FacultyProfile.objects.count(), 1)

    def test_a_duplicate_email_is_rejected(self):
        make_faculty(username="other", employee_id="EMP-100", email="meera@college.edu")
        response = self.client.post(reverse("faculty_create"), self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FacultyProfile.objects.count(), 1)

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            reverse("faculty_create"), self.payload(password2="something-else")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "do not match")
        self.assertFalse(FacultyProfile.objects.filter(employee_id="EMP-042").exists())

    def test_a_faculty_member_cannot_create_an_account(self):
        self.client.force_login(make_faculty())
        response = self.client.post(reverse("faculty_create"), self.payload())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(FacultyProfile.objects.filter(employee_id="EMP-042").exists())


class FacultyUpdateTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()
        self.other = make_department(code="CSE", name="Computer Science")
        self.user = make_faculty(departments=[self.department])
        self.profile = self.user.faculty_profile
        self.client.force_login(self.admin)

    def test_admin_can_update_the_profile(self):
        response = self.client.post(
            reverse("faculty_update", args=[self.profile.pk]),
            {
                "employee_id": "EMP-042",
                "designation": "Professor",
                "phone": "9000000000",
                "first_name": "Meera",
                "last_name": "Iyer",
                "email": "meera@college.edu",
                "is_active": "on",
                "departments": [self.other.pk],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.designation, "Professor")
        self.assertEqual(list(self.profile.departments.all()), [self.other])
        self.assertEqual(self.profile.user.email, "meera@college.edu")

    def test_the_password_is_only_changed_when_a_new_one_is_given(self):
        self.client.post(
            reverse("faculty_update", args=[self.profile.pk]),
            {
                "employee_id": "EMP-001",
                "designation": "Lecturer",
                "phone": "",
                "first_name": "Faculty",
                "last_name": "Member",
                "email": "faculty@college.edu",
                "is_active": "on",
                "departments": [],
            },
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Faculty-pass-123"))

    def test_a_new_password_replaces_the_old_one(self):
        self.client.post(
            reverse("faculty_update", args=[self.profile.pk]),
            {
                "employee_id": "EMP-001",
                "designation": "Lecturer",
                "phone": "",
                "first_name": "Faculty",
                "last_name": "Member",
                "email": "faculty@college.edu",
                "is_active": "on",
                "departments": [],
                "new_password": "Another-pass-789",
            },
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Another-pass-789"))

    def test_the_account_can_be_deactivated(self):
        self.client.post(
            reverse("faculty_update", args=[self.profile.pk]),
            {
                "employee_id": "EMP-001",
                "designation": "Lecturer",
                "phone": "",
                "first_name": "Faculty",
                "last_name": "Member",
                "email": "faculty@college.edu",
                "departments": [],
            },
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)


class FacultyRoleTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.user = make_faculty()
        self.profile = self.user.faculty_profile
        self.client.force_login(self.admin)

    def test_an_account_can_be_promoted_to_admin(self):
        response = self.client.post(
            reverse("faculty_change_role", args=[self.profile.pk]), {"role": "Admin"}
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertIn("Admin", [g.name for g in self.user.groups.all()])
        self.assertNotIn("Faculty", [g.name for g in self.user.groups.all()])

    def test_an_account_can_be_moved_back_to_faculty(self):
        from django.contrib.auth.models import Group

        self.user.groups.add(Group.objects.get(name="Admin"))
        self.client.post(
            reverse("faculty_change_role", args=[self.profile.pk]), {"role": "Faculty"}
        )
        self.user.refresh_from_db()
        self.assertIn("Faculty", [g.name for g in self.user.groups.all()])
        self.assertNotIn("Admin", [g.name for g in self.user.groups.all()])

    def test_an_unknown_role_is_ignored(self):
        self.client.post(
            reverse("faculty_change_role", args=[self.profile.pk]), {"role": "Superuser"}
        )
        self.user.refresh_from_db()
        self.assertIn("Faculty", [g.name for g in self.user.groups.all()])
        self.assertNotIn("Admin", [g.name for g in self.user.groups.all()])

    def test_the_toggle_needs_a_post(self):
        response = self.client.get(reverse("faculty_toggle_active", args=[self.profile.pk]))
        self.assertEqual(response.status_code, 405)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_a_faculty_member_cannot_change_roles(self):
        other = make_faculty(username="other", employee_id="EMP-200")
        self.client.force_login(other)
        response = self.client.post(
            reverse("faculty_change_role", args=[self.profile.pk]), {"role": "Admin"}
        )
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertNotIn("Admin", [g.name for g in self.user.groups.all()])
