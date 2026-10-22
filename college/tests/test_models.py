"""Model behaviour and the data preservation of the migration.

The portal replaces the free text ``student_branch`` column with a real
foreign key.  These tests run the migration for real to make sure that the
existing student rows survive the change.
"""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from college.models import Department, FacultyProfile, Students

from .factories import make_admin, make_department, make_student


class StudentModelTests(TestCase):
    def test_a_student_is_stored_in_the_students_table(self):
        student = make_student(student_id="23A91A6001", name="Ravi Kumar")
        with connection.cursor() as cursor:
            cursor.execute("SELECT student_name, student_id FROM Students WHERE id = %s", [student.pk])
            row = cursor.fetchone()
        self.assertEqual(row, ("Ravi Kumar", "23A91A6001"))

    def test_the_timestamps_are_filled_in(self):
        student = make_student()
        self.assertIsNotNone(student.created_at)
        self.assertIsNotNone(student.updated_at)

    def test_a_department_cannot_be_deleted_while_students_use_it(self):
        department = make_department()
        make_student(department=department)
        with self.assertRaises(Exception):
            department.delete()

    def test_the_student_count_of_a_department(self):
        department = make_department()
        make_student(department=department)
        make_student(student_id="23A91A6002", department=department)
        self.assertEqual(department.student_count, 2)

    def test_a_student_without_a_photo_has_no_photo_url(self):
        student = make_student()
        self.assertIsNone(student.photo_url)
        self.assertFalse(student.has_account)

    def test_deleting_the_account_keeps_the_student_record(self):
        from django.contrib.auth.models import User

        student = make_student()
        user = User.objects.create_user(username="ravi", password="x")
        student.account = user
        student.save(update_fields=["account"])
        self.assertTrue(student.has_account)

        user.delete()
        student.refresh_from_db()
        self.assertIsNone(student.account)
        self.assertTrue(Students.objects.filter(pk=student.pk).exists())

    def test_a_faculty_profile_is_removed_with_the_user(self):
        from .factories import make_faculty

        user = make_faculty()
        self.assertEqual(FacultyProfile.objects.count(), 1)
        user.delete()
        self.assertEqual(FacultyProfile.objects.count(), 0)


class DepartmentModelTests(TestCase):
    def test_the_departments_are_sorted_by_name(self):
        make_department(code="CSE", name="Computer Science")
        make_department(code="AIML", name="Artificial Intelligence")
        names = list(Department.objects.values_list("name", flat=True))
        self.assertEqual(names, sorted(names))
        self.assertLess(
            names.index("Artificial Intelligence"), names.index("Computer Science")
        )

    def test_the_text_of_a_department(self):
        department = make_department(code="AIML", name="Artificial Intelligence")
        self.assertEqual(str(department), "AIML - Artificial Intelligence")


class BranchToDepartmentMigrationTests(TransactionTestCase):
    """The migration from ``student_branch`` to ``department`` keeps the data."""

    available_apps = ["college", "django.contrib.auth", "django.contrib.contenttypes"]

    def tearDown(self):
        # Leave the database in the state the rest of the suite expects.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_the_existing_students_survive_the_migration(self):
        executor = MigrationExecutor(connection)
        old_target = [("college", "0004_college_portal_models")]
        executor.migrate(old_target)
        old_apps = executor.loader.project_state(old_target).apps

        OldStudents = old_apps.get_model("college", "Students")
        OldStudents.objects.create(
            student_name="Asha Rao",
            student_id="23A91A6175",
            student_branch="AIML",
            student_section=1,
            student_image="student_images/asha.jpg",
        )
        OldStudents.objects.create(
            student_name="Ravi Kumar",
            student_id="23A91A6002",
            student_branch="AIML",
            student_section=2,
        )
        OldStudents.objects.create(
            student_name="Priya Sharma",
            student_id="23A91A6003",
            student_branch="",
            student_section=1,
        )

        executor = MigrationExecutor(connection)
        new_target = [("college", "0007_remove_students_branch")]
        executor.migrate(new_target)
        new_apps = executor.loader.project_state(new_target).apps

        Students = new_apps.get_model("college", "Students")
        Department = new_apps.get_model("college", "Department")

        # No student was lost.
        self.assertEqual(Students.objects.count(), 3)

        # The branch became a department.
        aiml = Department.objects.get(name="AIML")
        self.assertEqual(aiml.code, "AIML")
        self.assertEqual(
            Students.objects.get(student_id="23A91A6175").department_id, aiml.pk
        )
        self.assertEqual(
            Students.objects.get(student_id="23A91A6002").department_id, aiml.pk
        )

        # The other fields are untouched.
        asha = Students.objects.get(student_id="23A91A6175")
        self.assertEqual(asha.student_name, "Asha Rao")
        self.assertEqual(asha.student_section, 1)
        self.assertEqual(asha.student_image, "student_images/asha.jpg")

        # A student without a branch is kept and flagged.
        unassigned = Department.objects.get(code="UNASSIGNED")
        self.assertEqual(
            Students.objects.get(student_id="23A91A6003").department_id, unassigned.pk
        )

        # The timestamps are filled in for the old rows.
        self.assertIsNotNone(Students.objects.get(student_id="23A91A6175").created_at)

    def test_running_the_migration_twice_does_not_duplicate_anything(self):
        executor = MigrationExecutor(connection)
        old_target = [("college", "0004_college_portal_models")]
        executor.migrate(old_target)
        old_apps = executor.loader.project_state(old_target).apps
        OldStudents = old_apps.get_model("college", "Students")
        OldStudents.objects.create(
            student_name="Asha Rao",
            student_id="23A91A6175",
            student_branch="AIML",
            student_section=1,
        )

        for target in (
            [("college", "0005_migrate_branch_to_department")],
            [("college", "0006_finalize_student_fields")],
            [("college", "0007_remove_students_branch")],
        ):
            executor = MigrationExecutor(connection)
            executor.migrate(target)

        new_apps = executor.loader.project_state(
            [("college", "0007_remove_students_branch")]
        ).apps
        Department = new_apps.get_model("college", "Department")
        Students = new_apps.get_model("college", "Students")

        self.assertEqual(Department.objects.filter(name="AIML").count(), 1)
        self.assertEqual(Students.objects.count(), 1)
