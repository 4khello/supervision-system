from django.urls import path
from . import views_frontend

urlpatterns = [
    # الصفحة الرئيسية الجديدة
    path("", views_frontend.home, name="home"),
    path("home-department-stats/", views_frontend.home, name="home_department_stats"),
    
    # Dashboard القديم - إعادة توجيه للصفحة الرئيسية
    path("dashboard/", views_frontend.home, name="dashboard"),
    
    # صفحة الاختيار (مشرفين أو باحثين)
    path("choose/", views_frontend.choose_page, name="choose_page"),
    
    # المشرفين
    path("supervisors/", views_frontend.supervisors_page, name="supervisors_page"),
    path("supervisors/<int:pk>/", views_frontend.supervisor_detail, name="supervisor_detail"),
    
    # الباحثين
    path("researchers/", views_frontend.researchers_page, name="researchers_page"),
    path("research/<int:pk>/", views_frontend.research_detail, name="research_detail"),
    
    # الإحصائيات
    path("stats/", views_frontend.stats_page, name="stats_page"),
    path("department-stats/", views_frontend.department_stats, name="department_stats"),
    
    # API للإحصائيات التفاعلية
    path("api/stat-details/<str:stat_type>/", views_frontend.stat_details, name="stat_details"),
    path("api/home-stat-details/<str:stat_type>/", views_frontend.home_stat_details, name="home_stat_details"),
    
    # رفع الباحثين من Excel
    path("upload_researchers/", views_frontend.upload_researchers, name="upload_researchers"),
    
    # تعديل بحث (داخل النظام)
    path("edit-research/<int:pk>/", views_frontend.edit_research, name="edit_research"),
    path("delete-research/<int:pk>/", views_frontend.delete_research, name="delete_research"),
    path("delete-supervisor/<int:pk>/", views_frontend.delete_supervisor, name="delete_supervisor"),
    
    # إضافة باحث ومشرف جديد
    path("add-researcher/", views_frontend.add_researcher, name="add_researcher"),
    path("add-supervisor/", views_frontend.add_supervisor, name="add_supervisor"),
    
    # تصدير Excel
    path("export.xlsx", views_frontend.export_excel, name="export_excel"),
    path("export-department.xlsx", views_frontend.export_department_excel, name="export_department_excel"),
]