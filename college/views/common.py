"""Helpers shared by the role specific view modules."""

from django.core.paginator import Paginator
from django.db.models import Count, Q

from ..models import Department, Students

PAGE_SIZE = 12


def college_stats():
    """Numbers shown on the admin and faculty dashboards.

    Every value comes from a database query - nothing is hard coded.
    """
    students = Students.objects.all()
    return {
        "total_students": students.count(),
        "total_departments": Department.objects.filter(is_active=True).count(),
        "total_departments_all": Department.objects.count(),
        "students_by_department": list(
            Department.objects.annotate(students_count=Count("students")).order_by(
                "name"
            )
        ),
        "students_by_section": list(
            students.values("student_section")
            .annotate(count=Count("id"))
            .order_by("student_section")
        ),
        "recent_students": list(
            students.select_related("department")
            .order_by("-created_at", "-id")[:5]
        ),
    }


def filtered_students(request):
    """Build the student queryset from the search / filter query string.

    The same helper is used by the admin and the faculty directory, so the
    two roles always see identical results for identical filters.
    """
    queryset = Students.objects.select_related("department").all()

    search = (request.GET.get("q") or "").strip()
    department_id = (request.GET.get("department") or "").strip()
    section = (request.GET.get("section") or "").strip()

    if search:
        queryset = queryset.filter(
            Q(student_name__icontains=search) | Q(student_id__icontains=search)
        )

    if department_id.isdigit():
        queryset = queryset.filter(department_id=int(department_id))
    elif department_id:
        # An unknown filter is ignored instead of raising an error.
        queryset = queryset.none()

    if section.isdigit():
        queryset = queryset.filter(student_section=int(section))
    elif section:
        queryset = queryset.none()

    return queryset.order_by("student_name", "student_id")


def paginate(request, queryset, per_page=PAGE_SIZE):
    """Paginate ``queryset`` and keep the current filters in the context."""
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Query string without the "page" parameter - used to build the
    # pagination links so the active filters survive a page change.
    querystring = request.GET.copy()
    querystring.pop("page", None)

    return {
        "page_obj": page_obj,
        "paginator": paginator,
        "filter_querystring": querystring.urlencode(),
        "total_results": paginator.count,
    }


def active_filter_values(request):
    """The filter values that are currently applied (for the form fields)."""
    return {
        "current_q": (request.GET.get("q") or "").strip(),
        "current_department": (request.GET.get("department") or "").strip(),
        "current_section": (request.GET.get("section") or "").strip(),
    }
