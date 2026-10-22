"""Create a faculty account from the command line.

Useful for the first setup and for automation.  The account is put in the
``Faculty`` group and can be assigned to departments right away.

Example::

    python manage.py create_faculty --username iyer --email iyer@college.edu \\
        --employee-id EMP-001 --departments AIML,CSE
"""

import getpass

from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from college.models import Department, FacultyProfile

FACULTY_GROUP = "Faculty"


class Command(BaseCommand):
    help = "Create a faculty account and assign it to one or more departments."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--employee-id", required=True, dest="employee_id")
        parser.add_argument("--first-name", default="", dest="first_name")
        parser.add_argument("--last-name", default="", dest="last_name")
        parser.add_argument("--designation", default="")
        parser.add_argument("--phone", default="")
        parser.add_argument(
            "--departments",
            default="",
            help="Comma separated department codes, e.g. AIML,CSE.",
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise CommandError(f"The username '{username}' is already taken.")

        employee_id = options["employee_id"].strip().upper()
        if FacultyProfile.objects.filter(employee_id__iexact=employee_id).exists():
            raise CommandError(f"Employee ID '{employee_id}' is already in use.")

        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise CommandError("The passwords do not match.")
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError("\n".join(error.messages))

        user = User.objects.create_user(
            username=username,
            email=options["email"].strip(),
            password=password,
            first_name=options["first_name"].strip(),
            last_name=options["last_name"].strip(),
            is_active=True,
        )
        profile = FacultyProfile.objects.create(
            user=user,
            employee_id=employee_id,
            designation=options["designation"].strip(),
            phone=options["phone"].strip(),
        )

        codes = [code.strip() for code in options["departments"].split(",") if code.strip()]
        if codes:
            departments = Department.objects.filter(code__in=codes)
            missing = set(codes) - {d.code for d in departments}
            if missing:
                self.stderr.write(
                    self.style.WARNING(
                        "Unknown department code(s): " + ", ".join(sorted(missing))
                    )
                )
            profile.departments.set(departments)

        faculty_group, _ = Group.objects.get_or_create(name=FACULTY_GROUP)
        user.groups.add(faculty_group)

        self.stdout.write(
            self.style.SUCCESS(
                f"Faculty account '{username}' created with "
                f"{profile.departments.count()} department assignment(s)."
            )
        )
