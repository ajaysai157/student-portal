"""Create the three role groups.

The permissions of those groups are attached by the ``post_migrate``
handler in ``app1.apps.App1Config`` because Django only creates the
``auth_permission`` rows *after* the migrations have finished - a data
migration would run too early to see them.

The groups themselves are created here so that a fresh database always
contains them even if the signal handler is replaced later.
"""

from django.db import migrations

ADMIN_GROUP = "Admin"
FACULTY_GROUP = "Faculty"
STUDENT_GROUP = "Student"


def forwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in (ADMIN_GROUP, FACULTY_GROUP, STUDENT_GROUP):
        Group.objects.get_or_create(name=name)


def backwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(
        name__in=[ADMIN_GROUP, FACULTY_GROUP, STUDENT_GROUP]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app1", "0007_remove_students_branch"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
