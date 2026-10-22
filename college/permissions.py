"""Role and permission helpers.

The role of a user is **never** read from request data. It is derived from
Django's own data: ``user.is_superuser`` and the Django groups listed in
``college.roles``.

Three groups are used:

``Admin``
    Full control over student records, departments and user accounts.
``Faculty``
    Read only access to every student, plus editing of a *limited set of
    fields* on the departments they are assigned to.
``Student``
    Access to their own student record only.

Every helper here is used by the views, so the same rules are applied no
matter which URL or which HTTP method is used.
"""

from functools import wraps

from django.contrib.auth import SESSION_KEY, logout
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from .models import Department, FacultyProfile, Students

ADMIN_GROUP = "Admin"
FACULTY_GROUP = "Faculty"
STUDENT_GROUP = "Student"

ROLE_ADMIN = "admin"
ROLE_FACULTY = "faculty"
ROLE_STUDENT = "student"


def _in_group(user, group_name):
    return user.is_superuser or user.groups.filter(name=group_name).exists()


def is_admin(user):
    """True for superusers and members of the ``Admin`` group."""
    return bool(user and user.is_authenticated and _in_group(user, ADMIN_GROUP))


def is_faculty(user):
    """True for members of the ``Faculty`` group."""
    return bool(user and user.is_authenticated and _in_group(user, FACULTY_GROUP))


def is_student(user):
    """True for members of the ``Student`` group."""
    return bool(user and user.is_authenticated and _in_group(user, STUDENT_GROUP))


def role_of(user):
    """Return the primary role of ``user`` or ``None``.

    Superusers are treated as admins. If a user somehow belongs to more
    than one group, the most privileged role wins.
    """
    if not user or not user.is_authenticated:
        return None
    if is_admin(user):
        return ROLE_ADMIN
    if is_faculty(user):
        return ROLE_FACULTY
    if is_student(user):
        return ROLE_STUDENT
    return None


def faculty_profile_for(user):
    """Return the ``FacultyProfile`` of ``user`` or ``None``."""
    if not user or not user.is_authenticated:
        return None
    return FacultyProfile.objects.filter(user=user).first()


def faculty_departments(user):
    """Departments the given faculty member is assigned to."""
    profile = faculty_profile_for(user)
    if not profile:
        return Department.objects.none()
    return profile.departments.all()


def faculty_can_edit_department(user, department):
    """Object level check used by the department edit view.

    Faculty may only edit departments they are assigned to. Admin may edit
    every department.
    """
    if not user or not user.is_authenticated:
        return False
    if is_admin(user):
        return True
    if not is_faculty(user):
        return False
    return faculty_departments(user).filter(pk=department.pk).exists()


def student_record_for(user):
    """Return the student record linked to the logged in user.

    The record is looked up through the one-to-one link, never through a
    student id coming from the URL or a form.
    """
    if not user or not user.is_authenticated:
        return None
    record = Students.objects.filter(account=user).first()
    if record:
        return record
    # Fallback for accounts that were created before the link existed.
    return Students.objects.filter(student_id__iexact=user.username).first()


def student_owns(user, student):
    """True when ``student`` is the record linked to ``user``."""
    if not user or not user.is_authenticated or student is None:
        return False
    record = student_record_for(user)
    return bool(record and record.pk == student.pk)


def _login_guard(request):
    """Return a redirect response when the visitor may not continue.

    ``None`` means the request may go on.  Anonymous visitors are sent to
    the login page (with a ``next`` parameter).

    Django's authentication backend refuses to load a *deactivated* account,
    so ``request.user`` is an ``AnonymousUser`` in that case even though the
    session still holds the user id.  The stale session is dropped here,
    otherwise the browser would keep the dead cookie around and the login
    page would bounce between the dashboard and the sign in form.
    """
    if not request.user.is_authenticated:
        if request.session.get(SESSION_KEY):
            logout(request)
        return redirect(f"{reverse('login')}?next={request.get_full_path()}")
    if not request.user.is_active:
        logout(request)
        return redirect(f"{reverse('login')}?next={request.get_full_path()}")
    return None


def role_required(*roles):
    """View decorator enforcing that the user holds one of ``roles``.

    * anonymous visitors are redirected to the login page (with ``next``)
    * authenticated users without the role get a 403 permission denied
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            denied = _login_guard(request)
            if denied is not None:
                return denied
            if role_of(request.user) not in roles:
                raise PermissionDenied("You do not have permission to access this page.")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def active_login_required(view_func):
    """Like ``django.contrib.auth.decorators.login_required`` but an
    account that has been deactivated is signed out instead of being let
    in."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        denied = _login_guard(request)
        if denied is not None:
            return denied
        return view_func(request, *args, **kwargs)

    return wrapper


def admin_required(view_func):
    return role_required(ROLE_ADMIN)(view_func)


def faculty_required(view_func):
    return role_required(ROLE_FACULTY)(view_func)


def student_required(view_func):
    return role_required(ROLE_STUDENT)(view_func)


def staff_or_faculty_required(view_func):
    """Used by pages shared by admin and faculty (student directory)."""
    return role_required(ROLE_ADMIN, ROLE_FACULTY)(view_func)


def ensure_groups():
    """Create the three role groups if they do not exist yet.

    Used by the data migration and by the ``bootstrap`` management command
    so a fresh checkout always has the expected groups.
    """
    for name in (ADMIN_GROUP, FACULTY_GROUP, STUDENT_GROUP):
        Group.objects.get_or_create(name=name)


def assign_role_permissions(**kwargs):
    """Give each role group the permissions it is allowed to use.

    Called from the ``post_migrate`` signal because Django only creates the
    ``auth_permission`` rows *after* the migrations have run - a plain data
    migration would run too early to see them.

    * **Admin** gets full control over the portal models.
    * **Faculty** may read every student and may edit the departments they
      are assigned to.  Which *fields* of a department faculty may change is
      enforced by ``college.forms`` and ``college.permissions``.
    * **Student** gets no model permissions on purpose.  A student reaches
      their own record through the one-to-one account link and the views
      check that ownership explicitly, which is safer than a blanket
      ``view_students`` permission.
    """
    from django.contrib.auth.models import Permission

    ensure_groups()

    admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    faculty_group, _ = Group.objects.get_or_create(name=FACULTY_GROUP)

    admin_permissions = Permission.objects.filter(
        content_type__app_label="college"
    )
    admin_group.permissions.set(admin_permissions)

    faculty_permissions = Permission.objects.filter(
        content_type__app_label="college",
        codename__in=[
            "view_students",
            "view_department",
            "change_department",
            "view_facultyprofile",
        ],
    )
    faculty_group.permissions.set(faculty_permissions)

