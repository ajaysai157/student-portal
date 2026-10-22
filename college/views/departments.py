"""Department views.

Two rules drive the design of this module:

* Everyone who is signed in may **look at** the department directory.
* Only an administrator may change every field of a department.  A faculty
  member may change *three* descriptive fields, and only on the
  departments they are assigned to.

The faculty edit uses a different form (``DepartmentFacultyEditForm``)
that does not even contain the administrative fields, so a crafted POST
request cannot set them.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import DepartmentFacultyEditForm, DepartmentForm
from ..models import Department, DepartmentChangeLog
from ..permissions import (
    ROLE_ADMIN,
    ROLE_FACULTY,
    active_login_required,
    admin_required,
    faculty_can_edit_department,
    faculty_departments,
    is_admin,
    role_of,
)


def _record_change(department, action, changes, user):
    """Write one entry into the department audit trail."""
    DepartmentChangeLog.objects.create(
        department=department,
        changed_by=user if user.is_authenticated else None,
        action=action,
        changes=changes or {},
    )


def _department_changes(department, form):
    """Compare the submitted values with the stored ones.

    The old value is taken from ``form.initial`` - the snapshot that was
    taken when the form was built.  The model instance itself cannot be
    used for this, because validating the form already writes the new
    values onto it.
    """
    changes = {}
    for field in form.changed_data:
        old = form.initial.get(field)
        if old is None:
            old = getattr(department, field, None)
        new = form.cleaned_data.get(field)
        if str(old or "") != str(new or ""):
            changes[field] = {"from": str(old or ""), "to": str(new or "")}
    return changes


@active_login_required
def department_list(request):
    """Department directory.

    Everyone who is signed in may look at the directory.  Only an
    administrator sees the "new department" button; a faculty member only
    gets an edit link for the departments assigned to them.
    """
    departments = Department.objects.all().order_by("name")
    return render(
        request,
        "departments/list.html",
        {
            "departments": departments,
            "total_students": sum(d.students.count() for d in departments),
            "my_departments": faculty_departments(request.user),
        },
    )


@active_login_required
def department_detail(request, pk):
    """Read only view of a single department."""
    department = get_object_or_404(Department, pk=pk)
    can_edit = faculty_can_edit_department(request.user, department)
    return render(
        request,
        "departments/detail.html",
        {
            "department": department,
            "can_edit": can_edit,
            "change_logs": department.change_logs.select_related("changed_by")[:10],
            "faculty_members": department.faculty_members.select_related("user"),
        },
    )


@admin_required
def department_create(request):
    """Admin: create a department."""
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            _record_change(department, "created", {"name": department.name}, request.user)
            messages.success(request, f"Department '{department.name}' was created.")
            return redirect("department_detail", pk=department.pk)
    else:
        form = DepartmentForm()
    return render(request, "departments/form.html", {"form": form, "mode": "create"})


def department_edit(request, pk):
    """Edit a department - full form for admins, limited form for faculty."""
    department = get_object_or_404(Department, pk=pk)

    if not request.user.is_authenticated:
        from django.urls import reverse

        return redirect(f"{reverse('login')}?next={request.get_full_path()}")

    role = role_of(request.user)

    if role == ROLE_ADMIN:
        form_class = DepartmentForm
    elif role == ROLE_FACULTY:
        if not faculty_can_edit_department(request.user, department):
            raise PermissionDenied(
                "You can only edit the departments you are assigned to."
            )
        form_class = DepartmentFacultyEditForm
    else:
        raise PermissionDenied("You do not have permission to edit departments.")

    if request.method == "POST":
        form = form_class(request.POST, instance=department)
        if form.is_valid():
            changes = _department_changes(department, form)
            form.save()
            if changes:
                action = "updated"
                if "is_active" in changes:
                    action = (
                        "deactivated"
                        if department.is_active is False
                        else "reactivated"
                    )
                _record_change(department, action, changes, request.user)
                messages.success(
                    request, f"Department '{department.name}' was updated."
                )
            else:
                messages.info(request, "Nothing was changed.")
            return redirect("department_detail", pk=department.pk)
    else:
        form = form_class(instance=department)

    return render(
        request,
        "departments/form.html",
        {
            "form": form,
            "mode": "edit",
            "department": department,
            "is_admin": is_admin(request.user),
        },
    )


@admin_required
@require_POST
def department_delete(request, pk):
    """Admin: delete a department.

    A department that still has students or faculty attached cannot be
    deleted - those records have to be reassigned or the department has to
    be deactivated instead.
    """
    department = get_object_or_404(Department, pk=pk)
    name = department.name

    student_count = department.students.count()
    faculty_count = department.faculty_members.count()

    if student_count or faculty_count:
        messages.error(
            request,
            f"'{name}' still has {student_count} student(s) and "
            f"{faculty_count} faculty member(s) attached. Reassign them or "
            "deactivate the department instead of deleting it.",
        )
        return redirect("department_detail", pk=pk)

    try:
        department.delete()
    except ProtectedError:
        messages.error(
            request,
            f"'{name}' cannot be deleted while other records point to it.",
        )
        return redirect("department_detail", pk=pk)

    messages.success(request, f"Department '{name}' was deleted.")
    return redirect("department_list")


@admin_required
def department_delete_confirmation(request, pk):
    """Confirmation page shown before deleting a department."""
    department = get_object_or_404(Department, pk=pk)
    return render(
        request,
        "departments/confirm_delete.html",
        {
            "department": department,
            "student_count": department.students.count(),
            "faculty_count": department.faculty_members.count(),
        },
    )


@admin_required
@require_POST
def department_toggle_active(request, pk):
    """Admin: activate or deactivate a department."""
    department = get_object_or_404(Department, pk=pk)
    department.is_active = not department.is_active
    department.save(update_fields=["is_active", "updated_at"])
    action = "reactivated" if department.is_active else "deactivated"
    _record_change(
        department,
        action,
        {"is_active": {"from": not department.is_active, "to": department.is_active}},
        request.user,
    )
    messages.success(
        request,
        f"Department '{department.name}' was {'activated' if department.is_active else 'deactivated'}.",
    )
    return redirect("department_detail", pk=pk)
