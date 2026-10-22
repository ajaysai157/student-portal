"""Admin student CRUD, validation and photo handling."""

from django.test import TestCase
from django.urls import reverse

from app1.models import Students

from .factories import (
    fake_image_file,
    fake_non_image_file,
    large_image_file,
    make_admin,
    make_department,
    make_faculty,
    make_student,
    make_student_user,
)


class StudentCreateTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()
        self.client.force_login(self.admin)

    def post_student(self, **overrides):
        data = {
            "student_name": "Ravi Kumar",
            "student_id": "23A91A6001",
            "department": self.department.pk,
            "student_section": 1,
        }
        data.update(overrides)
        return self.client.post(reverse("register_student"), data)

    def test_admin_can_register_a_student(self):
        response = self.post_student()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("student_detail", args=["23A91A6001"]))

        student = Students.objects.get(student_id="23A91A6001")
        self.assertEqual(student.student_name, "Ravi Kumar")
        self.assertEqual(student.department, self.department)
        self.assertEqual(student.student_section, 1)
        self.assertIsNotNone(student.created_at)

    def test_a_duplicate_student_id_is_rejected(self):
        make_student(student_id="23A91A6001", name="Existing Student")
        response = self.post_student()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already in use")
        self.assertEqual(Students.objects.filter(student_id="23A91A6001").count(), 1)

    def test_the_student_id_is_normalised_to_upper_case(self):
        self.post_student(student_id="23a91a6002")
        self.assertTrue(Students.objects.filter(student_id="23A91A6002").exists())

    def test_a_missing_name_is_rejected(self):
        response = self.post_student(student_name="")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Students.objects.filter(student_id="23A91A6001").exists())

    def test_an_unknown_department_is_rejected(self):
        response = self.post_student(department=9999)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Students.objects.filter(student_id="23A91A6001").exists())

    def test_an_inactive_department_cannot_be_selected(self):
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])
        response = self.post_student()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Students.objects.filter(student_id="23A91A6001").exists())

    def test_an_invalid_section_is_rejected(self):
        response = self.post_student(student_section=9)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Students.objects.filter(student_id="23A91A6001").exists())

    def test_a_faculty_member_cannot_register_a_student(self):
        self.client.force_login(make_faculty())
        response = self.post_student()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Students.objects.filter(student_id="23A91A6001").exists())

    def test_a_student_cannot_register_a_student(self):
        self.client.force_login(make_student_user()[1])
        response = self.post_student()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Students.objects.filter(student_id="23A91A6001").exists())

    def test_an_anonymous_visitor_is_sent_to_the_login_page(self):
        self.client.logout()
        response = self.post_student()
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])
        self.assertFalse(Students.objects.filter(student_id="23A91A6001").exists())


class StudentPhotoTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()
        self.client.force_login(self.admin)

    def test_a_photo_can_be_uploaded(self):
        response = self.client.post(
            reverse("register_student"),
            {
                "student_name": "Ravi Kumar",
                "student_id": "23A91A6001",
                "department": self.department.pk,
                "student_section": 1,
                "student_image": fake_image_file(),
            },
        )
        self.assertEqual(response.status_code, 302)
        student = Students.objects.get(student_id="23A91A6001")
        self.assertTrue(student.student_image)
        self.assertIn("student_images", student.student_image.name)

    def test_a_file_that_is_not_an_image_is_rejected(self):
        response = self.client.post(
            reverse("register_student"),
            {
                "student_name": "Ravi Kumar",
                "student_id": "23A91A6001",
                "department": self.department.pk,
                "student_section": 1,
                "student_image": fake_non_image_file(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not a valid image")
        self.assertFalse(Students.objects.filter(student_id="23A91A6001").exists())

    def test_an_image_that_is_too_large_is_rejected(self):
        response = self.client.post(
            reverse("register_student"),
            {
                "student_name": "Ravi Kumar",
                "student_id": "23A91A6001",
                "department": self.department.pk,
                "student_section": 1,
                "student_image": large_image_file(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "too large")
        self.assertFalse(Students.objects.filter(student_id="23A91A6001").exists())

    def test_replacing_the_photo_removes_the_old_file(self):
        student = make_student(student_id="23A91A6001", name="Ravi Kumar")
        student.student_image.save("first.png", fake_image_file(), save=True)
        old_path = student.student_image.path
        self.assertTrue(old_path)

        response = self.client.post(
            reverse("update_student", args=["23A91A6001"]),
            {
                "student_name": "Ravi Kumar",
                "student_id": "23A91A6001",
                "department": self.department.pk,
                "student_section": 1,
                "student_image": fake_image_file(name="second.png"),
            },
        )
        self.assertEqual(response.status_code, 302)

        student.refresh_from_db()
        self.assertNotEqual(student.student_image.name, "student_images/first.png")
        import os

        self.assertFalse(os.path.exists(old_path))


class StudentUpdateTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()
        self.other_department = make_department(code="CSE", name="Computer Science")
        self.student = make_student(
            student_id="23A91A6001", name="Ravi Kumar", department=self.department
        )
        self.client.force_login(self.admin)

    def test_admin_can_update_a_student(self):
        response = self.client.post(
            reverse("update_student", args=["23A91A6001"]),
            {
                "student_name": "Ravi K",
                "student_id": "23A91A6001",
                "department": self.other_department.pk,
                "student_section": 2,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_name, "Ravi K")
        self.assertEqual(self.student.department, self.other_department)
        self.assertEqual(self.student.student_section, 2)

    def test_a_student_id_that_belongs_to_someone_else_is_rejected(self):
        make_student(student_id="23A91A6002", name="Other Student")
        response = self.client.post(
            reverse("update_student", args=["23A91A6001"]),
            {
                "student_name": "Ravi Kumar",
                "student_id": "23A91A6002",
                "department": self.department.pk,
                "student_section": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_id, "23A91A6001")

    def test_keeping_the_same_student_id_is_allowed(self):
        response = self.client.post(
            reverse("update_student", args=["23A91A6001"]),
            {
                "student_name": "Ravi Kumar",
                "student_id": "23A91A6001",
                "department": self.department.pk,
                "student_section": 3,
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_a_missing_student_gives_a_404(self):
        response = self.client.get(reverse("update_student", args=["99A99A9999"]))
        self.assertEqual(response.status_code, 404)

    def test_faculty_cannot_update_a_student(self):
        self.client.force_login(make_faculty())
        response = self.client.get(reverse("update_student", args=["23A91A6001"]))
        self.assertEqual(response.status_code, 403)


class StudentDeleteTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_student(student_id="23A91A6001", name="Ravi Kumar")
        self.client.force_login(self.admin)

    def test_the_confirmation_page_is_shown_first(self):
        response = self.client.get(reverse("student_delete_confirmation", args=["23A91A6001"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ravi Kumar")
        self.assertTrue(Students.objects.filter(student_id="23A91A6001").exists())

    def test_the_delete_only_works_with_a_post(self):
        response = self.client.get(reverse("delete_student", args=["23A91A6001"]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Students.objects.filter(student_id="23A91A6001").exists())

    def test_admin_can_delete_a_student(self):
        response = self.client.post(reverse("delete_student", args=["23A91A6001"]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("student_directory"))
        self.assertFalse(Students.objects.filter(student_id="23A91A6001").exists())

    def test_faculty_cannot_delete_a_student(self):
        self.client.force_login(make_faculty())
        response = self.client.post(reverse("delete_student", args=["23A91A6001"]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Students.objects.filter(student_id="23A91A6001").exists())

    def test_the_photo_is_removed_with_the_record(self):
        import os

        self.student.student_image.save("photo.png", fake_image_file(), save=True)
        path = self.student.student_image.path
        self.assertTrue(os.path.exists(path))

        self.client.post(reverse("delete_student", args=["23A91A6001"]))
        self.assertFalse(os.path.exists(path))

    def test_deleting_a_missing_student_gives_a_404(self):
        response = self.client.post(reverse("delete_student", args=["99A99A9999"]))
        self.assertEqual(response.status_code, 404)


class StudentDetailTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_student(student_id="23A91A6001", name="Ravi Kumar")
        self.client.force_login(self.admin)

    def test_the_detail_page_shows_the_student(self):
        response = self.client.get(reverse("student_detail", args=["23A91A6001"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ravi Kumar")
        self.assertContains(response, "23A91A6001")

    def test_a_missing_student_gives_a_404(self):
        response = self.client.get(reverse("student_detail", args=["99A99A9999"]))
        self.assertEqual(response.status_code, 404)

    def test_a_student_cannot_read_another_student_record(self):
        self.client.force_login(make_student_user()[1])
        response = self.client.get(reverse("student_detail", args=["23A91A6001"]))
        self.assertEqual(response.status_code, 403)
