"""Tests for the management commands used to set the portal up."""

from io import StringIO

from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app1.models import FacultyProfile

from .factories import make_department


class SetupRolesCommandTests(TestCase):
    def test_the_three_role_groups_exist_after_the_command(self):
        call_command("setup_roles", stdout=StringIO(), stderr=StringIO())
        names = set(Group.objects.values_list("name", flat=True))
        self.assertTrue({"Admin", "Faculty", "Student"}.issubset(names))

    def test_the_admin_group_can_manage_the_portal_models(self):
        call_command("setup_roles", stdout=StringIO(), stderr=StringIO())
        admin = Group.objects.get(name="Admin")
        codenames = set(
            admin.permissions.filter(content_type__app_label="app1").values_list(
                "codename", flat=True
            )
        )
        self.assertIn("add_students", codenames)
        self.assertIn("change_department", codenames)
        self.assertIn("view_correctionrequest", codenames)

    def test_the_admin_group_cannot_touch_the_user_table(self):
        call_command("setup_roles", stdout=StringIO(), stderr=StringIO())
        admin = Group.objects.get(name="Admin")
        self.assertFalse(
            admin.permissions.filter(content_type__app_label="auth").exists()
        )
        self.assertFalse(
            admin.permissions.filter(
                content_type__app_label__in=["auth", "admin"]
            ).exists()
        )

    def test_the_student_group_has_no_model_permissions(self):
        call_command("setup_roles", stdout=StringIO(), stderr=StringIO())
        student = Group.objects.get(name="Student")
        self.assertEqual(
            student.permissions.filter(content_type__app_label="app1").count(), 0
        )

    def test_the_command_is_idempotent(self):
        call_command("setup_roles", stdout=StringIO(), stderr=StringIO())
        first = Group.objects.get(name="Admin").permissions.count()
        call_command("setup_roles", stdout=StringIO(), stderr=StringIO())
        second = Group.objects.get(name="Admin").permissions.count()
        self.assertEqual(first, second)


class CreateAdminCommandTests(TestCase):
    def test_an_admin_is_created_without_a_password(self):
        out = StringIO()
        call_command(
            "create_admin",
            username="principal",
            email="principal@college.edu",
            no_input=True,
            stdout=out,
            stderr=StringIO(),
        )
        user = User.objects.get(username="principal")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.assertIn(user.groups.get().name, ["Admin"])

    def test_the_password_is_read_interactively(self):
        answers = iter(["Str0ng-Passw0rd", "Str0ng-Passw0rd"])
        original = __import__("getpass").getpass
        __import__("getpass").getpass = lambda *args, **kwargs: next(answers)
        try:
            call_command(
                "create_admin",
                username="admin1",
                email="admin1@college.edu",
                stdout=StringIO(),
                stderr=StringIO(),
            )
        finally:
            __import__("getpass").getpass = original

        user = User.objects.get(username="admin1")
        self.assertTrue(user.check_password("Str0ng-Passw0rd"))

    def test_a_duplicate_username_is_refused(self):
        User.objects.create_user(username="principal", password="x")
        with self.assertRaisesMessage(CommandError, "already taken"):
            call_command(
                "create_admin",
                username="principal",
                email="p@college.edu",
                no_input=True,
                stdout=StringIO(),
                stderr=StringIO(),
            )

    def test_a_weak_password_is_refused(self):
        answers = iter(["123", "123"])
        original = __import__("getpass").getpass
        __import__("getpass").getpass = lambda *args, **kwargs: next(answers)
        try:
            with self.assertRaises(CommandError):
                call_command(
                    "create_admin",
                    username="weak",
                    email="weak@college.edu",
                    stdout=StringIO(),
                    stderr=StringIO(),
                )
        finally:
            __import__("getpass").getpass = original
        self.assertFalse(User.objects.filter(username="weak").exists())


class CreateFacultyCommandTests(TestCase):
    def run_command(self, **overrides):
        options = {
            "username": "iyer",
            "email": "iyer@college.edu",
            "employee_id": "EMP-101",
            "first_name": "Meera",
            "last_name": "Iyer",
            "designation": "Associate Professor",
            "phone": "9000000000",
            "departments": "AIML",
        }
        options.update(overrides)
        answers = iter(["Faculty@12345", "Faculty@12345"])
        original = __import__("getpass").getpass
        __import__("getpass").getpass = lambda *args, **kwargs: next(answers)
        try:
            call_command(
                "create_faculty",
                stdout=StringIO(),
                stderr=StringIO(),
                **options,
            )
        finally:
            __import__("getpass").getpass = original

    def test_a_faculty_account_is_created(self):
        self.run_command()
        user = User.objects.get(username="iyer")
        self.assertTrue(user.check_password("Faculty@12345"))
        self.assertEqual(user.groups.get().name, "Faculty")

        profile = FacultyProfile.objects.get(user=user)
        self.assertEqual(profile.employee_id, "EMP-101")
        self.assertEqual(profile.designation, "Associate Professor")
        self.assertEqual(profile.phone, "9000000000")
        self.assertEqual(profile.user.first_name, "Meera")

    def test_the_faculty_member_is_assigned_to_the_given_departments(self):
        department = make_department(code="AIML", name="Artificial Intelligence")
        self.run_command()
        profile = FacultyProfile.objects.get(user__username="iyer")
        self.assertEqual(list(profile.departments.all()), [department])

    def test_an_unknown_department_code_is_only_a_warning(self):
        make_department(code="AIML", name="Artificial Intelligence")
        err = StringIO()
        answers = iter(["Faculty@12345", "Faculty@12345"])
        original = __import__("getpass").getpass
        __import__("getpass").getpass = lambda *args, **kwargs: next(answers)
        try:
            call_command(
                "create_faculty",
                username="iyer",
                email="iyer@college.edu",
                employee_id="EMP-101",
                departments="AIML,NOPE",
                stdout=StringIO(),
                stderr=err,
            )
        finally:
            __import__("getpass").getpass = original

        self.assertIn("NOPE", err.getvalue())
        self.assertTrue(User.objects.filter(username="iyer").exists())

    def test_a_duplicate_employee_id_is_refused(self):
        self.run_command()
        with self.assertRaisesMessage(CommandError, "already in use"):
            self.run_command(username="iyer2")

    def test_a_duplicate_username_is_refused(self):
        self.run_command()
        with self.assertRaisesMessage(CommandError, "already taken"):
            self.run_command(employee_id="EMP-102")

    def test_the_employee_id_is_stored_in_upper_case(self):
        self.run_command(employee_id="emp-101")
        profile = FacultyProfile.objects.get(user__username="iyer")
        self.assertEqual(profile.employee_id, "EMP-101")
