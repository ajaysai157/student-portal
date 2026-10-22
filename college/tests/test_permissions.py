"""Unit tests for the role helpers in :mod:`college.permissions`."""

from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase

from college import permissions
from college.models import Students

from .factories import (
    make_admin,
    make_department,
    make_faculty,
    make_student,
    make_student_user,
    make_superuser,
)


class RoleDetectionTests(TestCase):
    def test_an_anonymous_user_has_no_role(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertIsNone(permissions.role_of(AnonymousUser()))
        self.assertIsNone(permissions.role_of(None))

    def test_a_superuser_is_an_admin(self):
        user = make_superuser()
        self.assertEqual(permissions.role_of(user), "admin")
        self.assertTrue(permissions.is_admin(user))

    def test_a_member_of_the_admin_group_is_an_admin(self):
        self.assertEqual(permissions.role_of(make_admin()), "admin")

    def test_a_faculty_member_is_a_faculty_member(self):
        user = make_faculty()
        self.assertEqual(permissions.role_of(user), "faculty")
        self.assertTrue(permissions.is_faculty(user))
        self.assertFalse(permissions.is_admin(user))
        self.assertFalse(permissions.is_student(user))

    def test_a_student_is_a_student(self):
        user = make_student_user()[1]
        self.assertEqual(permissions.role_of(user), "student")
        self.assertTrue(permissions.is_student(user))

    def test_a_user_without_a_group_has_no_role(self):
        user = User.objects.create_user(username="nobody", password="x")
        self.assertIsNone(permissions.role_of(user))

    def test_the_most_privileged_role_wins(self):
        user = make_admin()
        user.groups.add(Group.objects.get(name="Student"))
        self.assertEqual(permissions.role_of(user), "admin")


class FacultyScopeTests(TestCase):
    def setUp(self):
        self.assigned = make_department(code="AIML", name="Artificial Intelligence")
        self.other = make_department(code="CSE", name="Computer Science")
        self.faculty = make_faculty()
        permissions.faculty_profile_for(self.faculty).departments.set([self.assigned])

    def test_the_profile_of_a_faculty_member_is_found(self):
        self.assertIsNotNone(permissions.faculty_profile_for(self.faculty))

    def test_a_user_without_a_profile_has_no_departments(self):
        user = User.objects.create_user(username="plain", password="x")
        self.assertEqual(list(permissions.faculty_departments(user)), [])

    def test_faculty_can_edit_their_own_department(self):
        self.assertTrue(
            permissions.faculty_can_edit_department(self.faculty, self.assigned)
        )

    def test_faculty_cannot_edit_a_department_they_are_not_assigned_to(self):
        self.assertFalse(
            permissions.faculty_can_edit_department(self.faculty, self.other)
        )

    def test_an_admin_can_edit_every_department(self):
        admin = make_admin()
        self.assertTrue(permissions.faculty_can_edit_department(admin, self.other))

    def test_a_student_can_edit_nothing(self):
        student = make_student_user()[1]
        self.assertFalse(
            permissions.faculty_can_edit_department(student, self.assigned)
        )

    def test_an_anonymous_user_can_edit_nothing(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(
            permissions.faculty_can_edit_department(AnonymousUser(), self.assigned)
        )


class StudentOwnershipTests(TestCase):
    def test_the_record_is_found_through_the_account_link(self):
        student, user = make_student_user(
            student_id="23A91A6001", name="Ravi Kumar"
        )
        record = permissions.student_record_for(user)
        self.assertEqual(record, student)
        self.assertTrue(permissions.student_owns(user, student))

    def test_a_student_does_not_own_somebody_elses_record(self):
        student, user = make_student_user(student_id="23A91A6001")
        other = make_student(student_id="23A91A6002")
        self.assertFalse(permissions.student_owns(user, other))

    def test_an_account_without_a_record_has_none(self):
        user = User.objects.create_user(username="ghost", password="x")
        self.assertIsNone(permissions.student_record_for(user))

    def test_the_old_style_username_link_still_works(self):
        student = make_student(student_id="23A91A6500", name="Old Account")
        user = User.objects.create_user(username="23A91A6500", password="x")
        self.assertEqual(permissions.student_record_for(user), student)

    def test_an_anonymous_user_owns_nothing(self):
        from django.contrib.auth.models import AnonymousUser

        student = make_student()
        self.assertIsNone(permissions.student_record_for(AnonymousUser()))
        self.assertFalse(permissions.student_owns(AnonymousUser(), student))


class FakeSession(dict):
    """A session that behaves enough like the real one for the guard."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flushed = False

    def flush(self):
        self.flushed = True
        self.clear()


class LoginGuardTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_an_anonymous_visitor_is_redirected_to_the_login_page(self):
        request = self.factory.get("/manage/students/")
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()
        request.session = FakeSession()
        denied = permissions._login_guard(request)
        self.assertEqual(denied.status_code, 302)
        self.assertIn("/login", denied["Location"])

    def test_a_stale_session_of_a_deactivated_user_is_dropped(self):
        from django.contrib.auth import SESSION_KEY

        user = make_admin()
        user.is_active = False
        request = self.factory.get("/manage/students/")
        request.user = user
        request.session = FakeSession({SESSION_KEY: str(user.pk)})

        denied = permissions._login_guard(request)
        self.assertEqual(denied.status_code, 302)
        self.assertIn("/login", denied["Location"])
        self.assertTrue(request.session.flushed)

    def test_an_active_user_passes_the_guard(self):
        user = make_admin()
        request = self.factory.get("/manage/students/")
        request.user = user
        request.session = FakeSession()
        self.assertIsNone(permissions._login_guard(request))
