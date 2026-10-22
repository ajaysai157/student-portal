"""Database models for the College Management Portal.

Design notes
------------
* ``Department`` is a first-class table. The original portal stored the
  branch as free text on every student row, which allowed typos and
  duplicate spellings of the same branch. The migration to the foreign
  key is done in ``0005_migrate_branch_to_department``.
* ``Students.account`` is a ``OneToOneField`` to ``auth.User``. One login
  maps to at most one student record, which is what makes "log in and see
  only your own profile" enforceable on the server.
* ``FacultyProfile`` keeps authentication data (the ``User`` row) separate
  from faculty specific data (employee id, designation, departments).
* ``DepartmentChangeLog`` is a deliberately small audit trail: who changed
  a department, when, and which fields moved.
"""

from django.conf import settings
from django.db import models


class Department(models.Model):
    """An academic department / branch of the college."""

    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short unique code, e.g. AIML, CSE, ECE.",
    )
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    office_location = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive departments stay in the records but cannot be assigned to new students.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        # The code and the name are sometimes the same (a department created
        # from a branch value), so the code is only added when it adds
        # information - otherwise the label would read "AIML - AIML".
        code = (self.code or "").strip()
        name = (self.name or "").strip()
        if not code:
            return name
        if not name:
            return code
        if code.upper() == name.upper():
            return name
        return f"{code} - {name}"

    @property
    def display_name(self):
        """The department name without the code."""
        return (self.name or self.code or "").strip()

    @property
    def student_count(self):
        return self.students.count()


class Students(models.Model):
    """Official student record.

    The table name (``Students``) and the primary key of the original
    project are kept so the existing rows keep working after migration.
    """

    SECTION_CHOICES = [
        (1, "Section 1"),
        (2, "Section 2"),
        (3, "Section 3"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
        ("unspecified", "Not specified"),
    ]

    student_name = models.CharField(max_length=30)
    student_id = models.CharField(max_length=15, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="students",
        help_text="The department this student is enrolled in.",
    )
    student_section = models.IntegerField(choices=SECTION_CHOICES)
    gender = models.CharField(
        max_length=12,
        choices=GENDER_CHOICES,
        default="unspecified",
        help_text="Used to pick the default avatar when no photo is uploaded.",
    )
    student_image = models.ImageField(upload_to="student_images/", blank=True, null=True)
    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_record",
        help_text="Login account linked to this student (at most one).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Students"
        ordering = ["student_name"]
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        return f"{self.student_name} ({self.student_id})"

    @property
    def has_account(self):
        return self.account_id is not None

    @property
    def photo_url(self):
        """URL of the uploaded photo, or ``None`` when no photo is on file."""
        if self.student_image:
            try:
                return self.student_image.url
            except ValueError:  # pragma: no cover - file missing on disk
                return None
        return None

    @property
    def gender_display(self):
        return dict(self.GENDER_CHOICES).get(self.gender, "Not specified")


class FacultyProfile(models.Model):
    """Faculty specific information attached to a Django user account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="faculty_profile",
    )
    employee_id = models.CharField(max_length=20, unique=True)
    designation = models.CharField(max_length=60, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(
        upload_to="faculty_photos/",
        blank=True,
        null=True,
        help_text="Photo shown in the portal. A default avatar is used when empty.",
    )
    departments = models.ManyToManyField(
        Department,
        related_name="faculty_members",
        blank=True,
        help_text="Departments this faculty member is assigned to.",
    )

    class Meta:
        ordering = ["user__first_name", "user__last_name"]
        verbose_name = "Faculty member"
        verbose_name_plural = "Faculty members"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.employee_id})"

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def photo_url(self):
        """URL of the uploaded photo, or ``None`` when no photo is on file."""
        if self.photo:
            try:
                return self.photo.url
            except ValueError:  # pragma: no cover - file missing on disk
                return None
        return None


class UserProfile(models.Model):
    """Extra portal data of a user account without a faculty profile.

    Administrators (and any other user without a ``FacultyProfile``) can
    upload a photo here.  When no photo is uploaded the portal shows the
    default avatar of the role.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portal_profile",
    )
    photo = models.ImageField(
        upload_to="profile_photos/",
        blank=True,
        null=True,
        help_text="Photo shown in the portal. A default avatar is used when empty.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User profile"
        verbose_name_plural = "User profiles"

    def __str__(self):
        return f"Profile of {self.user.get_username()}"

    @property
    def photo_url(self):
        if self.photo:
            try:
                return self.photo.url
            except ValueError:  # pragma: no cover - file missing on disk
                return None
        return None


class DepartmentChangeLog(models.Model):
    """Small audit trail for department edits."""

    ACTION_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("deactivated", "Deactivated"),
        ("reactivated", "Reactivated"),
    ]

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="change_logs",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="department_changes",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    changes = models.JSONField(default=dict, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "Department change log"

    def __str__(self):
        return f"{self.department} - {self.action} by {self.changed_by}"


class CorrectionRequest(models.Model):
    """A student's request to correct a field on their own record.

    Submitting a request never edits the official student row. An admin
    reviews the request and decides whether to apply the change.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    FIELD_CHOICES = [
        ("student_name", "Name"),
        ("department", "Department"),
        ("student_section", "Section"),
    ]

    student = models.ForeignKey(
        Students,
        on_delete=models.CASCADE,
        related_name="correction_requests",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="correction_requests",
    )
    field_name = models.CharField(max_length=30, choices=FIELD_CHOICES)
    current_value = models.CharField(max_length=120, blank=True)
    requested_value = models.CharField(max_length=120)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_correction_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Correction request"

    def __str__(self):
        return f"{self.student.student_id} - {self.get_field_name_display()} ({self.status})"
