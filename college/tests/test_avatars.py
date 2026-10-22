"""Avatars, photo uploads and the branch seeding.

Every person of the portal has a picture: the uploaded photo when there is
one, otherwise a default avatar.  The default of a student depends on the
gender, the faculty and the administrators have their own default.
"""

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from college.avatars import (
    ADMIN_AVATAR,
    FACULTY_AVATAR,
    STUDENT_AVATARS,
    student_avatar_url,
    user_avatar_url,
)
from college.models import Department, FacultyProfile, Students, UserProfile

from .factories import (
    fake_image_file,
    make_admin,
    make_department,
    make_faculty,
    make_student,
    make_student_user,
)


class StudentAvatarTests(TestCase):
    def test_a_student_without_a_photo_gets_the_avatar_of_the_gender(self):
        student = make_student()
        student.gender = "male"
        student.save(update_fields=["gender"])
        self.assertTrue(student_avatar_url(student).endswith(STUDENT_AVATARS["male"]))

    def test_every_gender_has_its_own_default_avatar(self):
        for gender in ("male", "female", "other", "unspecified"):
            student = make_student(student_id=f"23A91A{gender[:2].upper()}")
            student.gender = gender
            student.save(update_fields=["gender"])
            url = student_avatar_url(student)
            self.assertTrue(url.endswith(".svg"), url)
            self.assertIn(STUDENT_AVATARS[gender], url)

    def test_an_unknown_gender_falls_back_to_the_neutral_avatar(self):
        student = make_student()
        student.gender = "something else"
        student.save(update_fields=["gender"])
        self.assertTrue(
            student_avatar_url(student).endswith(STUDENT_AVATARS["unspecified"])
        )

    def test_an_uploaded_photo_wins_over_the_default_avatar(self):
        student = make_student()
        student.student_image = fake_image_file(name="ravi.png")
        student.save()
        self.assertTrue(student_avatar_url(student).startswith("/media/"))
        self.assertNotIn(".svg", student_avatar_url(student))

    def test_the_gender_of_a_new_student_can_be_set_by_the_administration(self):
        admin = make_admin()
        department = make_department()
        self.client.force_login(admin)
        response = self.client.post(
            reverse("register_student"),
            {
                "student_name": "Ravi Kumar",
                "student_id": "23A91A6001",
                "department": department.pk,
                "student_section": 1,
                "gender": "female",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Students.objects.get(student_id="23A91A6001").gender, "female")

    def test_a_student_without_a_gender_is_stored_as_not_specified(self):
        admin = make_admin()
        department = make_department()
        self.client.force_login(admin)
        self.client.post(
            reverse("register_student"),
            {
                "student_name": "Ravi Kumar",
                "student_id": "23A91A6001",
                "department": department.pk,
                "student_section": 1,
            },
        )
        student = Students.objects.get(student_id="23A91A6001")
        self.assertEqual(student.gender, "unspecified")
        self.assertEqual(student.gender_display, "Not specified")


class RoleAvatarTests(TestCase):
    def test_a_faculty_member_gets_the_faculty_avatar(self):
        faculty = make_faculty()
        self.assertTrue(user_avatar_url(faculty).endswith(FACULTY_AVATAR))

    def test_an_administrator_gets_the_admin_avatar(self):
        admin = make_admin()
        self.assertTrue(user_avatar_url(admin).endswith(ADMIN_AVATAR))

    def test_a_student_account_gets_the_neutral_student_avatar(self):
        student, user = make_student_user()
        self.assertTrue(
            user_avatar_url(user).endswith(STUDENT_AVATARS["unspecified"])
        )

    def test_an_uploaded_faculty_photo_wins_over_the_default_avatar(self):
        faculty = make_faculty()
        profile = FacultyProfile.objects.get(user=faculty)
        profile.photo = fake_image_file(name="faculty.png")
        profile.save()
        self.assertTrue(user_avatar_url(faculty).startswith("/media/"))

    def test_an_uploaded_administrator_photo_wins_over_the_default_avatar(self):
        admin = make_admin()
        profile = UserProfile.objects.create(user=admin)
        profile.photo = fake_image_file(name="admin.png")
        profile.save()
        self.assertTrue(user_avatar_url(admin).startswith("/media/"))


class FacultySelfServiceTests(TestCase):
    def test_a_faculty_member_can_open_the_page(self):
        faculty = make_faculty()
        self.client.force_login(faculty)
        response = self.client.get(reverse("my_faculty_profile"))
        self.assertEqual(response.status_code, 200)

    def test_a_faculty_member_can_upload_a_photo(self):
        faculty = make_faculty()
        self.client.force_login(faculty)
        response = self.client.post(
            reverse("my_faculty_profile"),
            {
                "designation": "Associate Professor",
                "phone": "9876543210",
                "email": "faculty@college.edu",
                "photo": fake_image_file(name="me.png"),
            },
        )
        self.assertEqual(response.status_code, 302)
        profile = FacultyProfile.objects.get(user=faculty)
        self.assertTrue(profile.photo)
        self.assertEqual(profile.designation, "Associate Professor")
        self.assertEqual(profile.phone, "9876543210")

    def test_a_student_cannot_open_the_page(self):
        student, user = make_student_user()
        self.client.force_login(user)
        response = self.client.get(reverse("my_faculty_profile"))
        self.assertEqual(response.status_code, 403)

    def test_an_administrator_cannot_open_the_page(self):
        admin = make_admin()
        self.client.force_login(admin)
        response = self.client.get(reverse("my_faculty_profile"))
        self.assertEqual(response.status_code, 403)

    def test_an_anonymous_visitor_is_sent_to_the_login_page(self):
        response = self.client.get(reverse("my_faculty_profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])


class AccountPhotoTests(TestCase):
    def test_an_administrator_can_upload_a_photo_on_the_account_page(self):
        admin = make_admin()
        self.client.force_login(admin)
        response = self.client.post(
            reverse("account_overview"),
            {
                "first_name": "Portal",
                "last_name": "Admin",
                "photo": fake_image_file(name="admin.png"),
            },
        )
        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.get(user=admin)
        self.assertTrue(profile.photo)

    def test_a_faculty_member_uses_the_faculty_profile_for_the_photo(self):
        faculty = make_faculty()
        self.client.force_login(faculty)
        self.client.post(
            reverse("account_overview"),
            {
                "designation": "Lecturer",
                "phone": "9000000000",
                "email": "faculty@college.edu",
                "photo": fake_image_file(name="me.png"),
            },
        )
        profile = FacultyProfile.objects.get(user=faculty)
        self.assertTrue(profile.photo)
        self.assertFalse(UserProfile.objects.filter(user=faculty).exists())

    def test_a_student_cannot_upload_a_photo_on_the_account_page(self):
        student, user = make_student_user()
        self.client.force_login(user)
        response = self.client.post(
            reverse("account_overview"),
            {
                "first_name": "Asha",
                "last_name": "Rao",
                "photo": fake_image_file(name="me.png"),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

    def test_the_account_page_shows_the_default_avatar(self):
        admin = make_admin()
        self.client.force_login(admin)
        response = self.client.get(reverse("account_overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ADMIN_AVATAR.split("/")[-1])

    def test_an_administrator_can_upload_a_photo_for_a_faculty_member(self):
        admin = make_admin()
        faculty = make_faculty()
        profile = FacultyProfile.objects.get(user=faculty)
        self.client.force_login(admin)
        response = self.client.post(
            reverse("faculty_update", args=[profile.pk]),
            {
                "employee_id": profile.employee_id,
                "designation": "Lecturer",
                "phone": "9000000000",
                "email": "faculty@college.edu",
                "first_name": "Faculty",
                "last_name": "Member",
                "photo": fake_image_file(name="faculty.png"),
            },
        )
        self.assertEqual(response.status_code, 302)
        profile.refresh_from_db()
        self.assertTrue(profile.photo)
        self.assertTrue(user_avatar_url(faculty).startswith("/media/"))


class DepartmentTextTests(TestCase):
    def test_a_department_with_the_same_code_and_name_is_not_repeated(self):
        department = make_department(code="AIML", name="AIML")
        self.assertEqual(str(department), "AIML")

    def test_a_department_with_a_code_and_a_name_shows_both(self):
        department = make_department(code="CSE", name="Computer Science")
        self.assertEqual(str(department), "CSE - Computer Science")

    def test_the_student_page_does_not_show_the_department_twice(self):
        department = make_department(code="AIML", name="AIML")
        student = make_student(department=department)
        admin = make_admin()
        self.client.force_login(admin)
        response = self.client.get(
            reverse("student_detail", args=[student.student_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "AIML - AIML")


class SeedBranchesCommandTests(TestCase):
    def test_the_branches_are_created(self):
        call_command("seed_branches")
        codes = set(Department.objects.values_list("code", flat=True))
        self.assertTrue({"AIML", "CSE", "ECE", "MECH", "CIVIL"}.issubset(codes))

    def test_the_students_are_spread_over_the_branches(self):
        seed = make_department(code="AIML", name="AIML")
        for index in range(5):
            make_student(student_id=f"23A91A60{index:02d}", department=seed)

        call_command("seed_branches")

        used = set(Students.objects.values_list("department__code", flat=True))
        self.assertEqual(used, {"AIML", "CSE", "ECE", "MECH", "CIVIL"})
        for code in used:
            self.assertEqual(
                Students.objects.filter(department__code=code).count(), 1
            )

    def test_the_seed_department_gets_a_proper_name(self):
        make_department(code="AIML", name="AIML")
        call_command("seed_branches")
        self.assertEqual(
            Department.objects.get(code="AIML").name,
            "Artificial Intelligence & Machine Learning",
        )

    def test_the_gender_of_the_students_is_filled_in(self):
        seed = make_department(code="AIML", name="AIML")
        make_student(student_id="23A91A6001", department=seed)
        call_command("seed_branches")
        student = Students.objects.get(student_id="23A91A6001")
        self.assertNotEqual(student.gender, "unspecified")

    def test_the_command_can_be_run_twice(self):
        call_command("seed_branches")
        call_command("seed_branches")
        self.assertEqual(
            Department.objects.filter(code="CSE").count(),
            1,
        )

    def test_a_student_that_was_placed_by_hand_stays_where_it_is(self):
        manual = make_department(code="CSE", name="Computer Science")
        student = make_student(student_id="23A91A6001", department=manual)
        call_command("seed_branches")
        student.refresh_from_db()
        self.assertEqual(student.department, manual)
