from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse

from workbooks.forms import WorkbookUploadForm
from workbooks.services.importer import import_workbook

from .models import (
    Company,
    DashboardCategory,
    DashboardNote,
    FinancialPeriod,
    FinancialValue,
    ImportChange,
    MarketShareValue,
    MetricDefinition,
    RegulatoryFeeValue,
    WorkbookImport,
)


@admin.register(DashboardCategory)
class DashboardCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


@admin.register(FinancialPeriod)
class FinancialPeriodAdmin(admin.ModelAdmin):
    list_display = ("year", "updated_at")
    search_fields = ("year",)


@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "category", "unit_type", "is_active")
    list_filter = ("category", "unit_type", "is_active")
    search_fields = ("label", "key", "aliases")


class ImportChangeInline(admin.TabularInline):
    model = ImportChange
    extra = 0
    can_delete = False
    readonly_fields = ("category", "company", "period", "metric", "old_value", "new_value", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(WorkbookImport)
class WorkbookImportAdmin(admin.ModelAdmin):
    change_list_template = "admin/dashboards/workbookimport/change_list.html"
    list_display = (
        "id",
        "category",
        "original_filename",
        "status",
        "uploaded_by",
        "row_count",
        "warning_count",
        "created_at",
    )
    list_filter = ("category", "status", "created_at")
    search_fields = ("original_filename", "file_sha256", "error_summary")
    readonly_fields = (
        "uploaded_by",
        "original_filename",
        "file_sha256",
        "status",
        "parser_version",
        "row_count",
        "warning_count",
        "error_summary",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    )
    inlines = [ImportChangeInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

    def add_view(self, request, form_url="", extra_context=None):
        return redirect(reverse("admin:dashboards_workbookimport_upload"))

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "upload-workbook/",
                self.admin_site.admin_view(self.upload_workbook_view),
                name="dashboards_workbookimport_upload",
            )
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["upload_workbook_url"] = "upload-workbook/"
        return super().changelist_view(request, extra_context=extra_context)

    def upload_workbook_view(self, request):
        if request.method == "POST":
            form = WorkbookUploadForm(request.POST, request.FILES)
            if form.is_valid():
                upload = form.cleaned_data["workbook_file"]
                import_record = WorkbookImport.objects.create(
                    category=form.cleaned_data["category"],
                    uploaded_by=request.user,
                    original_filename=upload.name,
                    workbook_file=upload,
                )
                try:
                    result = import_workbook(import_record)
                except Exception as exc:
                    import_record.mark_failed(exc)
                    self.message_user(request, f"Workbook import failed: {exc}", level=messages.ERROR)
                else:
                    self.message_user(
                        request,
                        f"Imported {result.row_count} values with {result.change_count} changes.",
                        level=messages.SUCCESS,
                    )
                return redirect("admin:dashboards_workbookimport_change", import_record.pk)
        else:
            form = WorkbookUploadForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Upload financial workbook",
            "form": form,
        }
        return render(request, "admin/workbooks/upload_workbook.html", context)


@admin.register(FinancialValue)
class FinancialValueAdmin(admin.ModelAdmin):
    list_display = ("category", "company", "period", "metric", "value", "source_import")
    list_filter = ("category", "company", "period", "metric")
    search_fields = ("company__name", "metric__label")


@admin.register(ImportChange)
class ImportChangeAdmin(admin.ModelAdmin):
    list_display = ("import_record", "category", "company", "period", "metric", "old_value", "new_value")
    list_filter = ("category", "company", "period", "metric")
    search_fields = ("company__name", "metric__label")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MarketShareValue)
class MarketShareValueAdmin(admin.ModelAdmin):
    list_display = ("category", "company", "period", "metric_type", "value", "source_import")
    list_filter = ("category", "company", "period", "metric_type")


@admin.register(RegulatoryFeeValue)
class RegulatoryFeeValueAdmin(admin.ModelAdmin):
    list_display = ("category", "company", "period", "payment_received", "invoice_issued", "fee_to_revenue")
    list_filter = ("category", "company", "period")


@admin.register(DashboardNote)
class DashboardNoteAdmin(admin.ModelAdmin):
    list_display = ("category", "user", "updated_at")
    list_filter = ("category", "updated_at")
    search_fields = ("user__username", "body")
