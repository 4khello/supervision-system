from django.urls import path
from . import views_frontend

urlpatterns = [
    path("", views_frontend.home, name="home"),
    path("home-department-stats/", views_frontend.home, name="home_department_stats"),
    path("dashboard/", views_frontend.home, name="dashboard"),

    path("choose/", views_frontend.choose_page, name="choose_page"),

    path("supervisors/", views_frontend.supervisors_page, name="supervisors_page"),
    path("supervisors/<int:pk>/", views_frontend.supervisor_detail, name="supervisor_detail"),
    path("add-supervisor/", views_frontend.add_supervisor, name="add_supervisor"),
    path("supervisor/<int:supervisor_id>/edit/", views_frontend.edit_supervisor, name="edit_supervisor"),
    path("delete-supervisor/<int:pk>/", views_frontend.delete_supervisor, name="delete_supervisor"),

    path("researchers/", views_frontend.researchers_page, name="researchers_page"),
    path("research/<int:pk>/", views_frontend.research_detail, name="research_detail"),
    path("add-researcher/", views_frontend.add_researcher, name="add_researcher"),
    path("edit-research/<int:pk>/", views_frontend.edit_research, name="edit_research"),
    path("delete-research/<int:pk>/", views_frontend.delete_research, name="delete_research"),

    path("stats/", views_frontend.stats_page, name="stats_page"),
    path("department-stats/", views_frontend.department_stats, name="department_stats"),

    path("api/stat-details/<str:stat_type>/", views_frontend.stat_details, name="stat_details"),
    path("api/home-stat-details/<str:stat_type>/", views_frontend.home_stat_details, name="home_stat_details"),

    path("upload_researchers/", views_frontend.upload_researchers, name="upload_researchers"),
    path("export.xlsx", views_frontend.export_excel, name="export_excel"),
    path("export-department.xlsx", views_frontend.export_department_excel, name="export_department_excel"),

    # ✅ إدارة المصروفات (سنوي)
    path(
        "research/<int:research_id>/toggle-fees/<int:year>/",
        views_frontend.toggle_fees_status,
        name="toggle_fees_status",
    ),
    path(
        "research/<int:research_id>/add-fees-year/",
        views_frontend.add_fees_year,
        name="add_fees_year",
    ),

    # ✅ حذف سنة من المصروفات
    path(
        "research/<int:research_id>/delete-fees-year/<int:year>/",
        views_frontend.delete_fees_year,
        name="delete_fees_year",
    ),
]