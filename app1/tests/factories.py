"""Shared helpers for the test suite.

The helpers build the three kinds of users the portal knows about and a
handful of records.  Every test starts from a clean database, so the
objects created here never leak into another test.
"""

import io
import os

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile

from app1.models import Department, FacultyProfile, Students

ADMIN_PASSWORD = "Admin-pass-123"
FACULTY_PASSWORD = "Faculty-pass-123"
STUDENT_PASSWORD = "Student-pass-123"

# A valid 1x1 pixel PNG.
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def png_upload(name="photo.png", content_type="image/png", size=None):
    """Return an uploaded file that looks like a real (small) PNG."""
    payload = PNG_BYTES
    if size:
        # Pad the PNG with a comment chunk so the file reaches the wanted
        # size while still being a valid image.
        padding = b"\x00" * max(0, size - len(PNG_BYTES))
        payload = PNG_BYTES[:12] + padding + PNG_BYTES[12:]
    return SimpleUploadedFile(name, payload, content_type=content_type)


def make_group(name):
    group, _ = Group.objects.get_or_create(name=name)
    return group


def make_admin(username="admin_user", password=ADMIN_PASSWORD, **kwargs):
    """A portal administrator (member of the ``Admin`` group)."""
    user = User.objects.create_user(
        username=username, password=password, email=kwargs.pop("email", ""), **kwargs
    )
    user.groups.add(make_group("Admin"))
    return user


def make_superuser(username="root_user", password=ADMIN_PASSWORD):
    """A Django superuser - the highest privilege level."""
    return User.objects.create_superuser(
        username=username, password=password, email="root@college.edu"
    )


def make_faculty(
    username="faculty_user",
    password=FACULTY_PASSWORD,
    departments=(),
    employee_id="EMP-001",
    **kwargs,
):
    """A faculty member, optionally assigned to some departments."""
    user = User.objects.create_user(
        username=username,
        password=password,
        email=kwargs.pop("email", "faculty@college.edu"),
        first_name=kwargs.pop("first_name", "Faculty"),
        last_name=kwargs.pop("last_name", "Member"),
        **kwargs,
    )
    user.groups.add(make_group("Faculty"))
    profile = FacultyProfile.objects.create(
        user=user,
        employee_id=employee_id,
        designation=kwargs.pop("designation", "Lecturer"),
        phone=kwargs.pop("phone", "9000000000"),
    )
    profile.departments.set(list(departments))
    return user


def make_student(
    student_id="23A91A6175",
    name="Asha Rao",
    department=None,
    section=1,
    account_username=None,
    account_password=STUDENT_PASSWORD,
):
    """A student record, optionally with a linked login account."""
    if department is None:
        department, _ = Department.objects.get_or_create(
            code="AIML", defaults={"name": "Artificial Intelligence & Machine Learning"}
        )
    student = Students.objects.create(
        student_name=name,
        student_id=student_id,
        department=department,
        student_section=section,
    )
    if account_username:
        user = User.objects.create_user(
            username=account_username, password=account_password
        )
        user.groups.add(make_group("Student"))
        student.account = user
        student.save(update_fields=["account", "updated_at"])
    return student


def make_student_user(
    student_id="23A91A6175",
    name="Asha Rao",
    username=None,
    password=STUDENT_PASSWORD,
    **kwargs,
):
    """A student record **and** the login account linked to it."""
    username = username or student_id.lower()
    student = make_student(
        student_id=student_id, name=name, account_username=username,
        account_password=password, **kwargs
    )
    return student, student.account


def make_department(code="AIML", name="Artificial Intelligence & Machine Learning", **kwargs):
    defaults = {"name": name}
    defaults.update(kwargs)
    return Department.objects.create(code=code, **defaults)


def fake_image_file(name="student.png", content_type="image/png"):
    """A small in-memory image usable as an upload."""
    return SimpleUploadedFile(name, PNG_BYTES, content_type=content_type)


def fake_non_image_file(name="payload.exe", content_type="application/octet-stream"):
    return SimpleUploadedFile(name, b"MZ\x90\x00not-an-image", content_type=content_type)


def large_image_file(name="huge.png", size=3 * 1024 * 1024):
    """A PNG that is big enough to trip the size limit."""
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow is a hard requirement
        return fake_non_image_file(name)

    width = 1400
    height = 1400
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for x in range(width):
        for y in range(height):
            pixels[x, y] = (os.urandom(1)[0], os.urandom(1)[0], os.urandom(1)[0])
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()
    if len(payload) < size:
        # PNG compression may shrink the file - add a large text chunk.
        payload = payload[:12] + b"\x00" * (size - len(payload)) + payload[12:]
    return SimpleUploadedFile(name, payload, content_type="image/png")
