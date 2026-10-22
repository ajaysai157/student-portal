"""Create the standard branches (departments) and fill them with students.

The portal starts with a single department that was created from the
``branch`` column of the original student table.  This command creates the
usual set of branches, gives them a proper name and spreads the students
over them, so the directory shows a realistic college::

    python manage.py seed_branches

The command is idempotent - running it twice does not create duplicates.
Departments that already exist are only completed (name, description,
office, e-mail) when they are still empty, so manual changes are never
overwritten.

Students that were already put in one of the branches by hand are left
where they are; only the students of the *seed* department are moved.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models

from college.models import Department, Students

#: The branches of the college: code -> details.
BRANCHES = [
    {
        "code": "AIML",
        "name": "Artificial Intelligence & Machine Learning",
        "description": (
            "Data mining, machine learning and the design of intelligent "
            "systems."
        ),
        "office_location": "Block A - Room 204",
        "contact_email": "aiml@college.edu",
    },
    {
        "code": "CSE",
        "name": "Computer Science & Engineering",
        "description": (
            "Programming, algorithms, databases and the engineering of "
            "software systems."
        ),
        "office_location": "Block A - Room 108",
        "contact_email": "cse@college.edu",
    },
    {
        "code": "ECE",
        "name": "Electronics & Communication Engineering",
        "description": (
            "Circuits, embedded systems, signals and communication "
            "technology."
        ),
        "office_location": "Block B - Room 301",
        "contact_email": "ece@college.edu",
    },
    {
        "code": "MECH",
        "name": "Mechanical Engineering",
        "description": (
            "Thermodynamics, manufacturing and the design of machines."
        ),
        "office_location": "Block C - Room 12",
        "contact_email": "mech@college.edu",
    },
    {
        "code": "CIVIL",
        "name": "Civil Engineering",
        "description": (
            "Structures, geotechnics and the planning of infrastructure."
        ),
        "office_location": "Block C - Room 04",
        "contact_email": "civil@college.edu",
    },
]

#: The department that was created from the old ``branch`` column.
SEED_CODES = {"AIML", "UNASSIGNED"}

#: The genders that are spread over the students that have no gender yet.
GENDERS = ["male", "female", "other"]


class Command(BaseCommand):
    help = "Create the standard branches and spread the students over them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-students",
            action="store_true",
            help="Only create the branches, do not move any student.",
        )
        parser.add_argument(
            "--no-gender",
            action="store_true",
            help="Do not fill in the gender of the students that have none.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # The departments that still carry the raw branch value are the seed
        # departments - the students in them are the ones to spread.
        seed_departments = list(self._seed_departments())

        departments = []
        for branch in BRANCHES:
            department, created = self._create_department(branch)
            departments.append(department)
            if created:
                self.stdout.write(f"  created branch {department}")
            else:
                self.stdout.write(f"  kept branch {department}")

        if options["no_students"]:
            self.stdout.write(
                self.style.SUCCESS("Branches are ready (no student was moved).")
            )
            return

        moved = self._spread_students(seed_departments, departments)
        self.stdout.write(f"  {moved} student(s) spread over the branches")

        if not options["no_gender"]:
            filled = self._fill_genders()
            self.stdout.write(f"  {filled} student(s) got a default gender")

        self.stdout.write(self.style.SUCCESS("The branches are ready."))

    # -- helpers ---------------------------------------------------------

    def _seed_departments(self):
        """Departments that still carry the raw branch value as their name.

        A department created from the old ``branch`` column has the same
        code and name ("AIML - AIML").  As soon as the branch gets its
        proper name it is no longer a seed department, so the command can
        be run again without moving the same students a second time.
        """
        return Department.objects.filter(code__in=SEED_CODES).filter(
            name__iexact=models.F("code")
        )

    def _create_department(self, branch):
        """Create the branch or complete the fields that are still empty."""
        department, created = Department.objects.get_or_create(
            code=branch["code"],
            defaults={
                "name": branch["name"],
                "description": branch["description"],
                "office_location": branch["office_location"],
                "contact_email": branch["contact_email"],
            },
        )
        if created:
            return department, True

        changed = []
        # A department that was created from a branch value has the same
        # code and name ("AIML - AIML"), which is replaced by the proper
        # name of the branch.
        if department.name.strip().upper() == branch["code"]:
            department.name = branch["name"]
            changed.append("name")
        for field in ("description", "office_location", "contact_email"):
            if not getattr(department, field).strip():
                setattr(department, field, branch[field])
                changed.append(field)
        if changed:
            department.save(update_fields=changed + ["updated_at"])
        return department, False

    def _spread_students(self, seed_departments, departments):
        """Move the students of the seed department over the branches.

        The students are spread in a round robin, ordered by their student
        id, so every branch gets a fair share.
        """
        if not seed_departments or not departments:
            return 0
        students = list(
            Students.objects.filter(
                department__in=seed_departments
            ).order_by("student_id")
        )
        for index, student in enumerate(students):
            student.department = departments[index % len(departments)]
            student.save(update_fields=["department", "updated_at"])
        return len(students)

    def _fill_genders(self):
        """Give the students without a gender a default one."""
        students = list(
            Students.objects.filter(gender="unspecified").order_by("student_id")
        )
        for index, student in enumerate(students):
            student.gender = GENDERS[index % len(GENDERS)]
            student.save(update_fields=["gender", "updated_at"])
        return len(students)
