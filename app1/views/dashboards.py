"""Role specific dashboards.

``dashboard`` sends the signed in user to the dashboard of their role.
Each role gets its own template because the information structure is
different: an admin manages the college, a faculty member browses
students, a student only cares about their own record.
"""

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from ..models import CorrectionRequest, FacultyProfile, Students
from ..permissions import (
    ROLE_ADMIN,
    ROLE_FACULTY,
    ROLE_STUDENT,
    active_login_required,
    faculty_departments,
    role_of,
    student_record_for,
)
from .common import college_stats


@active_login_required
def dashboard(request):
    """Send the user to the dashboard that matches their role."""
    role = role_of(request.user)
    if role == ROLE_ADMIN:
        return redirect("admin_dashboard")
    if role == ROLE_FACULTY:
        return redirect("faculty_dashboard")
    if role == ROLE_STUDENT:
        return redirect("student_dashboard")
    # Signed in but without a role: show the account overview instead of
    # an empty page.
    return redirect("account_overview")


@active_login_required
def admin_dashboard(request):
    """College wide overview for administrators."""
    from ..permissions import is_admin

    if not is_admin(request.user):
        raise PermissionDenied("Only administrators can view this dashboard.")

    stats = college_stats()
    stats["total_faculty"] = FacultyProfile.objects.count()
    stats["active_faculty"] = FacultyProfile.objects.filter(user__is_active=True).count()
    stats["students_with_account"] = Students.objects.filter(
        account__isnull=False
    ).count()
    stats["pending_corrections"] = CorrectionRequest.objects.filter(
        status="pending"
    ).count()
    return render(request, "dashboard/admin.html", stats)


@active_login_required
def faculty_dashboard(request):
    """College wide numbers for faculty members."""
    from ..permissions import is_faculty

    if not is_faculty(request.user):
        raise PermissionDenied("Only faculty members can view this dashboard.")

    stats = college_stats()
    stats["my_departments"] = faculty_departments(request.user)
    stats["my_student_count"] = Students.objects.filter(
        department__in=stats["my_departments"]
    ).count()
    return render(request, "dashboard/faculty.html", stats)


@active_login_required
def student_dashboard(request):
    """Personal overview for a student."""
    from ..permissions import is_student

    if not is_student(request.user):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied("Only students can view this dashboard.")

    student = student_record_for(request.user)
    context = {
        "student": student,
        "department": student.department if student else None,
        "pending_corrections": (
            student.correction_requests.filter(status="pending").count()
            if student
            else 0
        ),
    }
    return render(request, "dashboard/student.html", context)
