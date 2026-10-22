"""Drop the obsolete ``student_branch`` text column.

The data was copied into the ``department`` foreign key in ``0005`` and
verified before this migration runs, so nothing is lost.

Note: reversing this migration re-creates the column **empty** - the
original text values live on in the ``Department`` rows that were created
from them.  Always take a database backup before migrating downwards.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app1", "0006_finalize_student_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="students",
            name="student_branch",
        ),
    ]
