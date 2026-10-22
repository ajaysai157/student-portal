"""Management of the student login accounts (admin only)."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .factories import (
    make_admin,
    make_department,
    make_faculty,
    make_student,
    make_student_user,
)


class StudentAccountAccessTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_student(student_id="23A91A6001", name="Ravi Kumar")

    def test_admin_can_open_the_account_list(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("student_accounts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "23A91A6001")

    def test_faculty_cannot_open_the_account_list(self):
        self.client.force_login(make_faculty())
        response = self.client.get(reverse("student_accounts"))
        self.assertEqual(response.status_code, 403)

    def test_a_student_cannot_open_the_account_list(self):
        self.client.force_login(make_student_user()[1])
        response = self.client.get(reverse("student_accounts"))
        self.assertEqual(response.status_code, 403)


class StudentAccountCreateTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()
        self.student = make_student(student_id="23A91A6001", name="Ravi Kumar")
        self.client.force_login(self.admin)

    def payload(self, **overrides):
        data = {
            "student": self.student.pk,
            "username": "ravi",
            "email": "ravi@college.edu",
            "password1": "Student-pass-456",
            "password2": "Student-pass-456",
        }
        data.update(overrides)
        return data

    def test_admin_can_create_a_login_for_a_student(self):
        response = self.client.post(reverse("student_account_create"), self.payload())
        self.assertEqual(response.status_code, 302)

        self.student.refresh_from_db()
        self.assertIsNotNone(self.student.account)
        self.assertEqual(self.student.account.username, "ravi")
        self.assertTrue(self.student.account.check_password("Student-pass-456"))
        self.assertIn("Student", [g.name for g in self.student.account.groups.all()])

    def test_the_new_account_is_not_an_admin(self):
        self.client.post(reverse("student_account_create"), self.payload())
        self.student.refresh_from_db()
        self.assertFalse(self.student.account.is_superuser)
        self.assertFalse(self.student.account.is_staff)

    def test_a_student_that_already_has_an_account_is_not_offered(self):
        self.student.account = User.objects.create_user(username="ravi", password="x")
        self.student.save(update_fields=["account"])
        response = self.client.get(reverse("student_account_create"))
        self.assertNotContains(response, f'value="{self.student.pk}"')

    def test_a_duplicate_username_is_rejected(self):
        User.objects.create_user(username="ravi", password="x")
        response = self.client.post(reverse("student_account_create"), self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "username is already taken")
        self.assertIsNone(self.student.account)

    def test_a_username_that_is_a_student_id_is_rejected(self):
        response = self.client.post(
            reverse("student_account_create"), self.payload(username="23a91a6001")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already used as a student ID")

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            reverse("student_account_create"), self.payload(password2="other-pass")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "do not match")


class StudentAccountUpdateTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student, self.user = make_student_user(
            student_id="23A91A6001", name="Ravi Kumar", username="ravi"
        )
        self.client.force_login(self.admin)

    def test_admin_can_update_the_account(self):
        response = self.client.post(
            reverse("student_account_update", args=[self.student.pk]),
            {
                "username": "ravi.kumar",
                "email": "ravi@college.edu",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "ravi.kumar")
        self.assertEqual(self.user.email, "ravi@college.edu")

    def test_the_account_can_be_deactivated(self):
        self.client.post(
            reverse("student_account_update", args=[self.student.pk]),
            {"username": "ravi", "email": "ravi@college.edu"},
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_a_deactivated_student_cannot_sign_in(self):
        self.client.post(
            reverse("student_account_update", args=[self.student.pk]),
            {"username": "ravi", "email": "ravi@college.edu"},
        )
        self.client.logout()
        response = self.client.post(
            reverse("login"), {"username": "ravi", "password": "Student-pass-123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_a_student_without_an_account_is_redirected(self):
        student = make_student(student_id="23A91A6002", name="No Account")
        response = self.client.get(reverse("student_account_update", args=[student.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("student_accounts"))

    def test_an_account_can_be_unlinked(self):
        response = self.client.post(
            reverse("student_account_unlink", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertIsNone(self.student.account)
        # The student record itself is kept.
        self.assertTrue(
            type(self.student).objects.filter(student_id="23A91A6001").exists()
        )

    def test_unlinking_needs_a_post(self):
        response = self.client.get(
            reverse("student_account_unlink", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 405)
        self.student.refresh_from_db()
        self.assertIsNotNone(self.student.account)

    def test_a_faculty_member_cannot_manage_accounts(self):
        self.client.force_login(make_faculty())
        response = self.client.post(
            reverse("student_account_unlink", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.student.refresh_from_db()
        self.assertIsNotNone(self.student.account)
