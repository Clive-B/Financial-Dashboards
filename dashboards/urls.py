from django.urls import path

from . import views


urlpatterns = [
    path("<slug:slug>/", views.dashboard_detail, name="dashboard-detail"),
    path("<slug:slug>/api/metrics/", views.dashboard_metrics_api, name="dashboard-metrics-api"),
    path("<slug:slug>/api/fees/", views.dashboard_fees_api, name="dashboard-fees-api"),
]
