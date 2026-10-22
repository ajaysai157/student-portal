"""URL routing for the College Management Portal.

Every URL has a name so templates can use ``{% url %}`` instead of hard
coded paths.  The permission rules live in the views - the URL layout only
makes the routes easy to read.
"""

from django.urls import path

from . import views

urlpatterns = [
    # --- public ---------------------------------------------------------
    path("", views.landing, name="landing"),
    # --- authentication --------------------------------------------------
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path(
        "accounts/password-change/",
        views.PortalPasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "accounts/password-change/done/",
        views.PortalPasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path("accounts/overview/", views.account_overview, name="account_overview"),
    # --- dashboards ------------------------------------------------------
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/faculty/", views.faculty_dashboard, name="faculty_dashboard"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    # --- students (directory is shared by admin + faculty) ----------------
    path("students/", views.student_directory, name="student_directory"),
    path("students/new/", views.register_student, name="register_student"),
    path(
        "students/<str:student_id>/",
        views.student_detail,
        name="student_detail",
    ),
    path(
        "students/<str:student_id>/edit/",
        views.update_student,
        name="update_student",
    ),
    path(
        "students/<str:student_id>/delete/",
        views.student_delete_confirmation,
        name="student_delete_confirmation",
    ),
    path(
        "students/<str:student_id>/delete/confirm/",
        views.delete_student,
        name="delete_student",
    ),
    # --- departments -----------------------------------------------------
    path("departments/", views.department_list, name="department_list"),
    path("departments/new/", views.department_create, name="department_create"),
    path("departments/<int:pk>/", views.department_detail, name="department_detail"),
    path(
        "departments/<int:pk>/edit/",
        views.department_edit,
        name="department_edit",
    ),
    path(
        "departments/<int:pk>/delete/",
        views.department_delete_confirmation,
        name="department_delete_confirmation",
    ),
    path(
        "departments/<int:pk>/delete/confirm/",
        views.department_delete,
        name="department_delete",
    ),
    path(
        "departments/<int:pk>/toggle-active/",
        views.department_toggle_active,
        name="department_toggle_active",
    ),
    # --- faculty management (admin) --------------------------------------
    path("manage/faculty/", views.faculty_list, name="faculty_list"),
    path("manage/faculty/new/", views.faculty_create, name="faculty_create"),
    path(
        "manage/faculty/<int:pk>/",
        views.faculty_detail,
        name="faculty_detail",
    ),
    path(
        "manage/faculty/<int:pk>/edit/",
        views.faculty_update,
        name="faculty_update",
    ),
    path(
        "manage/faculty/<int:pk>/toggle-active/",
        views.faculty_toggle_active,
        name="faculty_toggle_active",
    ),
    path(
        "manage/faculty/<int:pk>/role/",
        views.faculty_change_role,
        name="faculty_change_role",
    ),
    # --- student login accounts (admin) ----------------------------------
    path("manage/student-accounts/", views.student_accounts, name="student_accounts"),
    path(
        "manage/student-accounts/new/",
        views.student_account_create,
        name="student_account_create",
    ),
    path(
        "manage/student-accounts/<int:pk>/edit/",
        views.student_account_update,
        name="student_account_update",
    ),
    path(
        "manage/student-accounts/<int:pk>/unlink/",
        views.student_account_unlink,
        name="student_account_unlink",
    ),
    # --- correction requests ---------------------------------------------
    path(
        "manage/correction-requests/",
        views.correction_request_list,
        name="correction_request_list",
    ),
    path(
        "manage/correction-requests/<int:pk>/",
        views.correction_request_review,
        name="correction_request_review",
    ),
    # --- student self service --------------------------------------------
    path("my/profile/", views.my_profile, name="my_profile"),
    path(
        "my/correction-requests/",
        views.my_correction_requests,
        name="my_correction_requests",
    ),
    path("my/department/", views.my_department, name="my_department"),
]
