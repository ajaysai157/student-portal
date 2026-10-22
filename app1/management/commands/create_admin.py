"""Create the first administrator account.

This is the safe way to get a portal admin without a public sign up form
and without hard coded default credentials: the password is typed in
interactively and is checked by Django's own password validators.

Examples::

    python manage.py create_admin
    python manage.py create_admin --username principal --email principal@college.edu
"""

import getpass

from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

ADMIN_GROUP = "Admin"


class Command(BaseCommand):
    help = "Create a superuser account that can manage the College Management Portal."

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Username for the new account.")
        parser.add_argument("--email", help="Email address for the new account.")
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Do not ask for a password (the account is created disabled).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options.get("username") or input("Username: ").strip()
        email = options.get("email") or input("Email: ").strip()

        if not username:
            raise CommandError("A username is required.")

        if User.objects.filter(username__iexact=username).exists():
            raise CommandError(f"The username '{username}' is already taken.")

        password = None
        if not options.get("no_input"):
            password = getpass.getpass("Password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise CommandError("The passwords do not match.")
            try:
                validate_password(password)
            except ValidationError as error:
                raise CommandError("\n".join(error.messages))

        user = User(
            username=username,
            email=email,
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )
        if password:
            user.set_password(password)
        else:
            # Without a password the account cannot be used until an
            # administrator sets one.
            user.set_unusable_password()
        user.save()

        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        user.groups.add(admin_group)

        if password:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Administrator '{username}' created. You can sign in now."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Administrator '{username}' created without a password. "
                    "Set one with: python manage.py changepassword " + username
                )
            )
