from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import DashboardCategory, FinancialValue


@login_required
def dashboard_index(request):
    categories = DashboardCategory.objects.filter(is_active=True)
    return render(request, "dashboards/index.html", {"categories": categories})


@login_required
def dashboard_detail(request, slug):
    category = get_object_or_404(DashboardCategory, slug=slug, is_active=True)
    return render(request, "dashboards/detail.html", {"category": category})


@login_required
def dashboard_fees_api(request, slug):
    category = get_object_or_404(DashboardCategory, slug=slug, is_active=True)
    from .models import RegulatoryFeeValue
    fees = (
        RegulatoryFeeValue.objects.filter(category=category)
        .select_related("company", "period")
        .order_by("period__year", "company__name")
    )
    payload = [
        {
            "year": f.period.year,
            "company": f.company.name,
            "company_slug": f.company.slug,
            "invoice_issued": str(f.invoice_issued),
            "payment_received": str(f.payment_received),
            "outstanding": str(f.outstanding),
        }
        for f in fees
    ]
    return JsonResponse({"category": category.slug, "results": payload})


@login_required
def dashboard_metrics_api(request, slug):
    category = get_object_or_404(DashboardCategory, slug=slug, is_active=True)
    values = (
        FinancialValue.objects.filter(category=category)
        .select_related("company", "period", "metric")
        .order_by("period__year", "company__name", "metric__label")
    )
    year = request.GET.get("year")
    company = request.GET.get("company")
    metric = request.GET.get("metric")

    if year and year != "all":
        values = values.filter(period__year=year)
    if company and company != "all":
        values = values.filter(company__slug=company)
    if metric and metric != "all":
        values = values.filter(metric__key=metric)

    payload = [
        {
            "year": item.period.year,
            "company": item.company.name,
            "company_slug": item.company.slug,
            "metric": item.metric.key,
            "metric_label": item.metric.label,
            "unit_type": item.metric.unit_type,
            "value": str(item.value),
        }
        for item in values[:5000]
    ]
    return JsonResponse({"category": category.slug, "results": payload})
