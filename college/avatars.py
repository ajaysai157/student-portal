"""Default avatars for every role of the portal.

Every person in the portal has a picture: the uploaded photo when there is
one, otherwise a default avatar.  The default depends on the role - a
student gets the avatar of their gender, a faculty member and an
administrator get their own.

The default avatars are small SVG files in
``college/static/college/images/avatars/``.  They are part of the static
files, so they are served by the web server and never touch the database.
"""

from django.templatetags.static import static

AVATAR_DIR = "college/images/avatars/"

#: Default avatar of a student, by gender.
STUDENT_AVATARS = {
    "male": AVATAR_DIR + "student-male.svg",
    "female": AVATAR_DIR + "student-female.svg",
    "other": AVATAR_DIR + "student-neutral.svg",
    "unspecified": AVATAR_DIR + "student-neutral.svg",
}

#: Default avatars of the staff roles.
FACULTY_AVATAR = AVATAR_DIR + "faculty.svg"
ADMIN_AVATAR = AVATAR_DIR + "admin.svg"
USER_AVATAR = AVATAR_DIR + "user.svg"


def student_avatar_path(gender):
    """Static path of the default avatar of a student with that gender."""
    return STUDENT_AVATARS.get((gender or "").strip().lower(), STUDENT_AVATARS["unspecified"])


def student_avatar_url(student):
    """URL of the picture of a student (uploaded photo or default avatar)."""
    photo = getattr(student, "photo_url", None)
    if photo:
        return photo
    return static(student_avatar_path(getattr(student, "gender", "")))


def faculty_avatar_url(profile):
    """URL of the picture of a faculty member (uploaded photo or default)."""
    photo = getattr(profile, "photo_url", None)
    if photo:
        return photo
    return static(FACULTY_AVATAR)


def user_avatar_url(user):
    """URL of the picture of any signed in user.

    The uploaded photo wins, then the default avatar of the role the user
    has in the portal.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return static(USER_AVATAR)

    # The imports are done here to keep this module free of import loops.
    from .models import FacultyProfile, UserProfile
    from .permissions import is_admin, is_faculty, is_student

    profile = FacultyProfile.objects.filter(user=user).first()
    if profile is not None:
        return faculty_avatar_url(profile)

    user_profile = UserProfile.objects.filter(user=user).first()
    if user_profile is not None and user_profile.photo_url:
        return user_profile.photo_url

    if is_admin(user):
        return static(ADMIN_AVATAR)
    if is_faculty(user):
        return static(FACULTY_AVATAR)
    if is_student(user):
        return static(STUDENT_AVATARS["unspecified"])
    return static(USER_AVATAR)
