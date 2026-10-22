"""Department management: admin CRUD, faculty limited edit, delete rules."""

from django.test import TestCase
from django.urls import reverse

from college.models import Department, DepartmentChangeLog

from .factories import (
    make_admin,
    make_department,
    make_faculty,
    make_student,
    make_student_user,
)


class DepartmentAccessTests(TestCase):
    def setUp(self):
        self.department = make_department()

    def test_every_signed_in_user_can_see_the_department_list(self):
        for user in (
            make_admin(),
            make_faculty(),
            make_student_user()[1],
        ):
            self.client.force_login(user)
            response = self.client.get(reverse("department_list"))
            self.assertEqual(response.status_code, 200)

    def test_anonymous_visitors_are_sent_to_the_login_page(self):
        response = self.client.get(reverse("department_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_a_student_cannot_create_a_department(self):
        self.client.force_login(make_student_user()[1])
        response = self.client.get(reverse("department_create"))
        self.assertEqual(response.status_code, 403)

    def test_a_faculty_member_cannot_create_a_department(self):
        self.client.force_login(make_faculty())
        response = self.client.get(reverse("department_create"))
        self.assertEqual(response.status_code, 403)


class DepartmentCreateTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.force_login(self.admin)

    def test_admin_can_create_a_department(self):
        response = self.client.post(
            reverse("department_create"),
            {
                "code": "cse",
                "name": "Computer Science",
                "description": "Programming and systems.",
                "office_location": "Block B",
                "contact_email": "cse@college.edu",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        department = Department.objects.get(code="CSE")
        self.assertEqual(department.name, "Computer Science")
        self.assertEqual(department.code, "CSE")  # the code is upper cased
        self.assertTrue(department.is_active)

    def test_a_duplicate_code_is_rejected(self):
        make_department(code="AIML")
        response = self.client.post(
            reverse("department_create"),
            {"code": "AIML", "name": "Another name", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already in use")
        self.assertEqual(Department.objects.filter(code="AIML").count(), 1)

    def test_a_duplicate_name_is_rejected(self):
        make_department(code="AIML", name="Artificial Intelligence")
        response = self.client.post(
            reverse("department_create"),
            {"code": "CSE", "name": "Artificial Intelligence", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Department.objects.filter(code="CSE").exists())

    def test_an_invalid_contact_email_is_rejected(self):
        response = self.client.post(
            reverse("department_create"),
            {"code": "CSE", "name": "Computer Science", "contact_email": "not-an-email"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Department.objects.filter(code="CSE").exists())

    def test_the_change_is_written_to_the_audit_trail(self):
        self.client.post(
            reverse("department_create"),
            {"code": "CSE", "name": "Computer Science", "is_active": "on"},
        )
        log = DepartmentChangeLog.objects.get(department__code="CSE")
        self.assertEqual(log.action, "created")
        self.assertEqual(log.changed_by, self.admin)


class DepartmentEditTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department(code="AIML", name="Artificial Intelligence")
        self.other = make_department(code="CSE", name="Computer Science")

    def test_admin_can_edit_every_field(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("department_edit", args=[self.department.pk]),
            {
                "code": "AIML",
                "name": "AI and Machine Learning",
                "description": "New description",
                "office_location": "Block A",
                "contact_email": "aiml@college.edu",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.department.refresh_from_db()
        self.assertEqual(self.department.name, "AI and Machine Learning")
        self.assertEqual(self.department.office_location, "Block A")

    def test_the_edit_is_written_to_the_audit_trail(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("department_edit", args=[self.department.pk]),
            {
                "code": "AIML",
                "name": "Artificial Intelligence",
                "description": "Changed",
                "office_location": "Block A",
                "contact_email": "",
                "is_active": "on",
            },
        )
        log = DepartmentChangeLog.objects.filter(
            department=self.department, action="updated"
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("description", log.changes)

    def test_faculty_can_edit_the_descriptive_fields_of_their_own_department(self):
        faculty = make_faculty(departments=[self.department])
        self.client.force_login(faculty)
        response = self.client.post(
            reverse("department_edit", args=[self.department.pk]),
            {
                "description": "Updated by the faculty member",
                "office_location": "Block C",
                "contact_email": "aiml@college.edu",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.department.refresh_from_db()
        self.assertEqual(self.department.description, "Updated by the faculty member")
        self.assertEqual(self.department.office_location, "Block C")

    def test_faculty_cannot_change_the_administrative_fields(self):
        faculty = make_faculty(departments=[self.department])
        self.client.force_login(faculty)
        self.client.post(
            reverse("department_edit", args=[self.department.pk]),
            {
                "code": "HACKED",
                "name": "Hacked name",
                "description": "Only this may change",
                "office_location": "",
                "contact_email": "",
            },
        )
        self.department.refresh_from_db()
        self.assertEqual(self.department.code, "AIML")
        self.assertEqual(self.department.name, "Artificial Intelligence")
        self.assertEqual(self.department.description, "Only this may change")

    def test_faculty_cannot_edit_a_department_they_are_not_assigned_to(self):
        faculty = make_faculty(departments=[self.department])
        self.client.force_login(faculty)
        response = self.client.post(
            reverse("department_edit", args=[self.other.pk]),
            {"description": "Should not be saved", "office_location": "", "contact_email": ""},
        )
        self.assertEqual(response.status_code, 403)
        self.other.refresh_from_db()
        self.assertNotEqual(self.other.description, "Should not be saved")

    def test_a_student_cannot_edit_a_department(self):
        self.client.force_login(make_student_user()[1])
        response = self.client.post(
            reverse("department_edit", args=[self.department.pk]),
            {"description": "Nope", "office_location": "", "contact_email": ""},
        )
        self.assertEqual(response.status_code, 403)
        self.department.refresh_from_db()
        self.assertNotEqual(self.department.description, "Nope")

    def test_a_missing_department_gives_a_404(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("department_edit", args=[9999]))
        self.assertEqual(response.status_code, 404)


class DepartmentDeleteTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()

    def test_an_unused_department_can_be_deleted(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("department_delete", args=[self.department.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Department.objects.filter(pk=self.department.pk).exists())

    def test_a_department_with_students_cannot_be_deleted(self):
        make_student(student_id="23A91A6001", department=self.department)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("department_delete", args=[self.department.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Department.objects.filter(pk=self.department.pk).exists())

    def test_a_department_with_faculty_cannot_be_deleted(self):
        make_faculty(departments=[self.department])
        self.client.force_login(self.admin)
        response = self.client.post(reverse("department_delete", args=[self.department.pk]))
        self.assertTrue(Department.objects.filter(pk=self.department.pk).exists())

    def test_the_delete_needs_a_post(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("department_delete", args=[self.department.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Department.objects.filter(pk=self.department.pk).exists())

    def test_faculty_cannot_delete_a_department(self):
        self.client.force_login(make_faculty(departments=[self.department]))
        response = self.client.post(reverse("department_delete", args=[self.department.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Department.objects.filter(pk=self.department.pk).exists())


class DepartmentActiveTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()
        self.client.force_login(self.admin)

    def test_a_department_can_be_deactivated_and_activated_again(self):
        self.client.post(reverse("department_toggle_active", args=[self.department.pk]))
        self.department.refresh_from_db()
        self.assertFalse(self.department.is_active)

        self.client.post(reverse("department_toggle_active", args=[self.department.pk]))
        self.department.refresh_from_db()
        self.assertTrue(self.department.is_active)

    def test_the_toggle_is_written_to_the_audit_trail(self):
        self.client.post(reverse("department_toggle_active", args=[self.department.pk]))
        self.assertTrue(
            DepartmentChangeLog.objects.filter(
                department=self.department, action="deactivated"
            ).exists()
        )

    def test_a_deactivated_department_is_not_offered_for_new_students(self):
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])
        response = self.client.get(reverse("register_student"))
        self.assertNotContains(response, f">{self.department.name}</option>")

    def test_faculty_cannot_toggle_a_department(self):
        self.client.force_login(make_faculty(departments=[self.department]))
        response = self.client.post(
            reverse("department_toggle_active", args=[self.department.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.department.refresh_from_db()
        self.assertTrue(self.department.is_active)


class DepartmentDetailTests(TestCase):
    def setUp(self):
        self.department = make_department()
        self.client.force_login(make_admin())

    def test_the_detail_page_shows_the_department(self):
        response = self.client.get(reverse("department_detail", args=[self.department.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.department.code)
        self.assertContains(response, self.department.name.replace("&", "&amp;"))

    def test_a_missing_department_gives_a_404(self):
        response = self.client.get(reverse("department_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)
