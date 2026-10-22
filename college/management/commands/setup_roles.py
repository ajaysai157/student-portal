"""Create the portal role groups and (re)assign their permissions.

The groups are also created by the migrations and the permissions are
assigned by the ``post_migrate`` handler.  This command makes the same
thing happen on demand, which is handy after a manual change::

    python manage.py setup_roles
"""

from django.core.management.base import BaseCommand

from college.permissions import assign_role_permissions, ensure_groups


class Command(BaseCommand):
    help = "Create the Admin / Faculty / Student groups and assign their permissions."

    def handle(self, *args, **options):
        ensure_groups()
        assign_role_permissions()
        self.stdout.write(
            self.style.SUCCESS("Role groups and permissions are up to date.")
        )
