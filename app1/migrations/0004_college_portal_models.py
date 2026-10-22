"""Introduce the College Management Portal schema.

This migration only *adds* things:

* the new ``Department``, ``FacultyProfile``, ``DepartmentChangeLog`` and
  ``CorrectionRequest`` tables
* the nullable ``department`` / ``account`` columns on ``Students``
* the nullable ``created_at`` / ``updated_at`` columns on ``Students``

Nothing is dropped here. The existing ``student_branch`` text column is
kept until the data has been copied in ``0005`` so the migration is fully
reversible and no data is lost if something goes wrong.

Every new column on ``Students`` is nullable on purpose: SQLite cannot add
a ``NOT NULL`` column to a table that already has rows, so the columns are
filled in the following data migration and tightened afterwards.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app1", "0003_students_student_image"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        help_text="Short unique code, e.g. AIML, CSE, ECE.",
                        max_length=10,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=80, unique=True)),
                ("description", models.TextField(blank=True)),
                ("office_location", models.CharField(blank=True, max_length=120)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text=(
                            "Inactive departments stay in the records but cannot be "
                            "assigned to new students."
                        ),
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Department",
                "verbose_name_plural": "Departments",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="FacultyProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("employee_id", models.CharField(max_length=20, unique=True)),
                ("designation", models.CharField(blank=True, max_length=60)),
                ("phone", models.CharField(blank=True, max_length=20)),
                (
                    "departments",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Departments this faculty member is assigned to.",
                        related_name="faculty_members",
                        to="app1.department",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="faculty_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Faculty member",
                "verbose_name_plural": "Faculty members",
                "ordering": ["user__first_name", "user__last_name"],
            },
        ),
        migrations.CreateModel(
            name="DepartmentChangeLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("updated", "Updated"),
                            ("deactivated", "Deactivated"),
                            ("reactivated", "Reactivated"),
                        ],
                        max_length=20,
                    ),
                ),
                ("changes", models.JSONField(blank=True, default=dict)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="department_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="change_logs",
                        to="app1.department",
                    ),
                ),
            ],
            options={
                "verbose_name": "Department change log",
                "ordering": ["-changed_at"],
            },
        ),
        migrations.CreateModel(
            name="CorrectionRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "field_name",
                    models.CharField(
                        choices=[
                            ("student_name", "Name"),
                            ("department", "Department"),
                            ("student_section", "Section"),
                        ],
                        max_length=30,
                    ),
                ),
                ("current_value", models.CharField(blank=True, max_length=120)),
                ("requested_value", models.CharField(max_length=120)),
                ("reason", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("admin_note", models.TextField(blank=True)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_correction_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="correction_requests",
                        to="app1.students",
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="correction_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Correction request",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="students",
            name="department",
            field=models.ForeignKey(
                blank=True,
                help_text="The department this student is enrolled in.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="students",
                to="app1.department",
            ),
        ),
        migrations.AddField(
            model_name="students",
            name="account",
            field=models.OneToOneField(
                blank=True,
                help_text="Login account linked to this student (at most one).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="student_record",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="students",
            name="created_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="students",
            name="updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name="students",
            options={
                "ordering": ["student_name"],
                "verbose_name": "Student",
                "verbose_name_plural": "Students",
            },
        ),
    ]
