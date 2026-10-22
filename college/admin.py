"""Registration of the portal models in Django's own admin site.

The admin site is a convenient extra tool for a superuser.  The three
portal roles are managed through the portal itself (that is where the
business rules live), so this file only adds read friendly list views.
"""

from django.contrib import admin

from .models import (
    CorrectionRequest,
    Department,
    DepartmentChangeLog,
    FacultyProfile,
    Students,
    UserProfile,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "office_location", "contact_email", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "contact_email")
    ordering = ("name",)


@admin.register(Students)
class StudentsAdmin(admin.ModelAdmin):
    list_display = (
        "student_id",
        "student_name",
        "department",
        "student_section",
        "gender",
        "has_account",
    )
    list_filter = ("department", "student_section", "gender")
    search_fields = ("student_id", "student_name")
    autocomplete_fields = ("department",)
    ordering = ("student_name",)

    @admin.display(boolean=True, description="Has login")
    def has_account(self, obj):
        return obj.account_id is not None


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "user", "designation", "phone")
    search_fields = ("employee_id", "user__username", "user__first_name", "user__last_name")
    filter_horizontal = ("departments",)
    ordering = ("employee_id",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    ordering = ("user__username",)


@admin.register(DepartmentChangeLog)
class DepartmentChangeLogAdmin(admin.ModelAdmin):
    list_display = ("department", "action", "changed_by", "changed_at")
    list_filter = ("action",)
    readonly_fields = ("department", "changed_by", "action", "changes", "changed_at")
    date_hierarchy = "changed_at"


@admin.register(CorrectionRequest)
class CorrectionRequestAdmin(admin.ModelAdmin):
    list_display = ("student", "field_name", "requested_value", "status", "created_at")
    list_filter = ("status", "field_name")
    search_fields = ("student__student_id", "student__student_name")
    date_hierarchy = "created_at"
