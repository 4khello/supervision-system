from django.contrib import admin
from .models import (
    Department,
    Supervisor,
    Research,
    ResearchSupervision,
    ResearchFeePayment,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


class ResearchSupervisionInlineForSupervisor(admin.TabularInline):
    model = ResearchSupervision
    extra = 0
    autocomplete_fields = ["research"]


@admin.register(Supervisor)
class SupervisorAdmin(admin.ModelAdmin):
    list_display = ["name", "department", "is_active"]
    list_filter = ["is_active", "department"]
    search_fields = ["name"]
    inlines = [ResearchSupervisionInlineForSupervisor]


class ResearchSupervisionInlineForResearch(admin.TabularInline):
    model = ResearchSupervision
    extra = 0
    autocomplete_fields = ["supervisor"]


class ResearchFeePaymentInline(admin.TabularInline):
    model = ResearchFeePayment
    extra = 0


@admin.register(Research)
class ResearchAdmin(admin.ModelAdmin):
    list_display = [
        "researcher_name",
        "researcher_type",
        "degree",
        "department",
        "status",
        "registration_date",
        "phone",
    ]
    list_filter = ["degree", "status", "department", "researcher_type"]
    search_fields = ["researcher_name", "title", "phone"]
    autocomplete_fields = ["department"]
    inlines = [ResearchSupervisionInlineForResearch, ResearchFeePaymentInline]

    fieldsets = (
        ("البيانات الأساسية", {
            "fields": ("researcher_name", "researcher_type", "degree", "title", "department", "status", "status_note")
        }),
        ("معلومات الاتصال", {
            "fields": ("phone",)
        }),
        ("التواريخ المهمة", {
            "fields": ("registration_date", "frame_date", "university_approval_date")
        }),
    )


@admin.register(ResearchSupervision)
class ResearchSupervisionAdmin(admin.ModelAdmin):
    list_display = ["research", "supervisor", "role"]
    list_filter = ["role"]
    autocomplete_fields = ["research", "supervisor"]


@admin.register(ResearchFeePayment)
class ResearchFeePaymentAdmin(admin.ModelAdmin):
    list_display = ["research", "year", "is_paid", "paid_at"]
    list_filter = ["year", "is_paid"]
    search_fields = ["research__researcher_name"]
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import DepartmentUser

# تسجيل موديل DepartmentUser ليظهر في الأدمين
@admin.register(DepartmentUser)
class DepartmentUserAdmin(admin.ModelAdmin):
    list_display = ["user", "department"]
    search_fields = ["user__username", "department__name"]

# تخصيص لوحة تحكم المستخدمين لإظهار القسم الخاص بكل يوزر
class DepartmentUserInline(admin.StackedInline):
    model = DepartmentUser
    can_delete = False
    verbose_name_plural = "بيانات القسم"

# إعادة تسجيل موديل User الافتراضي مع الإضافات الجديدة
admin.site.unregister(User)
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [DepartmentUserInline]
    list_display = ("username", "email", "get_department", "is_staff", "is_active")

    def get_department(self, obj):
        if hasattr(obj, 'department_user'):
            return obj.department_user.department.name
        return "N/A"
    get_department.short_description = "القسم"