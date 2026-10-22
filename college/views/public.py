"""Public pages and the authentication workflow."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import (
    PasswordChangeView,
    PasswordChangeDoneView,
)
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from ..forms import FacultySelfServiceForm, LoginForm, ProfilePhotoForm
from ..models import UserProfile
from ..permissions import (
    ROLE_ADMIN,
    ROLE_FACULTY,
    ROLE_STUDENT,
    active_login_required,
    faculty_profile_for,
    role_of,
)


def landing(request):
    """Public landing page.

    Signed in users are sent straight to their dashboard.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


def login_view(request):
    """Sign in page.

    Uses Django's authentication backend, so passwords are checked with the
    configured hasher and inactive accounts are rejected.
    """
    if request.user.is_authenticated:
        if request.user.is_active:
            return redirect("dashboard")
        # The account was deactivated while the session was alive - drop the
        # session so the sign in form is shown again.
        logout(request)

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_short_name() or user.username}!")
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect("dashboard")
    else:
        form = LoginForm(request)

    return render(
        request,
        "registration/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


@require_POST
def logout_view(request):
    """Sign out.

    Only a POST is accepted so the logout cannot be triggered by a
    third-party page loading an image or a link.
    """
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("landing")


class PortalPasswordChangeView(PasswordChangeView):
    """Let a signed in user change their own password."""

    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("password_change_done")


class PortalPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "registration/password_change_done.html"


@active_login_required
def account_overview(request):
    """Small page listing what the signed in user is allowed to do.

    It is also the place where a member of staff uploads their own photo:
    a faculty member edits their faculty profile, everybody else gets a
    ``UserProfile`` row.
    """
    role = role_of(request.user)
    context = {
        "role": role,
        "role_label": {
            ROLE_ADMIN: "Administrator",
            ROLE_FACULTY: "Faculty member",
            ROLE_STUDENT: "Student",
        }.get(role, "User"),
    }

    profile = faculty_profile_for(request.user)
    if profile is not None:
        # A faculty member keeps their picture in the faculty profile.
        form = FacultySelfServiceForm(
            request.POST or None, request.FILES or None, instance=profile
        )
    elif role == ROLE_STUDENT:
        # The picture of a student is maintained by the administration.
        form = None
    else:
        instance = (
            UserProfile.objects.filter(user=request.user).first()
            or UserProfile(user=request.user)
        )
        form = ProfilePhotoForm(
            request.POST or None,
            request.FILES or None,
            instance=instance,
            user=request.user,
        )

    context["profile_form"] = form

    if request.method == "POST" and form is not None:
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("account_overview")

    return render(request, "account_overview.html", context)
