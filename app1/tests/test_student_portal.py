"""Student self service: own profile, own department, correction requests."""

from django.test import TestCase
from django.urls import reverse

from app1.models import CorrectionRequest, Students

from .factories import (
    make_admin,
    make_department,
    make_faculty,
    make_student,
    make_student_user,
)


class MyProfileTests(TestCase):
    def setUp(self):
        self.department = make_department()
        self.student, self.user = make_student_user(
            student_id="23A91A6001", name="Ravi Kumar"
        )
        self.client.force_login(self.user)

    def test_the_student_sees_their_own_profile(self):
        response = self.client.get(reverse("my_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ravi Kumar")
        self.assertContains(response, "23A91A6001")

    def test_the_student_sees_their_own_department(self):
        response = self.client.get(reverse("my_department"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.department.code)

    def test_an_account_without_a_student_record_says_so(self):
        from django.contrib.auth.models import Group, User

        user = User.objects.create_user(username="orphan", password="x")
        user.groups.add(Group.objects.get(name="Student"))
        self.client.force_login(user)
        response = self.client.get(reverse("my_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "my/no_profile.html")

    def test_an_admin_can_open_the_self_service_pages_too(self):
        self.client.force_login(make_admin())
        response = self.client.get(reverse("my_profile"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_visitors_are_sent_to_the_login_page(self):
        self.client.logout()
        response = self.client.get(reverse("my_profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])


class CorrectionRequestTests(TestCase):
    def setUp(self):
        self.department = make_department()
        self.student, self.user = make_student_user(
            student_id="23A91A6001", name="Ravi Kumar"
        )
        self.client.force_login(self.user)

    def post_request(self, **overrides):
        data = {
            "field_name": "student_name",
            "requested_value": "Ravi Kumar Raj",
            "reason": "My name is spelled wrongly on the certificate.",
        }
        data.update(overrides)
        return self.client.post(reverse("my_correction_requests"), data)

    def test_a_student_can_submit_a_correction_request(self):
        response = self.post_request()
        self.assertEqual(response.status_code, 302)

        request = CorrectionRequest.objects.get()
        self.assertEqual(request.student, self.student)
        self.assertEqual(request.submitted_by, self.user)
        self.assertEqual(request.field_name, "student_name")
        self.assertEqual(request.requested_value, "Ravi Kumar Raj")
        self.assertEqual(request.current_value, "Ravi Kumar")
        self.assertEqual(request.status, "pending")

    def test_submitting_a_request_does_not_change_the_official_record(self):
        self.post_request()
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_name, "Ravi Kumar")

    def test_an_empty_value_is_rejected(self):
        response = self.post_request(requested_value="   ")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CorrectionRequest.objects.count(), 0)

    def test_a_student_only_sees_their_own_requests(self):
        self.post_request()
        other_student, other_user = make_student_user(
            student_id="23A91A6002", name="Priya Sharma", username="priya"
        )
        CorrectionRequest.objects.create(
            student=other_student,
            submitted_by=other_user,
            field_name="student_name",
            requested_value="P",
            reason="x",
        )
        response = self.client.get(reverse("my_correction_requests"))
        self.assertEqual(len(response.context["requests"]), 1)
        self.assertEqual(response.context["requests"][0].student, self.student)


class CorrectionReviewTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department(code="AIML", name="Artificial Intelligence")
        self.other_department = make_department(code="CSE", name="Computer Science")
        self.student, self.user = make_student_user(
            student_id="23A91A6001", name="Ravi Kumar"
        )
        self.request = CorrectionRequest.objects.create(
            student=self.student,
            submitted_by=self.user,
            field_name="student_name",
            current_value="Ravi Kumar",
            requested_value="Ravi Kumar Raj",
            reason="Spelling mistake",
        )
        self.client.force_login(self.admin)

    def test_only_admin_can_review_requests(self):
        self.client.force_login(make_faculty())
        response = self.client.get(reverse("correction_request_list"))
        self.assertEqual(response.status_code, 403)

    def test_admin_sees_the_pending_requests(self):
        response = self.client.get(reverse("correction_request_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ravi Kumar Raj")

    def test_a_request_can_be_approved_without_applying_it(self):
        response = self.client.post(
            reverse("correction_request_review", args=[self.request.pk]),
            {"decision": "approved", "admin_note": "Verified with the office."},
        )
        self.assertEqual(response.status_code, 302)

        self.request.refresh_from_db()
        self.assertEqual(self.request.status, "approved")
        self.assertEqual(self.request.reviewed_by, self.admin)
        self.assertIsNotNone(self.request.reviewed_at)

        self.student.refresh_from_db()
        self.assertEqual(self.student.student_name, "Ravi Kumar")

    def test_an_approved_request_can_be_applied(self):
        self.client.post(
            reverse("correction_request_review", args=[self.request.pk]),
            {"decision": "approved", "apply_change": "on"},
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_name, "Ravi Kumar Raj")

    def test_a_request_can_be_rejected(self):
        self.client.post(
            reverse("correction_request_review", args=[self.request.pk]),
            {"decision": "rejected", "admin_note": "Please come to the office."},
        )
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, "rejected")
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_name, "Ravi Kumar")

    def test_a_department_change_is_applied_by_name(self):
        request = CorrectionRequest.objects.create(
            student=self.student,
            submitted_by=self.user,
            field_name="department",
            requested_value="Computer Science",
            reason="Wrong department",
        )
        self.client.post(
            reverse("correction_request_review", args=[request.pk]),
            {"decision": "approved", "apply_change": "on"},
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.department, self.other_department)

    def test_an_unknown_department_is_reported_and_not_applied(self):
        request = CorrectionRequest.objects.create(
            student=self.student,
            submitted_by=self.user,
            field_name="department",
            requested_value="Astrophysics",
            reason="Wrong department",
        )
        self.client.post(
            reverse("correction_request_review", args=[request.pk]),
            {"decision": "approved", "apply_change": "on"},
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.department, self.department)

    def test_a_section_change_is_applied(self):
        request = CorrectionRequest.objects.create(
            student=self.student,
            submitted_by=self.user,
            field_name="student_section",
            requested_value="2",
            reason="Wrong section",
        )
        self.client.post(
            reverse("correction_request_review", args=[request.pk]),
            {"decision": "approved", "apply_change": "on"},
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_section, 2)

    def test_an_invalid_section_is_not_applied(self):
        request = CorrectionRequest.objects.create(
            student=self.student,
            submitted_by=self.user,
            field_name="student_section",
            requested_value="nine",
            reason="Wrong section",
        )
        self.client.post(
            reverse("correction_request_review", args=[request.pk]),
            {"decision": "approved", "apply_change": "on"},
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_section, 1)

    def test_a_reviewed_request_cannot_be_reviewed_again(self):
        self.client.post(
            reverse("correction_request_review", args=[self.request.pk]),
            {"decision": "approved"},
        )
        response = self.client.get(reverse("correction_request_review", args=[self.request.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("correction_request_list"))
