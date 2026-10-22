"""Copy the free-text ``student_branch`` value into a real Department row.

The old portal stored the branch as plain text, so the same branch could be
spelled in several ways and nothing tied a branch to a faculty member.  In
this migration every distinct branch value becomes one ``Department`` and
every student is pointed at it.

Rules followed here:

* a branch value that already matches a department name is reused,
  so running the migration twice changes nothing;
* students whose branch is blank are **not** dropped - they are attached to
  an explicit "Unassigned" department and the affected ids are reported in
  the migration output so a human can fix them;
* the migration is reversible: reversing it only clears the foreign key,
  the original ``student_branch`` text column is still present and is
  dropped later by ``0007``.
"""

from django.db import migrations

UNASSIGNED_CODE = "UNASSIGNED"
UNASSIGNED_NAME = "Unassigned (needs review)"


def _unique_code(value, Department, db_alias, reserved=()):
    """Build a short, unique department code from a branch name."""
    base = "".join(ch for ch in value.upper() if ch.isalnum())[:10] or "DEPT"
    code = base
    suffix = 2
    while (
        code in reserved
        or Department.objects.using(db_alias).filter(code=code).exists()
    ):
        tail = str(suffix)
        code = f"{base[: 10 - len(tail)]}{tail}"
        suffix += 1
    return code


def forwards(apps, schema_editor):
    Department = apps.get_model("app1", "Department")
    Students = apps.get_model("app1", "Students")
    db_alias = schema_editor.connection.alias

    students = Students.objects.using(db_alias).all()
    branch_values = sorted(
        {
            (student.student_branch or "").strip()
            for student in students
            if (student.student_branch or "").strip()
        }
    )

    mapping = {}
    for value in branch_values:
        department = Department.objects.using(db_alias).filter(name=value).first()
        if department is None:
            code = _unique_code(value, Department, db_alias)
            department = Department.objects.using(db_alias).create(
                code=code, name=value
            )
        mapping[value] = department

    unassigned = Department.objects.using(db_alias).filter(
        code=UNASSIGNED_CODE
    ).first()
    if unassigned is None:
        unassigned = Department.objects.using(db_alias).create(
            code=UNASSIGNED_CODE, name=UNASSIGNED_NAME
        )

    blank_ids = []
    for student in students:
        value = (student.student_branch or "").strip()
        if value in mapping:
            student.department_id = mapping[value].pk
        else:
            student.department_id = unassigned.pk
            blank_ids.append(student.student_id)
        student.save(update_fields=["department"])

    print(
        f"Created/reused {len(mapping)} department(s) from existing branch "
        f"values: {', '.join(mapping) or 'none'}"
    )
    if blank_ids:
        print(
            "WARNING: the following students had no branch value and were "
            f"placed in '{UNASSIGNED_NAME}': {', '.join(blank_ids)}"
        )


def backwards(apps, schema_editor):
    Students = apps.get_model("app1", "Students")
    db_alias = schema_editor.connection.alias
    Students.objects.using(db_alias).all().update(department=None)


class Migration(migrations.Migration):

    dependencies = [
        ("app1", "0004_college_portal_models"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
