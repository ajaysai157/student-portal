"""All form definitions for the College Management Portal.

Every form is a plain Django ``Form``/``ModelForm``.  The important design
rule is that **a form only ever exposes the fields the current role is
allowed to change**:

* ``StudentRegisterForm`` / ``StudentUpdateForm`` are for admins only and
  contain the official fields.
* ``DepartmentFacultyEditForm`` contains *only* the three descriptive
  fields a faculty member may change - the department code, name and the
  faculty assignment stay out of the form entirely.
* ``FacultyCreateForm`` / ``FacultyUpdateForm`` are used by admins and set
  the role (Django group) on the server, never from submitted data.
"""

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .models import CorrectionRequest, Department, FacultyProfile, Students

#: Maximum size of an uploaded student photo (2 MB by default).
MAX_IMAGE_SIZE = 2 * 1024 * 1024
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

TEXT_CLASS = "form-input"
SELECT_CLASS = "form-input form-select"
CHECK_CLASS = "form-check"


def _add_css(widget, css_class=TEXT_CLASS):
    return widget.attrs.update({"class": css_class})


def validate_student_image(image):
    """Reject anything that is not a reasonably sized, real image.

    The extension and the content type are both checked and the file is
    opened with Pillow, so a renamed ``.exe`` or a truncated file cannot be
    stored.
    """
    if image is None:
        return

    max_size = getattr(settings, "PORTAL_MAX_IMAGE_SIZE", MAX_IMAGE_SIZE)
    if image.size > max_size:
        raise ValidationError(
            "Image is too large. The maximum allowed size is "
            f"{max_size // (1024 * 1024)} MB."
        )

    extension = "." + (image.name.rsplit(".", 1)[-1] if "." in image.name else "")
    if extension.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            "Unsupported file type. Please upload a JPG, PNG, GIF or WEBP image."
        )

    content_type = getattr(image, "content_type", None)
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError("Unsupported file type. Please upload an image file.")

    try:
        from PIL import Image

        image.seek(0)
        Image.open(image).verify()
        image.seek(0)
    except ValidationError:
        raise
    except Exception:
        raise ValidationError("The uploaded file is not a valid image.")


class StudentImageField(forms.ImageField):
    """``ImageField`` with the college specific validation rules."""

    default_error_messages = {
        "invalid_image": "The uploaded file is not a valid image.",
    }

    def clean(self, data, initial=None):
        cleaned = super().clean(data, initial)
        if cleaned:
            validate_student_image(cleaned)
        return cleaned


class StudentRegisterForm(forms.ModelForm):
    """Admin form used to register a new student."""

    student_image = StudentImageField(required=False)

    class Meta:
        model = Students
        fields = [
            "student_name",
            "student_id",
            "department",
            "student_section",
            "student_image",
        ]
        widgets = {
            "student_name": forms.TextInput(attrs={"class": TEXT_CLASS}),
            "student_id": forms.TextInput(
                attrs={"class": TEXT_CLASS, "placeholder": "e.g. 23A91A6175"}
            ),
            "department": forms.Select(attrs={"class": SELECT_CLASS}),
            "student_section": forms.Select(attrs={"class": SELECT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active departments may be picked for a new student.
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.fields["student_image"].widget.attrs.update(
            {"class": TEXT_CLASS, "accept": "image/*"}
        )
        self.fields["student_name"].label = "Full name"

    def clean_student_id(self):
        value = self.cleaned_data["student_id"].strip().upper()
        if not value:
            raise ValidationError("Student ID is required.")
        if Students.objects.filter(student_id__iexact=value).exists():
            raise ValidationError(f"Student ID '{value}' is already in use.")
        return value

    def clean_student_name(self):
        value = self.cleaned_data["student_name"].strip()
        if len(value) < 2:
            raise ValidationError("Enter the full name of the student.")
        return value


class StudentUpdateForm(forms.ModelForm):
    """Admin form used to edit an existing student record."""

    student_image = StudentImageField(required=False)

    class Meta:
        model = Students
        fields = [
            "student_name",
            "student_id",
            "department",
            "student_section",
            "student_image",
        ]
        widgets = {
            "student_name": forms.TextInput(attrs={"class": TEXT_CLASS}),
            "student_id": forms.TextInput(attrs={"class": TEXT_CLASS}),
            "department": forms.Select(attrs={"class": SELECT_CLASS}),
            "student_section": forms.Select(attrs={"class": SELECT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.fields["student_image"].widget.attrs.update(
            {"class": TEXT_CLASS, "accept": "image/*"}
        )
        self.fields["student_image"].help_text = (
            "Leave empty to keep the current photo. Uploading a new file "
            "replaces it."
        )

    def clean_student_id(self):
        value = self.cleaned_data["student_id"].strip().upper()
        if not value:
            raise ValidationError("Student ID is required.")
        duplicate = Students.objects.filter(student_id__iexact=value)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise ValidationError(f"Student ID '{value}' is already in use.")
        return value


class DepartmentForm(forms.ModelForm):
    """Admin form with the full set of department fields."""

    class Meta:
        model = Department
        fields = [
            "code",
            "name",
            "description",
            "office_location",
            "contact_email",
            "is_active",
        ]
        widgets = {
            "code": forms.TextInput(
                attrs={"class": TEXT_CLASS, "placeholder": "e.g. CSE"}
            ),
            "name": forms.TextInput(attrs={"class": TEXT_CLASS}),
            "description": forms.Textarea(attrs={"class": TEXT_CLASS, "rows": 4}),
            "office_location": forms.TextInput(attrs={"class": TEXT_CLASS}),
            "contact_email": forms.EmailInput(attrs={"class": TEXT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
        }

    def clean_code(self):
        value = self.cleaned_data["code"].strip().upper()
        if not value:
            raise ValidationError("Department code is required.")
        if not value.replace("-", "").replace("_", "").isalnum():
            raise ValidationError("Use letters, numbers, '-' or '_' only.")
        duplicate = Department.objects.filter(code__iexact=value)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise ValidationError(f"Department code '{value}' is already in use.")
        return value

    def clean_name(self):
        value = self.cleaned_data["name"].strip()
        duplicate = Department.objects.filter(name__iexact=value)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise ValidationError("A department with this name already exists.")
        return value


class DepartmentFacultyEditForm(forms.ModelForm):
    """Faculty form - only the three descriptive fields may be changed.

    The department code, the department name and the faculty assignments
    are intentionally missing: they are administrative fields and are not
    part of this form at all, so they cannot be tampered with by posting
    extra data.
    """

    class Meta:
        model = Department
        fields = ["description", "office_location", "contact_email"]
        widgets = {
            "description": forms.Textarea(attrs={"class": TEXT_CLASS, "rows": 4}),
            "office_location": forms.TextInput(attrs={"class": TEXT_CLASS}),
            "contact_email": forms.EmailInput(attrs={"class": TEXT_CLASS}),
        }

    def clean_contact_email(self):
        value = self.cleaned_data.get("contact_email", "").strip()
        if value:
            validate_email(value)
        return value


class FacultyCreateForm(forms.Form):
    """Creates a faculty account together with its profile.

    The role is decided by the view (it adds the user to the ``Faculty``
    group), it is never taken from the submitted data.
    """

    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": TEXT_CLASS}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": TEXT_CLASS}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": TEXT_CLASS}))
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": TEXT_CLASS}))
    employee_id = forms.CharField(
        max_length=20, widget=forms.TextInput(attrs={"class": TEXT_CLASS})
    )
    designation = forms.CharField(
        max_length=60,
        required=False,
        widget=forms.TextInput(attrs={"class": TEXT_CLASS}),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": TEXT_CLASS}),
    )
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Departments this faculty member may edit.",
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": TEXT_CLASS, "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": TEXT_CLASS, "autocomplete": "new-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["departments"].queryset = Department.objects.filter(is_active=True)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_employee_id(self):
        employee_id = self.cleaned_data["employee_id"].strip().upper()
        if FacultyProfile.objects.filter(employee_id__iexact=employee_id).exists():
            raise ValidationError("This employee ID is already in use.")
        return employee_id

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")
        return cleaned

    def save(self):
        """Create the user, the profile and the group membership."""
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            first_name=self.cleaned_data["first_name"].strip(),
            last_name=self.cleaned_data["last_name"].strip(),
            is_active=True,
        )
        profile = FacultyProfile.objects.create(
            user=user,
            employee_id=self.cleaned_data["employee_id"],
            designation=self.cleaned_data.get("designation", "").strip(),
            phone=self.cleaned_data.get("phone", "").strip(),
        )
        profile.departments.set(self.cleaned_data.get("departments") or [])
        faculty_group, _ = Group.objects.get_or_create(name="Faculty")
        user.groups.add(faculty_group)
        return profile


class FacultyUpdateForm(forms.ModelForm):
    """Updates a faculty profile and the state of the linked account."""

    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Departments this faculty member may edit.",
    )
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": TEXT_CLASS}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": TEXT_CLASS}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": TEXT_CLASS}))
    is_active = forms.BooleanField(
        required=False,
        label="Account active",
        help_text="An inactive account cannot sign in or use the portal.",
        widget=forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
    )
    new_password = forms.CharField(
        label="New password (optional)",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": TEXT_CLASS, "autocomplete": "new-password"}
        ),
        help_text="Leave empty to keep the current password.",
    )

    class Meta:
        model = FacultyProfile
        fields = ["employee_id", "designation", "phone"]
        widgets = {
            "employee_id": forms.TextInput(attrs={"class": TEXT_CLASS}),
            "designation": forms.TextInput(attrs={"class": TEXT_CLASS}),
            "phone": forms.TextInput(attrs={"class": TEXT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["departments"].queryset = Department.objects.filter(is_active=True)
        if self.instance and self.instance.pk:
            self.fields["departments"].initial = self.instance.departments.all()
            user = self.instance.user
            self.fields["email"].initial = user.email
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["is_active"].initial = user.is_active

    def clean_employee_id(self):
        employee_id = self.cleaned_data["employee_id"].strip().upper()
        duplicate = FacultyProfile.objects.filter(employee_id__iexact=employee_id)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise ValidationError("This employee ID is already in use.")
        return employee_id

    def save(self):
        profile = super().save()
        profile.departments.set(self.cleaned_data.get("departments") or [])
        user = profile.user
        user.email = self.cleaned_data.get("email", "").strip()
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.is_active = bool(self.cleaned_data.get("is_active"))
        new_password = self.cleaned_data.get("new_password")
        if new_password:
            user.set_password(new_password)
        user.save()
        return profile


class StudentAccountCreateForm(forms.Form):
    """Creates a login account for a student record."""

    student = forms.ModelChoiceField(
        queryset=Students.objects.none(),
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
        help_text="Only students without an account are listed.",
    )
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": TEXT_CLASS}))
    email = forms.EmailField(
        required=False, widget=forms.EmailInput(attrs={"class": TEXT_CLASS})
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": TEXT_CLASS, "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": TEXT_CLASS, "autocomplete": "new-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = Students.objects.filter(account__isnull=True)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        if Students.objects.filter(student_id__iexact=username).exists():
            raise ValidationError(
                "This username is already used as a student ID, please pick another one."
            )
        return username

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")
        return cleaned

    def save(self):
        student = self.cleaned_data["student"]
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data.get("email", "").strip(),
            password=self.cleaned_data["password1"],
            first_name=student.student_name,
            is_active=True,
        )
        student_group, _ = Group.objects.get_or_create(name="Student")
        user.groups.add(student_group)
        student.account = user
        student.save(update_fields=["account", "updated_at"])
        return user


class StudentAccountUpdateForm(forms.Form):
    """Updates an existing student login account."""

    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": TEXT_CLASS}))
    email = forms.EmailField(
        required=False, widget=forms.EmailInput(attrs={"class": TEXT_CLASS})
    )
    is_active = forms.BooleanField(
        required=False,
        label="Account active",
        widget=forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
    )
    new_password = forms.CharField(
        label="New password (optional)",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": TEXT_CLASS, "autocomplete": "new-password"}
        ),
    )

    def __init__(self, *args, **kwargs):
        # This is a plain form (not a model form), so the account that is
        # being edited is handed over as ``instance``.
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["username"].initial = self.instance.username
            self.fields["email"].initial = self.instance.email
            self.fields["is_active"].initial = self.instance.is_active

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        duplicate = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise ValidationError("This username is already taken.")
        return username

    def save(self):
        user = self.instance
        user.username = self.cleaned_data["username"]
        user.email = self.cleaned_data.get("email", "").strip()
        user.is_active = bool(self.cleaned_data.get("is_active"))
        new_password = self.cleaned_data.get("new_password")
        if new_password:
            user.set_password(new_password)
        user.save()
        return user


class CorrectionRequestForm(forms.ModelForm):
    """Lets a student ask for a correction to their own record.

    Submitting the form creates a *request* only.  The official student row
    is never changed here - an admin has to review and approve it.
    """

    class Meta:
        model = CorrectionRequest
        fields = ["field_name", "requested_value", "reason"]
        widgets = {
            "field_name": forms.Select(attrs={"class": SELECT_CLASS}),
            "requested_value": forms.TextInput(attrs={"class": TEXT_CLASS}),
            "reason": forms.Textarea(attrs={"class": TEXT_CLASS, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requested_value"].widget.attrs.update({"class": TEXT_CLASS})
        self.fields["reason"].help_text = (
            "Explain why the record should be corrected."
        )

    def clean_requested_value(self):
        value = self.cleaned_data["requested_value"].strip()
        if not value:
            raise ValidationError("Enter the value that should be used.")
        if len(value) > 120:
            raise ValidationError("Please use 120 characters or fewer.")
        return value


class CorrectionReviewForm(forms.Form):
    """Admin decision on a pending correction request."""

    decision = forms.ChoiceField(
        choices=[("approved", "Approve"), ("rejected", "Reject")],
        widget=forms.RadioSelect,
    )
    admin_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": TEXT_CLASS, "rows": 3}),
        label="Note (optional)",
    )
    apply_change = forms.BooleanField(
        required=False,
        label="Apply the new value to the student record",
        help_text=(
            "Tick this to write the requested value into the official record "
            "straight away."
        ),
        widget=forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
    )


class LoginForm(AuthenticationForm):
    """Django's authentication form with the portal styling applied.

    ``AuthenticationForm`` already handles the "inactive account" and the
    "incorrect credentials" cases, so it is reused instead of writing a
    second login implementation.
    """

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": TEXT_CLASS,
                "autofocus": True,
                "autocomplete": "username",
            }
        )
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"class": TEXT_CLASS, "autocomplete": "current-password"}
        ),
    )

