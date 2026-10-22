"""Template helpers of the College Management Portal."""

from django import template

from ..avatars import student_avatar_url, user_avatar_url

register = template.Library()


@register.simple_tag
def student_avatar(student):
    """URL of the picture of a student.

    Falls back to the default avatar of the gender when no photo was
    uploaded.
    """
    if student is None:
        return ""
    return student_avatar_url(student)


@register.simple_tag
def user_avatar(user):
    """URL of the picture of a signed in user (any role)."""
    return user_avatar_url(user)


@register.filter
def initials(value):
    """First letters of a name, used as a text fallback."""
    text = (value or "").strip()
    if not text:
        return ""
    parts = [part for part in text.split() if part]
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][:1] + parts[-1][:1]).upper()
