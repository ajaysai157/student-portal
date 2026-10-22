"""Student self service pages.

Everything in this module works on **the signed in student's own record**.
The record is found through the one-to-one link between the account and
the student row - never through a student id that came from the URL or a
form - so a student cannot reach another student's data by changing a
parameter.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..forms import CorrectionRequestForm
from ..models import CorrectionRequest, Department
from ..permissions import active_login_required, admin_required, student_record_for


def current_value(student, field_name):
    """The value that is currently stored for the requested field."""
    if field_name == "department":
        return student.department.name if student.department else ""
    return str(getattr(student, field_name, ""))


@active_login_required
def my_profile(request):
    """The student's own profile page."""
    student = student_record_for(request.user)
    if not student:
        return render(request, "my/no_profile.html", {"student": None})

    return render(
        request,
        "my/profile.html",
        {
            "student": student,
            "department": student.department,
            "corrections": student.correction_requests.all()[:5],
        },
    )


@active_login_required
def my_correction_requests(request):
    """List of the correction requests the student submitted."""
    student = student_record_for(request.user)
    if not student:
        return render(request, "my/no_profile.html", {"student": None})

    if request.method == "POST":
        form = CorrectionRequestForm(request.POST)
        if form.is_valid():
            correction = form.save(commit=False)
            correction.student = student
            correction.submitted_by = request.user
            correction.current_value = current_value(student, correction.field_name)
            correction.save()
            messages.success(
                request,
                "Your request was sent to the administration. It will not change "
                "your record until it is reviewed.",
            )
            return redirect("my_correction_requests")
    else:
        form = CorrectionRequestForm()

    return render(
        request,
        "my/corrections.html",
        {
            "form": form,
            "student": student,
            "requests": student.correction_requests.all(),
        },
    )


@active_login_required
def my_department(request):
    """Public information about the student's own department."""
    student = student_record_for(request.user)
    department = student.department if student else None
    if not department:
        return render(request, "my/no_profile.html", {"student": student})
    return render(request, "my/department.html", {"department": department})


@active_login_required
def department_public_info(request, pk):
    """Read only view of a department, visible to every signed in user."""
    department = get_object_or_404(Department, pk=pk)
    return render(
        request,
        "departments/detail.html",
        {
            "department": department,
            "can_edit": False,
            "change_logs": [],
            "faculty_members": department.faculty_members.select_related("user"),
        },
    )


# ---------------------------------------------------------------------------
# Admin: reviewing the correction requests
# ---------------------------------------------------------------------------


@admin_required
def correction_request_list(request):
    """All correction requests, newest first."""
    requests = CorrectionRequest.objects.select_related(
        "student", "submitted_by"
    ).order_by("-created_at")
    return render(
        request,
        "accounts/corrections.html",
        {"requests": requests},
    )


@admin_required
def correction_request_review(request, pk):
    """Admin: approve or reject a correction request."""
    correction = get_object_or_404(
        CorrectionRequest.objects.select_related("student", "submitted_by"), pk=pk
    )

    if correction.status != "pending":
        messages.info(request, "This request was already reviewed.")
        return redirect("correction_request_list")

    if request.method == "POST":
        decision = request.POST.get("decision")
        note = (request.POST.get("admin_note") or "").strip()
        apply_change = request.POST.get("apply_change") in {"on", "true", "1"}

        if decision not in {"approved", "rejected"}:
            messages.error(request, "Unknown decision.")
        else:
            correction.status = decision
            correction.admin_note = note
            correction.reviewed_by = request.user
            correction.reviewed_at = timezone.now()
            correction.save(
                update_fields=["status", "admin_note", "reviewed_by", "reviewed_at"]
            )

            if decision == "approved" and apply_change:
                applied, error = apply_correction(correction)
                if error:
                    messages.error(request, error)
                else:
                    messages.success(
                        request, "The new value was written to the student record."
                    )

            messages.success(
                request,
                f"The request for {correction.student.student_name} was {decision}.",
            )
            return redirect("correction_request_list")

    return render(
        request,
        "accounts/correction_review.html",
        {"correction": correction},
    )


def apply_correction(correction):
    """Write the requested value into the official student record.

    Returns ``(applied, error_message)``.  This is the only place where a
    student's request is allowed to change the official record, and it is
    always an explicit admin decision.
    """
    student = correction.student
    field = correction.field_name
    value = correction.requested_value

    if field == "department":
        department = Department.objects.filter(name__iexact=value).first()
        if department is None:
            return False, f"There is no department named '{value}'."
        student.department = department
    elif field == "student_section":
        try:
            student.student_section = int(value)
        except (TypeError, ValueError):
            return False, f"'{value}' is not a valid section."
    else:
        student.student_name = value

    student.save()
    return True, ""
