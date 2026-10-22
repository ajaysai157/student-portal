from django.apps import AppConfig
from django.db.models.signals import post_migrate


class App1Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app1"
    verbose_name = "College Portal"

    def ready(self):
        """Assign the role permissions once Django has created them.

        Django creates the ``auth_permission`` rows in a ``post_migrate``
        handler, so the groups have to be filled in there as well - doing
        it inside a data migration would run before the permissions exist.
        """
        from . import permissions  # imported lazily to avoid an import loop

        post_migrate.connect(
            permissions.assign_role_permissions,
            sender=self,
            dispatch_uid="app1.assign_role_permissions",
        )
