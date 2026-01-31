# =========================================
# file: core/admin.py
# =========================================
from django.contrib import admin

from .models import Department, Supervisor, Research, ResearchSupervision


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name",)


class ResearchSupervisionInline(admin.TabularInline):
    """
    ✅ داخل صفحة المشرف:
    - يظهر الباحث
    - نوعه (باحث/معيد)
    - قسم الباحث (فاضي)
    - المشرفين المشاركين مع نفس الباحث/البحث
    """
    model = ResearchSupervision
    extra = 0
    autocomplete_fields = ("research",)
    fields = ("research", "researcher_name", "researcher_type", "researcher_department", "co_supervisors", "role")
    readonly_fields = ("researcher_name", "researcher_type", "researcher_department", "co_supervisors")
    show_change_link = True

    def researcher_name(self, obj):
        return getattr(obj.research, "researcher_name", "") if obj and obj.research else ""
    researcher_name.short_description = "الباحث"

    def researcher_type(self, obj):
        return obj.research.get_researcher_type_display() if obj and obj.research else ""
    researcher_type.short_description = "النوع"

    def researcher_department(self, obj):
        if not obj or not obj.research or not obj.research.department:
            return ""
        return obj.research.department.name
    researcher_department.short_description = "قسم الباحث"

    def co_supervisors(self, obj):
        if not obj or not obj.research_id or not obj.supervisor_id:
            return ""
        qs = (
            ResearchSupervision.objects
            .filter(research_id=obj.research_id)
            .exclude(supervisor_id=obj.supervisor_id)
            .select_related("supervisor")
        )
        names = [x.supervisor.name for x in qs if x.supervisor and x.supervisor.name]
        # إزالة تكرار مع الحفاظ على ترتيب منطقي
        seen = set()
        out = []
        for n in names:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return "، ".join(out)
    co_supervisors.short_description = "المشرفون المشاركون"


@admin.register(Supervisor)
class SupervisorAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "department", "researchers_count", "assistants_count", "is_active")
    list_filter = ("is_active", "department")
    inlines = [ResearchSupervisionInline]

    def researchers_count(self, obj):
        # ✅ العدّ = الباحثين فقط (مش المعيدين)
        return (
            ResearchSupervision.objects
            .filter(supervisor=obj, research__researcher_type=Research.ResearcherType.RESEARCHER)
            .values("research_id")
            .distinct()
            .count()
        )
    researchers_count.short_description = "عدد الباحثين"

    def assistants_count(self, obj):
        # ✅ إحصائية المعيدين منفصلة
        return (
            ResearchSupervision.objects
            .filter(supervisor=obj, research__researcher_type=Research.ResearcherType.ASSISTANT)
            .values("research_id")
            .distinct()
            .count()
        )
    assistants_count.short_description = "عدد المعيدين"


@admin.register(Research)
class ResearchAdmin(admin.ModelAdmin):
    list_display = ("researcher_name", "researcher_type", "degree", "department", "status")
    list_filter = ("degree", "status", "department", "researcher_type")
    search_fields = ("researcher_name", "title")
    autocomplete_fields = ("department",)


@admin.register(ResearchSupervision)
class ResearchSupervisionAdmin(admin.ModelAdmin):
    list_display = ("research", "supervisor", "role")
    autocomplete_fields = ("research", "supervisor")
    list_filter = ("role", "supervisor")