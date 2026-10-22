"""Template context shared by every page.

Exposes the current user's role so the navigation can show the right
menu.  The menu is only a convenience - the views are the real access
control.
"""

from . import permissions


def portal_context(request):
    user = getattr(request, "user", None)
    role = permissions.role_of(user)
    return {
        "portal_role": role,
        "is_admin": role == permissions.ROLE_ADMIN,
        "is_faculty": role == permissions.ROLE_FACULTY,
        "is_student": role == permissions.ROLE_STUDENT,
    }
