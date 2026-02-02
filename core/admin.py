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
