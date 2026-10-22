"""Management of the student login accounts (admin only).

A student record and a login account are two different things:

* the **student record** holds the official data (name, id, department,
  section, photo) and only an admin may change it,
* the **login account** is the ``auth.User`` row that lets the student
  sign in.

They are connected by the ``Students.account`` one-to-one field, so a
login can only ever point at a single student and a student can only ever
have a single login.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import StudentAccountCreateForm, StudentAccountUpdateForm
from ..models import Students
from ..permissions import admin_required


@admin_required
def student_accounts(request):
    """List of student records with the state of their login account."""
    students = Students.objects.select_related("department", "account").order_by(
        "student_name"
    )
    return render(request, "accounts/list.html", {"students": students})


@admin_required
def student_account_create(request):
    """Admin: create a login account for a student record."""
    if request.method == "POST":
        form = StudentAccountCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Login account '{user.username}' was created.")
            return redirect("student_accounts")
    else:
        form = StudentAccountCreateForm()

    return render(request, "accounts/form.html", {"form": form, "mode": "create"})


@admin_required
def student_account_update(request, pk):
    """Admin: edit the login account of a student record."""
    student = get_object_or_404(Students, pk=pk)
    if not student.account:
        messages.error(
            request,
            f"'{student.student_name}' does not have a login account yet.",
        )
        return redirect("student_accounts")

    if request.method == "POST":
        form = StudentAccountUpdateForm(request.POST, instance=student.account)
        if form.is_valid():
            form.save()
            messages.success(request, "The login account was updated.")
            return redirect("student_accounts")
    else:
        form = StudentAccountUpdateForm(instance=student.account)

    return render(
        request,
        "accounts/form.html",
        {"form": form, "mode": "edit", "student": student},
    )


@admin_required
@require_POST
def student_account_unlink(request, pk):
    """Admin: remove the login account from a student record.

    The student record itself is kept - only the link to the login is
    removed so a new account can be linked later.
    """
    student = get_object_or_404(Students, pk=pk)
    if not student.account:
        messages.info(request, "This student has no login account.")
        return redirect("student_accounts")

    username = student.account.username
    student.account = None
    student.save(update_fields=["account", "updated_at"])
    messages.success(
        request, f"The login '{username}' was unlinked from {student.student_name}."
    )
    return redirect("student_accounts")
