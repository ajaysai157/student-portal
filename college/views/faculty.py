"""Faculty account management (admin only).

Faculty accounts are created here - never through a public sign up form.
The role is decided by the server: the view adds the new account to the
``Faculty`` group, the submitted form data never decides a role.
"""

from django.contrib import messages
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import FacultyCreateForm, FacultyUpdateForm
from ..models import FacultyProfile
from ..permissions import admin_required


@admin_required
def faculty_list(request):
    """All faculty members with their department assignments."""
    faculty = FacultyProfile.objects.select_related("user").prefetch_related(
        "departments"
    )
    return render(request, "faculty/list.html", {"faculty_members": faculty})


@admin_required
def faculty_detail(request, pk):
    """Read only profile of a faculty member."""
    profile = get_object_or_404(
        FacultyProfile.objects.select_related("user").prefetch_related("departments"),
        pk=pk,
    )
    group_names = list(profile.user.groups.values_list("name", flat=True))
    return render(
        request,
        "faculty/detail.html",
        {
            "profile": profile,
            "group_names": group_names,
            "is_admin_role": "Admin" in group_names,
        },
    )


@admin_required
def faculty_create(request):
    """Admin: create a faculty account and assign departments."""
    if request.method == "POST":
        form = FacultyCreateForm(request.POST)
        if form.is_valid():
            profile = form.save()
            messages.success(
                request,
                f"Faculty account '{profile.user.username}' was created.",
            )
            return redirect("faculty_detail", pk=profile.pk)
    else:
        form = FacultyCreateForm()

    return render(request, "faculty/form.html", {"form": form, "mode": "create"})


@admin_required
def faculty_update(request, pk):
    """Admin: edit a faculty profile, its departments and its status."""
    profile = get_object_or_404(FacultyProfile, pk=pk)

    if request.method == "POST":
        form = FacultyUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Faculty account '{profile.user.username}' was updated.",
            )
            return redirect("faculty_detail", pk=profile.pk)
    else:
        form = FacultyUpdateForm(instance=profile)

    return render(
        request,
        "faculty/form.html",
        {"form": form, "mode": "edit", "profile": profile},
    )


@admin_required
@require_POST
def faculty_toggle_active(request, pk):
    """Admin: activate or deactivate a faculty account.

    A deactivated account is refused by Django's authentication backend
    and is also blocked by the role decorator while the session is alive.
    """
    profile = get_object_or_404(FacultyProfile, pk=pk)
    user = profile.user
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])

    messages.success(
        request,
        f"Account '{user.username}' was "
        f"{'activated' if user.is_active else 'deactivated'}.",
    )
    return redirect("faculty_detail", pk=profile.pk)


@admin_required
@require_POST
def faculty_change_role(request, pk):
    """Admin: move a faculty account between the Faculty and Admin groups.

    The new role comes from the URL, not from a free form field, and it is
    validated against the list of known portal groups.
    """
    profile = get_object_or_404(FacultyProfile, pk=pk)
    target = request.POST.get("role")

    if target not in {"Faculty", "Admin"}:
        messages.error(request, "Unknown role.")
        return redirect("faculty_detail", pk=profile.pk)

    user = profile.user
    faculty_group = Group.objects.get(name="Faculty")
    admin_group = Group.objects.get(name="Admin")

    if target == "Admin":
        user.groups.remove(faculty_group)
        user.groups.add(admin_group)
    else:
        user.groups.remove(admin_group)
        user.groups.add(faculty_group)

    messages.success(request, f"'{user.username}' is now a {target}.")
    return redirect("faculty_detail", pk=profile.pk)
