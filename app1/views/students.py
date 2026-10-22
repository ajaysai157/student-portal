"""Student directory and the admin only student CRUD screens.

The directory (``student_directory`` / ``student_detail``) is shared by
administrators and faculty members.  Every screen that *changes* a student
record is restricted to administrators, and the restriction is enforced in
the view - hiding the button in the template is only a convenience.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import StudentRegisterForm, StudentUpdateForm
from ..models import Department, Students
from ..permissions import admin_required, is_admin, staff_or_faculty_required
from .common import active_filter_values, filtered_students, paginate


@staff_or_faculty_required
def student_directory(request):
    """Searchable, filterable and paginated list of all students."""
    queryset = filtered_students(request)
    context = {
        "departments": Department.objects.filter(is_active=True).order_by("name"),
        "sections": Students.SECTION_CHOICES,
    }
    context.update(paginate(request, queryset))
    context.update(active_filter_values(request))
    return render(request, "students/directory.html", context)


@staff_or_faculty_required
def student_detail(request, student_id):
    """Read only profile of a single student."""
    student = get_object_or_404(
        Students.objects.select_related("department"), student_id=student_id
    )
    return render(
        request,
        "students/detail.html",
        {"student": student, "can_edit": is_admin(request.user)},
    )


@admin_required
def register_student(request):
    """Admin: register a new student."""
    if request.method == "POST":
        form = StudentRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save()
            messages.success(
                request, f"Student '{student.student_name}' was registered."
            )
            return redirect("student_detail", student_id=student.student_id)
    else:
        form = StudentRegisterForm()

    if not Department.objects.filter(is_active=True).exists():
        messages.warning(
            request,
            "There is no active department yet. Create a department before "
            "registering students.",
        )

    return render(request, "students/form.html", {"form": form, "mode": "create"})


@admin_required
def update_student(request, student_id):
    """Admin: edit an existing student record."""
    student = get_object_or_404(Students, student_id=student_id)

    # The name of the current photo is remembered *before* the form is
    # validated: validating a form with a new upload replaces the file on
    # the instance, so afterwards the old name is gone.
    old_photo_name = student.student_image.name if student.student_image else None

    if request.method == "POST":
        form = StudentUpdateForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            if old_photo_name and old_photo_name != student.student_image.name:
                # The photo was replaced - remove the old file so the
                # media folder does not fill up with orphans.
                student.student_image.storage.delete(old_photo_name)
            messages.success(
                request, f"Student '{student.student_name}' was updated."
            )
            return redirect("student_detail", student_id=student.student_id)
    else:
        form = StudentUpdateForm(instance=student)

    return render(
        request,
        "students/form.html",
        {"form": form, "mode": "edit", "student": student},
    )


@admin_required
@require_POST
def delete_student(request, student_id):
    """Admin: delete a student record (POST only, with confirmation)."""
    student = get_object_or_404(Students, student_id=student_id)
    name = student.student_name
    photo = student.student_image

    student.delete()

    if photo:
        photo.delete(save=False)

    messages.success(request, f"Student '{name}' was deleted.")
    return redirect("student_directory")


@admin_required
def student_delete_confirmation(request, student_id):
    """Confirmation page shown before a destructive delete."""
    student = get_object_or_404(Students, student_id=student_id)
    return render(request, "students/confirm_delete.html", {"student": student})

