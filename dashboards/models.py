from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DashboardCategory(TimestampedModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "dashboard categories"

    def __str__(self):
        return self.name


class Company(TimestampedModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class FinancialPeriod(TimestampedModel):
    year = models.PositiveSmallIntegerField(unique=True, validators=[MinValueValidator(1900)])

    class Meta:
        ordering = ["year"]

    def __str__(self):
        return str(self.year)


class MetricDefinition(TimestampedModel):
    class UnitType(models.TextChoices):
        MONEY = "money", "Money"
        PERCENT = "percent", "Percent"
        RATIO = "ratio", "Ratio"
        COUNT = "count", "Count"
        TEXT = "text", "Text"

    category = models.ForeignKey(DashboardCategory, on_delete=models.CASCADE, related_name="metrics")
    key = models.SlugField()
    label = models.CharField(max_length=160)
    unit_type = models.CharField(max_length=20, choices=UnitType.choices, default=UnitType.MONEY)
    aliases = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category__name", "label"]
        constraints = [
            models.UniqueConstraint(fields=["category", "key"], name="unique_metric_key_per_category")
        ]

    def __str__(self):
        return f"{self.category}: {self.label}"


class WorkbookImport(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    category = models.ForeignKey(DashboardCategory, on_delete=models.PROTECT, related_name="workbook_imports")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="workbook_imports",
    )
    original_filename = models.CharField(max_length=255)
    workbook_file = models.FileField(upload_to="private_workbooks/%Y/%m/")
    file_sha256 = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    parser_version = models.CharField(max_length=40, default="bwa-v1")
    row_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.category} import {self.pk or 'new'} ({self.status})"

    def mark_processing(self):
        self.status = self.Status.PROCESSING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])

    def mark_completed(self, row_count=0, warning_count=0):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.row_count = row_count
        self.warning_count = warning_count
        self.save(update_fields=["status", "completed_at", "row_count", "warning_count", "updated_at"])

    def mark_failed(self, message):
        self.status = self.Status.FAILED
        self.completed_at = timezone.now()
        self.error_summary = str(message)[:4000]
        self.save(update_fields=["status", "completed_at", "error_summary", "updated_at"])


class FinancialValue(TimestampedModel):
    category = models.ForeignKey(DashboardCategory, on_delete=models.CASCADE, related_name="financial_values")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="financial_values")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="financial_values")
    metric = models.ForeignKey(MetricDefinition, on_delete=models.PROTECT, related_name="financial_values")
    value = models.DecimalField(max_digits=24, decimal_places=6)
    source_import = models.ForeignKey(
        WorkbookImport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_values",
    )

    class Meta:
        ordering = ["category__name", "period__year", "company__name", "metric__label"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "company", "period", "metric"],
                name="unique_financial_value",
            )
        ]

    def __str__(self):
        return f"{self.category} {self.company} {self.period} {self.metric.key}: {self.value}"


class ImportChange(TimestampedModel):
    import_record = models.ForeignKey(WorkbookImport, on_delete=models.CASCADE, related_name="changes")
    category = models.ForeignKey(DashboardCategory, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT)
    metric = models.ForeignKey(MetricDefinition, on_delete=models.PROTECT)
    old_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    new_value = models.DecimalField(max_digits=24, decimal_places=6)

    class Meta:
        ordering = ["period__year", "company__name", "metric__label"]

    def __str__(self):
        return f"{self.metric.label}: {self.old_value} -> {self.new_value}"


class MarketShareValue(TimestampedModel):
    class MetricType(models.TextChoices):
        REVENUE = "revenue", "Revenue"
        PROFITABILITY = "profitability", "Profitability"
        ENTERPRISE = "enterprise", "Enterprise Value"

    category = models.ForeignKey(DashboardCategory, on_delete=models.CASCADE, related_name="market_share_values")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="market_share_values")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="market_share_values")
    metric_type = models.CharField(max_length=32, choices=MetricType.choices)
    value = models.DecimalField(max_digits=16, decimal_places=8)
    source_import = models.ForeignKey(
        WorkbookImport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="market_share_values",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "company", "period", "metric_type"],
                name="unique_market_share_value",
            )
        ]


class RegulatoryFeeValue(TimestampedModel):
    category = models.ForeignKey(DashboardCategory, on_delete=models.CASCADE, related_name="regulatory_fee_values")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="regulatory_fee_values")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="regulatory_fee_values")
    invoice_issued = models.DecimalField(max_digits=24, decimal_places=6, default=0)
    payment_received = models.DecimalField(max_digits=24, decimal_places=6, default=0)
    outstanding = models.DecimalField(max_digits=24, decimal_places=6, default=0)
    fee_to_revenue = models.DecimalField(max_digits=16, decimal_places=8, default=0)
    source_import = models.ForeignKey(
        WorkbookImport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="regulatory_fee_values",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "company", "period"],
                name="unique_regulatory_fee_value",
            )
        ]


class DashboardNote(TimestampedModel):
    category = models.ForeignKey(DashboardCategory, on_delete=models.CASCADE, related_name="notes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_notes")
    body = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["category", "user"], name="unique_dashboard_note_per_user")
        ]

    def __str__(self):
        return f"{self.category} note for {self.user}"
