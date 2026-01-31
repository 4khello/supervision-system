from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # ✅ فرونت
    path("", include("core.urls_frontend")),
]