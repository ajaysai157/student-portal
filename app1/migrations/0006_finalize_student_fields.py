"""Tighten the new student columns now that the data has been copied.

The columns are added as nullable in ``0004`` because SQLite cannot add a
``NOT NULL`` column to a table that already contains rows.  After
``0005`` every student has a department and a timestamp, so they can be
made mandatory here.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app1", "0005_migrate_branch_to_department"),
    ]

    operations = [
        migrations.AlterField(
            model_name="students",
            name="department",
            field=models.ForeignKey(
                help_text="The department this student is enrolled in.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="students",
                to="app1.department",
            ),
        ),
        migrations.AlterField(
            model_name="students",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="students",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
