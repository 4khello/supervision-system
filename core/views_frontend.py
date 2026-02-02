from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
import json

from django.utils import timezone
from core.models import Research, Supervisor, ResearchSupervision, Department, ResearchFeePayment
from core.exporters import build_export_workbook
from datetime import datetime
from urllib.parse import quote
import re
import openpyxl


def home(request):
    """الصفحة الرئيسية الجديدة مع الإحصائيات واختيار القسم"""
    # الإحصائيات الرئيسية
    excluded_statuses = [Research.Status.DISCUSSED, Research.Status.DISMISSED, Research.Status.CANCELLED]
    
    ma_current = Research.objects.filter(
        degree=Research.Degree.MA,
        researcher_type=Research.ResearcherType.RESEARCHER
    ).exclude(status__in=excluded_statuses).count()
    
    phd_current = Research.objects.filter(
        degree=Research.Degree.PHD,
        researcher_type=Research.ResearcherType.RESEARCHER
    ).exclude(status__in=excluded_statuses).count()
    
    discussed_count = Research.objects.filter(status=Research.Status.DISCUSSED).count()
    dismissed_count = Research.objects.filter(status=Research.Status.DISMISSED).count()
    
    # الأقسام
    departments_with_supervisors = Supervisor.objects.filter(
        is_active=True,
        department__isnull=False
    ).values_list('department_id', flat=True).distinct()
    
    departments = Department.objects.filter(id__in=departments_with_supervisors).order_by('name')
    
    # القسم المختار
    dept_id = request.GET.get('dept_id')
    selected_dept = None
    dept_stats = None
    dept_supervisors = []
    
    if dept_id:
        selected_dept = get_object_or_404(Department, id=dept_id)
        
        # المشرفين في القسم مع إحصائياتهم
        dept_supervisors_qs = Supervisor.objects.filter(department=selected_dept, is_active=True)
        
        # الباحثين الحاليين فقط (بدون ناقشوا ومفصولين)
        excluded_statuses = [Research.Status.DISCUSSED, Research.Status.DISMISSED, Research.Status.CANCELLED]
        
        dept_supervisors = []
        
        # جمع كل IDs الباحثين في القسم لتجنب التكرار
        all_dept_research_ids = set()
        
        for supervisor in dept_supervisors_qs:
            # حساب إحصائيات كل مشرف - الحاليين فقط
            supervisor_researches = Research.objects.filter(
                researchsupervision__supervisor=supervisor
            ).exclude(status__in=excluded_statuses).distinct()
            
            # فقط الباحثين (بدون معيدين في الإجمالي)
            ma_researches = supervisor_researches.filter(
                degree=Research.Degree.MA,
                researcher_type=Research.ResearcherType.RESEARCHER
            )
            ma_count = ma_researches.count()
            
            phd_researches = supervisor_researches.filter(
                degree=Research.Degree.PHD,
                researcher_type=Research.ResearcherType.RESEARCHER
            )
            phd_count = phd_researches.count()
            
            assistant_researches = supervisor_researches.filter(
                researcher_type=Research.ResearcherType.ASSISTANT
            )
            assistants_count = assistant_researches.count()
            
            # الإجمالي = ماجستير + دكتوراه فقط (بدون معيدين)
            total_count = ma_count + phd_count
            
            supervisor.ma_count = ma_count
            supervisor.phd_count = phd_count
            supervisor.assistants_count = assistants_count
            supervisor.total_count = total_count
            supervisor.research_count = total_count
            
            # تجميع IDs لحساب الإجمالي الصحيح للقسم
            all_dept_research_ids.update(ma_researches.values_list('id', flat=True))
            all_dept_research_ids.update(phd_researches.values_list('id', flat=True))
            all_dept_research_ids.update(assistant_researches.values_list('id', flat=True))
            
            dept_supervisors.append(supervisor)
        
        # ترتيب حسب الإجمالي
        dept_supervisors = sorted(dept_supervisors, key=lambda x: x.total_count, reverse=True)
        
        # حساب إجمالي القسم (بدون تكرار)
        all_dept_researches = Research.objects.filter(id__in=all_dept_research_ids)
        
        dept_stats = {
            'total': all_dept_researches.filter(researcher_type=Research.ResearcherType.RESEARCHER).count(),
            'phd': all_dept_researches.filter(degree=Research.Degree.PHD, researcher_type=Research.ResearcherType.RESEARCHER).count(),
            'ma': all_dept_researches.filter(degree=Research.Degree.MA, researcher_type=Research.ResearcherType.RESEARCHER).count(),
            'assistants': all_dept_researches.filter(researcher_type=Research.ResearcherType.ASSISTANT).count(),
        }
    
    return render(request, "frontend/home.html", {
        "ma_current": ma_current,
        "phd_current": phd_current,
        "discussed_count": discussed_count,
        "dismissed_count": dismissed_count,
        "departments": departments,
        "selected_dept": selected_dept,
        "dept_stats": dept_stats,
        "dept_supervisors": dept_supervisors,
    })


def home_stat_details(request, stat_type):
    """API endpoint لإرجاع تفاصيل الإحصائيات في الصفحة الرئيسية"""
    excluded_statuses = [Research.Status.DISCUSSED, Research.Status.DISMISSED, Research.Status.CANCELLED]
    
    if stat_type == "ma_current":
        researches = Research.objects.filter(
            degree=Research.Degree.MA,
            researcher_type=Research.ResearcherType.RESEARCHER
        ).exclude(status__in=excluded_statuses)
        title = "ماجستير (الحاليين)"
    elif stat_type == "phd_current":
        researches = Research.objects.filter(
            degree=Research.Degree.PHD,
            researcher_type=Research.ResearcherType.RESEARCHER
        ).exclude(status__in=excluded_statuses)
        title = "دكتوراه (الحاليين)"
    elif stat_type == "discussed":
        researches = Research.objects.filter(status=Research.Status.DISCUSSED)
        title = "ناقشوا"
    elif stat_type == "dismissed":
        researches = Research.objects.filter(status=Research.Status.DISMISSED)
        title = "مفصولين"
    else:
        return JsonResponse({"error": "Invalid stat type"}, status=400)
    
    researches = researches.select_related('department').prefetch_related('researchsupervision_set__supervisor')[:100]
    
    data = []
    for r in researches:
        supervisors = [f"د. {link.supervisor.name}" for link in r.researchsupervision_set.all()]
        data.append({
            "id": r.id,
            "name": r.researcher_name,
            "degree": r.get_degree_display(),
            "supervisors": ", ".join(supervisors),
            "status": r.get_status_display(),
        })
    
    return JsonResponse({"title": title, "count": len(data), "data": data})


def dashboard(request):
    """الصفحة الرئيسية مع إحصائيات تفاعلية"""
    q = (request.GET.get("q") or "").strip()
    
    total_research = Research.objects.count()
    discussed_count = Research.objects.filter(status=Research.Status.DISCUSSED).count()
    researcher_count = Research.objects.filter(status=Research.Status.REGISTERED).count()
    dismissed_count = Research.objects.filter(status=Research.Status.DISMISSED).count()
    phd_count = Research.objects.filter(degree=Research.Degree.PHD).count()
    total_supervisors = Supervisor.objects.filter(is_active=True).count()
    total_researchers_only = Research.objects.filter(researcher_type=Research.ResearcherType.RESEARCHER).count()
    total_assistants = Research.objects.filter(researcher_type=Research.ResearcherType.ASSISTANT).count()

    # ✅ البحث على كل الأبحاث مش 50 بس!
    researches = Research.objects.all().prefetch_related('researchsupervision_set__supervisor', 'department').order_by('-id')
    
    if q:
        researches = researches.filter(
            Q(researcher_name__icontains=q) | Q(title__icontains=q)
        )
    else:
        # لو مفيش بحث، نعرض آخر 50 بس
        researches = researches[:50]

    departments_stats = Department.objects.annotate(
        total=Count('researches'),
        phd=Count('researches', filter=Q(researches__degree=Research.Degree.PHD)),
        ma=Count('researches', filter=Q(researches__degree=Research.Degree.MA))
    ).order_by('-total')[:10]

    return render(request, "frontend/dashboard.html", {
        "total_research": total_research,
        "discussed_count": discussed_count,
        "researcher_count": researcher_count,
        "dismissed_count": dismissed_count,
        "phd_count": phd_count,
        "total_supervisors": total_supervisors,
        "total_researchers_only": total_researchers_only,
        "total_assistants": total_assistants,
        "researches": researches,
        "departments_stats": departments_stats,
        "q": q,
    })


def choose_page(request):
    """صفحة اختيار عرض المشرفين أو الباحثين"""
    return render(request, "frontend/choose.html")


def stat_details(request, stat_type):
    """API endpoint لإرجاع تفاصيل الإحصائيات مع رابط لصفحة الباحث"""
    if stat_type == "total":
        researches = Research.objects.all()
        title = "إجمالي الإشرافات"
    elif stat_type == "discussed":
        researches = Research.objects.filter(status=Research.Status.DISCUSSED)
        title = "ناقش"
    elif stat_type == "researcher":
        researches = Research.objects.filter(status=Research.Status.REGISTERED)
        title = "مسجل"
    elif stat_type == "dismissed":
        researches = Research.objects.filter(status=Research.Status.DISMISSED)
        title = "مفصول"
    elif stat_type == "phd":
        researches = Research.objects.filter(degree=Research.Degree.PHD)
        title = "طلاب دكتوراه"
    else:
        return JsonResponse({"error": "Invalid stat type"}, status=400)

    researches = researches.select_related('department').prefetch_related('researchsupervision_set__supervisor')[:100]

    data = []
    for r in researches:
        supervisors = [link.supervisor.name for link in r.researchsupervision_set.all()]
        data.append({
            "id": r.id,
            "name": r.researcher_name,
            "degree": r.get_degree_display(),
            "title": r.title or "—",
            "supervisors": ", ".join(supervisors),
            "status": r.get_status_display(),
        })

    return JsonResponse({"title": title, "count": len(data), "data": data})


def research_detail(request, pk):
    """صفحة تفاصيل الباحث الكاملة"""
    research = get_object_or_404(
        Research.objects.select_related('department').prefetch_related(
            'researchsupervision_set__supervisor',
            'fee_payments'
        ),
        pk=pk
    )

    supervisors = [link.supervisor for link in research.researchsupervision_set.all()]
    current_year = timezone.now().year

    # تأكد إن في سجل للسنة الحالية (افتراضي لم يدفع)
    ResearchFeePayment.objects.get_or_create(research=research, year=current_year, defaults={"is_paid": False})

    payments = list(research.fee_payments.all())  # مرتبة -year

    return render(request, "frontend/research_detail.html", {
        "research": research,
        "supervisors": supervisors,
        "payments": payments,
        "current_year": current_year,
    })



def department_stats(request):
    """صفحة إحصائيات الأقسام - بناءً على أقسام المشرفين مع فلاتر"""
    dept_id = request.GET.get('dept_id')
    sf = (request.GET.get("sf") or "active").strip().lower()
    
    # ✅ تحديد الفلتر
    excluded_for_active = [Research.Status.DISCUSSED, Research.Status.DISMISSED, Research.Status.CANCELLED]
    
    if sf == "discussed":
        status_filter = Q(status=Research.Status.DISCUSSED)
    elif sf == "dismissed":
        status_filter = Q(status=Research.Status.DISMISSED)
    elif sf == "all":
        status_filter = Q()
    elif sf == "active_discussed":
        status_filter = ~Q(status__in=[Research.Status.DISMISSED, Research.Status.CANCELLED])
    else:
        sf = "active"
        status_filter = ~Q(status__in=excluded_for_active)
    
    # ✅ جلب كل الأقسام اللي فيها مشرفين نشطين
    departments_with_supervisors = Supervisor.objects.filter(
        is_active=True,
        department__isnull=False
    ).values_list('department_id', flat=True).distinct()
    
    all_departments = Department.objects.filter(id__in=departments_with_supervisors)
    
    departments = []
    for dept in all_departments:
        # ✅ نجيب المشرفين في القسم ده
        dept_supervisors = Supervisor.objects.filter(department=dept, is_active=True)
        
        # ✅ نجيب كل الباحثين اللي ليهم مشرفين في القسم ده + تطبيق الفلتر
        dept_researches = Research.objects.filter(
            researchsupervision__supervisor__in=dept_supervisors
        ).filter(status_filter).distinct()
        
        total = dept_researches.count()
        
        if total > 0:
            phd = dept_researches.filter(degree=Research.Degree.PHD).count()
            ma = dept_researches.filter(degree=Research.Degree.MA).count()
            researchers = dept_researches.filter(researcher_type=Research.ResearcherType.RESEARCHER).count()
            assistants = dept_researches.filter(researcher_type=Research.ResearcherType.ASSISTANT).count()
            
            dept.total = total
            dept.phd = phd
            dept.ma = ma
            dept.researchers = researchers
            dept.assistants = assistants
            departments.append(dept)
    
    # ترتيب حسب العدد الكلي
    departments = sorted(departments, key=lambda x: x.total, reverse=True)

    selected_dept = None
    dept_researches = []
    
    if dept_id:
        selected_dept = get_object_or_404(Department, id=dept_id)
        # ✅ نجيب الباحثين من خلال مشرفين القسم + الفلتر
        dept_supervisors = Supervisor.objects.filter(department=selected_dept, is_active=True)
        dept_researches = Research.objects.filter(
            researchsupervision__supervisor__in=dept_supervisors
        ).filter(status_filter).distinct().prefetch_related('researchsupervision_set__supervisor')

    return render(request, "frontend/department_stats.html", {
        "departments": departments,
        "selected_dept": selected_dept,
        "dept_researches": dept_researches,
        "sf": sf,
    })


def export_department_excel(request):
    """تصدير Excel لإحصائيات قسم معين مع الفلتر"""
    dept_id = request.GET.get('dept_id')
    sf = (request.GET.get("sf") or "active").strip().lower()
    
    if not dept_id:
        return HttpResponse("يجب اختيار قسم", status=400)
    
    dept = get_object_or_404(Department, id=dept_id)
    
    # تطبيق نفس الفلتر
    excluded_for_active = [Research.Status.DISCUSSED, Research.Status.DISMISSED, Research.Status.CANCELLED]
    
    if sf == "discussed":
        status_filter = Q(status=Research.Status.DISCUSSED)
    elif sf == "dismissed":
        status_filter = Q(status=Research.Status.DISMISSED)
    elif sf == "all":
        status_filter = Q()
    elif sf == "active_discussed":
        status_filter = ~Q(status__in=[Research.Status.DISMISSED, Research.Status.CANCELLED])
    else:
        status_filter = ~Q(status__in=excluded_for_active)
    
    # جلب الباحثين
    dept_supervisors = Supervisor.objects.filter(department=dept, is_active=True)
    researches = Research.objects.filter(
        researchsupervision__supervisor__in=dept_supervisors
    ).filter(status_filter).distinct().prefetch_related('researchsupervision_set__supervisor')
    
    # إنشاء Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{dept.name}"
    
    # العناوين
    headers = ['#', 'اسم الباحث', 'النوع', 'الدرجة', 'عنوان الرسالة', 'المشرفون', 'الحالة']
    ws.append(headers)
    
    # البيانات
    for idx, research in enumerate(researches, start=1):
        supervisors = ", ".join([link.supervisor.name for link in research.researchsupervision_set.all()])
        researcher_type = "معيد" if research.researcher_type == Research.ResearcherType.ASSISTANT else "باحث"
        degree = "دكتوراه" if research.degree == Research.Degree.PHD else "ماجستير"
        
        ws.append([
            idx,
            research.researcher_name,
            researcher_type,
            degree,
            research.title or "",
            supervisors,
            research.get_status_display()
        ])
    
    # تنسيق
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="1a4f9c", end_color="1a4f9c", fill_type="solid")
        cell.font = openpyxl.styles.Font(color="FFFFFF", bold=True)
    
    # العرض التلقائي
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # اسم الملف
    filter_name = {"active": "الحاليين", "discussed": "ناقشوا", "dismissed": "مفصولين", "all": "الكل", "active_discussed": "الحاليين+ناقشوا"}.get(sf, sf)
    filename = f"{dept.name}_{filter_name}_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


def supervisors_page(request):
    """صفحة المشرفين - الأعداد للباحثين الحاليين فقط + فلتر القسم"""
    q = (request.GET.get("q") or "").strip()
    dept_id = request.GET.get("dept_id")
    
    # ✅ افتراضي: الحاليين فقط (بدون ناقشوا ومفصولين)
    sf = "active"

    # ✅ الحاليين = بدون (ناقش، مفصول، ملغي)
    excluded_for_active = [Research.Status.DISCUSSED, Research.Status.DISMISSED, Research.Status.CANCELLED]
    status_q = ~Q(researches__status__in=excluded_for_active)

    supervisors = (
        Supervisor.objects.filter(is_active=True).select_related("department")
        .annotate(
            ma_count=Count("researches", filter=(Q(researches__researcher_type=Research.ResearcherType.RESEARCHER) & Q(researches__degree=Research.Degree.MA) & status_q), distinct=True),
            phd_count=Count("researches", filter=(Q(researches__researcher_type=Research.ResearcherType.RESEARCHER) & Q(researches__degree=Research.Degree.PHD) & status_q), distinct=True),
            researchers_total=Count("researches", filter=(Q(researches__researcher_type=Research.ResearcherType.RESEARCHER) & status_q), distinct=True),
            assistants_count=Count("researches", filter=(Q(researches__researcher_type=Research.ResearcherType.ASSISTANT) & status_q), distinct=True),
            total_links=Count("researchsupervision", distinct=True),
        ).order_by("-researchers_total", "name")
    )

    if q:
        supervisors = supervisors.filter(name__icontains=q)
    
    # ✅ فلتر القسم
    if dept_id:
        supervisors = supervisors.filter(department_id=dept_id)
    
    # ✅ جلب الأقسام للفلتر - تصحيح الكويري
    all_departments = Department.objects.filter(
        id__in=Supervisor.objects.filter(is_active=True, department__isnull=False).values_list('department_id', flat=True).distinct()
    ).order_by('name')

    return render(request, "frontend/supervisors.html", {
        "supervisors": supervisors,
        "q": q,
        "sf": sf,
        "dept_id": dept_id,
        "all_departments": all_departments,
    })


def researchers_page(request):
    """صفحة الباحثين (بدون المعيدين)"""
    q = (request.GET.get("q") or "").strip()
    sf = (request.GET.get("sf") or "active").strip().lower()
    # فلترة بالتاريخ (القيم جاية من <input type="date">)
    date_from = (request.GET.get("date_from") or "").strip() or None
    date_to   = (request.GET.get("date_to") or "").strip() or None

    excluded_for_active = [Research.Status.DISCUSSED, Research.Status.DISMISSED, Research.Status.CANCELLED]

    if sf == "discussed":
        status_filter = Q(status=Research.Status.DISCUSSED)
    elif sf == "dismissed":
        status_filter = Q(status=Research.Status.DISMISSED)
    elif sf == "all":
        status_filter = Q()
    elif sf == "active_discussed":
        status_filter = ~Q(status__in=[Research.Status.DISMISSED, Research.Status.CANCELLED])
    else:
        sf = "active"
        status_filter = ~Q(status__in=excluded_for_active)

    researches = (
        Research.objects
        .filter(researcher_type=Research.ResearcherType.RESEARCHER)
        .filter(status_filter)
        .prefetch_related("researchsupervision_set__supervisor", "department")
        .order_by("-id")
    )

    if q:
        researches = researches.filter(Q(researcher_name__icontains=q) | Q(title__icontains=q))
    if date_from:
        researches = researches.filter(registration_date__gte=date_from)
    if date_to:
        researches = researches.filter(registration_date__lte=date_to)
    return render(request, "frontend/researchers.html", {"researches": researches, "q": q, "sf": sf, "date_from": date_from,  # ← جديد
        "date_to": date_to, })




def supervisor_detail(request, pk: int):
    supervisor = get_object_or_404(Supervisor.objects.select_related("department"), pk=pk)
    sf = (request.GET.get("sf") or "active").strip().lower()

    excluded_for_active_only = [Research.Status.DISCUSSED, Research.Status.DISMISSED, Research.Status.CANCELLED]

    if sf == "discussed":
        status_filter = Q(status=Research.Status.DISCUSSED)
    elif sf == "dismissed":
        status_filter = Q(status=Research.Status.DISMISSED)
    elif sf == "all":
        status_filter = Q()
    elif sf == "active_discussed":
        status_filter = ~Q(status__in=[Research.Status.DISMISSED, Research.Status.CANCELLED])
    else:
        sf = "active"
        status_filter = ~Q(status__in=excluded_for_active_only)

    researches = Research.objects.filter(researchsupervision__supervisor=supervisor).filter(status_filter).prefetch_related("researchsupervision_set__supervisor", "department").order_by("-degree", "researcher_name").distinct()

    items = []
    for r in researches:
        links = list(ResearchSupervision.objects.filter(research=r).select_related("supervisor").order_by("supervisor__name"))
        co_supers = [l.supervisor for l in links if l.supervisor_id != supervisor.id]
        items.append({"research": r, "co_supervisors": co_supers})

    ma_count = sum(1 for x in items if x["research"].researcher_type == Research.ResearcherType.RESEARCHER and x["research"].degree == Research.Degree.MA)
    phd_count = sum(1 for x in items if x["research"].researcher_type == Research.ResearcherType.RESEARCHER and x["research"].degree == Research.Degree.PHD)
    researchers_total = ma_count + phd_count
    assistants_only = sum(1 for x in items if x["research"].researcher_type == Research.ResearcherType.ASSISTANT)

    return render(request, "frontend/supervisor_detail.html", {
        "supervisor": supervisor, "items": items, "ma_count": ma_count, "phd_count": phd_count,
        "researchers_total": researchers_total, "assistants_only": assistants_only, "sf": sf
    })


def stats_page(request):
    by_degree = Research.objects.values("degree").annotate(total=Count("id")).order_by("degree")
    by_status = Research.objects.values("status").annotate(total=Count("id")).order_by("-total")
    by_type = Research.objects.values("researcher_type").annotate(total=Count("id")).order_by("researcher_type")
    return render(request, "frontend/stats.html", {"by_degree": by_degree, "by_status": by_status, "by_type": by_type})


def export_excel(request):
    q = (request.GET.get("q") or "").strip()
    supervisor_id = request.GET.get("supervisor_id")
    sf = (request.GET.get("sf") or "active").strip().lower()
    wb = build_export_workbook(q=q, supervisor_id=supervisor_id, sf=sf)
    sf_slug = {"active": "active", "discussed": "discussed", "active_discussed": "active+discussed", "dismissed": "dismissed", "all": "all"}.get(sf, sf)

    def _safe_ascii_filename(text: str) -> str:
        text = (text or "").strip()
        text = re.sub(r"\s+", "_", text)
        text = re.sub(r"[^A-Za-z0-9_\-]+", "", text)
        return text[:40] or "Supervisor"

    date_part = datetime.now().strftime("%Y-%m-%d")
    if supervisor_id:
        sup = Supervisor.objects.filter(id=int(supervisor_id)).only("name").first()
        sup_part = _safe_ascii_filename(sup.name if sup else "Supervisor")
        filename_ascii = f"{sup_part}__{sf_slug}__{date_part}.xlsx"
    else:
        filename_ascii = f"Supervisors__{sf_slug}__{date_part}.xlsx"

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename_ascii}"'
    wb.save(response)
    return response


def upload_researchers(request):
    """رفع ملف Excel - مع منع التكرار الكامل"""
    if request.method == "POST" and request.FILES.get("file"):
        try:
            file = request.FILES["file"]
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            header = [str(cell.value).strip() if cell.value else "" for cell in sheet[1]]

            name_idx = degree_idx = title_idx = supervisors_idx = type_idx = dept_idx = status_idx = None

            for idx, col in enumerate(header):
                col_lower = col.lower()
                if any(k in col_lower for k in ["اسم", "name", "الإســـــــم"]): name_idx = idx
                elif any(k in col_lower for k in ["مرحلة", "degree", "درجة"]): degree_idx = idx
                elif any(k in col_lower for k in ["عنوان", "title", "العنـــــــــوان"]): title_idx = idx
                elif any(k in col_lower for k in ["مشرف", "supervisor"]): supervisors_idx = idx
                elif any(k in col_lower for k in ["نوع", "type"]): type_idx = idx
                elif any(k in col_lower for k in ["قسم", "department"]): dept_idx = idx
                elif any(k in col_lower for k in ["حالة", "status"]): status_idx = idx

            if None in [name_idx, degree_idx, supervisors_idx]:
                messages.error(request, "الملف لا يحتوي على الأعمدة المطلوبة")
                return redirect("upload_researchers")

            new_researchers = []
            errors = []
            duplicates = []

            for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    if not row or all(cell is None or str(cell).strip() == "" for cell in row): continue

                    researcher_name = str(row[name_idx]).strip() if row[name_idx] else ""
                    degree_raw = str(row[degree_idx]).strip() if row[degree_idx] else ""
                    title = str(row[title_idx]).strip() if title_idx is not None and row[title_idx] else ""
                    supervisor_names = str(row[supervisors_idx]).strip() if row[supervisors_idx] else ""

                    if not researcher_name or not degree_raw or not supervisor_names: continue

                    degree = Research.Degree.PHD if any(k in degree_raw.lower() for k in ["دكتور", "phd"]) else Research.Degree.MA
                    researcher_type = Research.ResearcherType.RESEARCHER
                    if type_idx is not None and row[type_idx] and "معيد" in str(row[type_idx]).lower():
                        researcher_type = Research.ResearcherType.ASSISTANT

                    status = Research.Status.REGISTERED
                    if status_idx is not None and row[status_idx]:
                        status_raw = str(row[status_idx]).strip()
                        if "ناقش" in status_raw: status = Research.Status.DISCUSSED
                        elif "فصل" in status_raw: status = Research.Status.DISMISSED
                        elif "إلغاء" in status_raw or "الغاء" in status_raw: status = Research.Status.CANCELLED

                    department = None
                    if dept_idx is not None and row[dept_idx]:
                        dept_name = str(row[dept_idx]).strip()
                        if dept_name: department, _ = Department.objects.get_or_create(name=dept_name)

                    # ✅ التحقق من التكرار: الاسم + الدرجة + النوع فقط
                    existing_research = Research.objects.filter(
                        researcher_name=researcher_name,
                        degree=degree,
                        researcher_type=researcher_type
                    ).first()

                    if existing_research:
                        # ✅ موجود بالفعل - نشوف المشرفين
                        new_supers = []
                        existing_supervisors = [link.supervisor.name for link in ResearchSupervision.objects.filter(research=existing_research)]
                        supervisors = [s.strip() for s in re.split(r'[|،,;/]', supervisor_names) if s.strip()]

                        for supervisor_name in supervisors:
                            if supervisor_name not in existing_supervisors:
                                supervisor, _ = Supervisor.objects.get_or_create(name=supervisor_name)
                                if department and not supervisor.department:
                                    supervisor.department = department
                                    supervisor.save()
                                ResearchSupervision.objects.get_or_create(research=existing_research, supervisor=supervisor)
                                new_supers.append(supervisor_name)

                        if new_supers:
                            new_researchers.append(f"✅ صف {row_num}: {researcher_name} - تم إضافة المشرفين: {', '.join(new_supers)}")
                        else:
                            duplicates.append(f"⚠️ صف {row_num}: {researcher_name} ({degree_raw}) - موجود بالفعل مع نفس المشرفين")
                    else:
                        # ✅ جديد - نضيفه
                        research = Research.objects.create(
                            researcher_name=researcher_name,
                            degree=degree,
                            title=title,
                            researcher_type=researcher_type,
                            department=department,
                            status=status
                        )
                        supervisors = [s.strip() for s in re.split(r'[|،,;/]', supervisor_names) if s.strip()]
                        
                        for supervisor_name in supervisors:
                            supervisor, _ = Supervisor.objects.get_or_create(name=supervisor_name)
                            if department and not supervisor.department:
                                supervisor.department = department
                                supervisor.save()
                            ResearchSupervision.objects.create(research=research, supervisor=supervisor)

                        new_researchers.append(f"✅ صف {row_num}: {researcher_name} ({degree_raw}) - تم إضافته بنجاح")

                except Exception as e:
                    errors.append(f"❌ خطأ في الصف {row_num}: {str(e)}")

            return render(request, "frontend/upload_success.html", {
                "new_researchers": new_researchers,
                "duplicates": duplicates,
                "errors": errors
            })

        except Exception as e:
            messages.error(request, f"حدث خطأ: {str(e)}")
            return redirect("upload_researchers")

    return render(request, "frontend/upload_researchers.html")


def edit_research(request, pk):
    """تعديل بحث داخل النظام"""
    research = get_object_or_404(Research, pk=pk)

    if request.method == "POST":
        try:
            research.researcher_name = request.POST.get("researcher_name", "").strip()
            research.title = request.POST.get("title", "").strip()
            research.degree = request.POST.get("degree")
            research.researcher_type = request.POST.get("researcher_type")
            research.status = request.POST.get("status")
            research.status_note = request.POST.get("status_note", "").strip()

            dept_id = request.POST.get("department")
            research.department_id = int(dept_id) if dept_id else None

            research.phone = (request.POST.get("phone", "") or "").strip() or None

            # التواريخ (نخليها تتحدث أو تتفضى)
            research.registration_date = request.POST.get("registration_date") or None
            research.frame_date = request.POST.get("frame_date") or None
            research.university_approval_date = request.POST.get("university_approval_date") or None

            # مصروفات السنة الحالية (سجل سنوي في ResearchFeePayment)
            fees_paid = request.POST.get("fees_paid") == "on"
            current_year = timezone.localdate().year
            payment, _ = ResearchFeePayment.objects.get_or_create(
                research=research,
                year=current_year,
                defaults={"is_paid": False},
            )
            if fees_paid and not payment.is_paid:
                payment.mark_paid()
            elif (not fees_paid) and payment.is_paid:
                payment.mark_unpaid()


            research.save()

            supervisor_ids = request.POST.getlist("supervisors")
            if supervisor_ids is not None:
                ResearchSupervision.objects.filter(research=research).delete()
                for sup_id in supervisor_ids:
                    supervisor = Supervisor.objects.get(id=int(sup_id))
                    ResearchSupervision.objects.create(research=research, supervisor=supervisor)

            messages.success(request, f"تم تحديث {research.researcher_name}")
            return redirect("dashboard")

        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")

    all_supervisors = Supervisor.objects.filter(is_active=True).order_by("name")
    all_departments = Department.objects.all().order_by("name")
    current_supervisors = [link.supervisor.id for link in research.researchsupervision_set.all()]
    current_year = timezone.now().year
    ResearchFeePayment.objects.get_or_create(research=research, year=current_year, defaults={"is_paid": False})
    payments = list(research.fee_payments.all().order_by('-year'))

    return render(request, "frontend/edit_research.html", {
        "research": research,
        "all_supervisors": all_supervisors,
        "all_departments": all_departments,
        "current_supervisors": current_supervisors,
        "payments": payments,
    })


def add_researcher(request):
    """إضافة باحث جديد"""
    if request.method == "POST":
        try:
            researcher_name = request.POST.get("researcher_name", "").strip()
            degree = request.POST.get("degree")
            researcher_type = request.POST.get("researcher_type")
            title = request.POST.get("title", "").strip()
            status = request.POST.get("status")
            status_note = request.POST.get("status_note", "").strip()
            dept_id = request.POST.get("department")

            phone = (request.POST.get("phone", "") or "").strip() or None
            fees_paid = request.POST.get("fees_paid") == "on"

            reg_date = request.POST.get("registration_date") or None
            frame_date = request.POST.get("frame_date") or None
            univ_date = request.POST.get("university_approval_date") or None

            if not researcher_name:
                messages.error(request, "يجب إدخال اسم الباحث")
                return redirect("add_researcher")

            research = Research.objects.create(
                researcher_name=researcher_name,
                degree=degree,
                researcher_type=researcher_type,
                title=title,
                status=status,
                status_note=status_note,
                department_id=int(dept_id) if dept_id else None,
                phone=phone,
                registration_date=reg_date,
                frame_date=frame_date,
                university_approval_date=univ_date,
            )

            # مصروفات السنة الحالية (سجل سنوي في ResearchFeePayment)
            current_year = timezone.localdate().year
            payment, _ = ResearchFeePayment.objects.get_or_create(
                research=research,
                year=current_year,
                defaults={"is_paid": False},
            )
            if fees_paid:
                payment.mark_paid()
            else:
                payment.mark_unpaid()

            supervisor_ids = request.POST.getlist("supervisors")
            if supervisor_ids:
                for sup_id in supervisor_ids:
                    supervisor = Supervisor.objects.get(id=int(sup_id))
                    ResearchSupervision.objects.create(research=research, supervisor=supervisor)
            fees_data_str = request.POST.get("fees_data", "{}")
            try:
                fees_data = json.loads(fees_data_str)  # {2025: true, 2024: false}
                for year_str, is_paid in fees_data.items():
                    payment, _ = ResearchFeePayment.objects.get_or_create(
                        research=research,
                        year=int(year_str),
                        defaults={"is_paid": False},
                    )
                    if bool(is_paid):
                        payment.mark_paid()
                    else:
                        payment.mark_unpaid()
            except:
                pass  # إذا مفيش مصروفات، عادي
            messages.success(request, f"تم إضافة الباحث: {researcher_name}")
            return redirect("researchers_page")

        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
            return redirect("add_researcher")

    all_supervisors = Supervisor.objects.filter(is_active=True).order_by("name")
    all_departments = Department.objects.all().order_by("name")

    return render(request, "frontend/add_researcher.html", {
        "all_supervisors": all_supervisors,
        "all_departments": all_departments,
    })


def add_supervisor(request):
    """إضافة مشرف جديد"""
    if request.method == "POST":
        try:
            name = request.POST.get("name", "").strip()
            dept_id = request.POST.get("department")
            is_active = request.POST.get("is_active") == "true"
            
            if not name:
                messages.error(request, "يجب إدخال اسم المشرف")
                return redirect("add_supervisor")
            
            if not dept_id:
                messages.error(request, "يجب اختيار القسم")
                return redirect("add_supervisor")
            
            # إنشاء المشرف
            supervisor = Supervisor.objects.create(
                name=name,
                department_id=int(dept_id),
                is_active=is_active
            )
            
            messages.success(request, f"تم إضافة المشرف: {name}")
            return redirect("supervisors_page")
            
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
            return redirect("add_supervisor")
    
    # GET request
    all_departments = Department.objects.all().order_by("name")
    
    return render(request, "frontend/add_supervisor.html", {
        "all_departments": all_departments,
    })


def delete_research(request, pk):
    """حذف بحث"""
    research = get_object_or_404(Research, pk=pk)
    name = research.researcher_name
    research.delete()
    messages.success(request, f"تم حذف الباحث: {name}")
    return redirect("researchers_page")


def delete_supervisor(request, pk):
    """حذف مشرف"""
    supervisor = get_object_or_404(Supervisor, pk=pk)
    name = supervisor.name
    
    # حذف كل الارتباطات أولاً
    ResearchSupervision.objects.filter(supervisor=supervisor).delete()
    
    # حذف المشرف
    supervisor.delete()
    
    messages.success(request, f"تم حذف المشرف: {name}")
    return redirect("supervisors_page")


# ═══════════════════════════════════════════════════════════
# إدارة المصروفات
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# إدارة المصروفات (سنوية) - باستخدام ResearchFeePayment
# ═══════════════════════════════════════════════════════════

from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from core.models import Research, ResearchFeePayment

def toggle_fees_status(request, research_id, year):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    research = get_object_or_404(Research, id=research_id)
    year = int(year)

    payment, _ = ResearchFeePayment.objects.get_or_create(
        research=research,
        year=year,
        defaults={"is_paid": False},
    )

    if payment.is_paid:
        payment.mark_unpaid()
        status = "unpaid"
    else:
        payment.mark_paid()
        status = "paid"

    return JsonResponse({
        "success": True,
        "year": year,
        "status": status,
        "status_display": "دفع" if status == "paid" else "لم يدفع",
    })


def add_fees_year(request, research_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    research = get_object_or_404(Research, id=research_id)
    year_raw = (request.POST.get("year") or "").strip()

    if not year_raw.isdigit():
        return JsonResponse({"error": "Year is required"}, status=400)

    year = int(year_raw)

    payment, created = ResearchFeePayment.objects.get_or_create(
        research=research,
        year=year,
        defaults={"is_paid": False},
    )

    return JsonResponse({
        "success": True,
        "created": created,
        "year": year,
        "status": "paid" if payment.is_paid else "unpaid",
        "status_display": "دفع" if payment.is_paid else "لم يدفع",
    })
def delete_fees_year(request, research_id, year):
    """حذف سنة من المصروفات"""
    if request.method != "POST":
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    research = get_object_or_404(Research, id=research_id)
    
    # حذف السنة
    deleted_count, _ = ResearchFeePayment.objects.filter(
        research=research, 
        year=int(year)
    ).delete()
    
    if deleted_count > 0:
        return JsonResponse({
            'success': True,
            'year': year,
            'message': f'تم حذف سنة {year} بنجاح'
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'السنة غير موجودة'
        }, status=404)


# ═══════════════════════════════════════════════════════════
# تعديل المشرف (بدون email/phone/image)
# ═══════════════════════════════════════════════════════════

def edit_supervisor(request, supervisor_id):
    """تعديل بيانات المشرف (بدون email/phone)"""
    supervisor = get_object_or_404(Supervisor, id=supervisor_id)

    if request.method == "POST":
        try:
            supervisor.name = (request.POST.get("name", "") or "").strip() or supervisor.name

            dept_id = request.POST.get("department_id")
            supervisor.department_id = int(dept_id) if dept_id else None

            supervisor.is_active = request.POST.get("is_active") == "on"

            supervisor.save()
            messages.success(request, "تم تحديث بيانات المشرف بنجاح")
            return redirect("supervisor_detail", pk=supervisor_id)
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")

    departments = Department.objects.all().order_by("name")
    return render(request, "frontend/edit_supervisor.html", {
        "supervisor": supervisor,
        "departments": departments
    })
