from django.contrib import admin
from django.urls import include, path
from two_factor.urls import urlpatterns as two_factor_urlpatterns

from dashboards import views as dashboard_views


urlpatterns = [
    path("", dashboard_views.dashboard_index, name="dashboard-index"),
    path("dashboards/", include("dashboards.urls")),
    path("", include((two_factor_urlpatterns[0], "two_factor"), namespace="two_factor")),
    path("admin/", admin.site.urls),
]
