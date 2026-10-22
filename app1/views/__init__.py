"""Views of the College Management Portal.

The package is split by responsibility so every file stays small:

``public``       landing page, login, logout, password change
``dashboards``   the three role dashboards
``students``     student directory (admin + faculty) and admin student CRUD
``departments``  department directory and the role aware edit screens
``faculty``      faculty account management (admin only)
``accounts``     student login accounts (admin only)
``portal``       student self service and the correction request workflow
``common``       shared helpers (statistics, search, pagination)
"""

from .accounts import (  # noqa: F401
    student_account_create,
    student_account_unlink,
    student_account_update,
    student_accounts,
)
from .common import college_stats, filtered_students, paginate  # noqa: F401
from .dashboards import (  # noqa: F401
    admin_dashboard,
    dashboard,
    faculty_dashboard,
    student_dashboard,
)
from .departments import (  # noqa: F401
    department_create,
    department_delete,
    department_delete_confirmation,
    department_detail,
    department_edit,
    department_list,
    department_toggle_active,
)
from .faculty import (  # noqa: F401
    faculty_change_role,
    faculty_create,
    faculty_detail,
    faculty_list,
    faculty_toggle_active,
    faculty_update,
)
from .portal import (  # noqa: F401
    correction_request_list,
    correction_request_review,
    my_correction_requests,
    my_department,
    my_profile,
)
from .public import (  # noqa: F401
    PortalPasswordChangeDoneView,
    PortalPasswordChangeView,
    account_overview,
    landing,
    login_view,
    logout_view,
)
from .students import (  # noqa: F401
    delete_student,
    register_student,
    student_delete_confirmation,
    student_detail,
    student_directory,
    update_student,
)
