# =========================================
# file: core/urls.py
# =========================================
from django.urls import path
from .views import supervisors_list, supervisor_detail

urlpatterns = [
    path("supervisors/", supervisors_list, name="supervisors_list"),
    path("supervisors/<int:pk>/", supervisor_detail, name="supervisor_detail"),
]