import django.db.models.deletion
from django.core.validators import MinValueValidator
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=120)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"], "verbose_name_plural": "companies"},
        ),
        migrations.CreateModel(
            name="DashboardCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"], "verbose_name_plural": "dashboard categories"},
        ),
        migrations.CreateModel(
            name="FinancialPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("year", models.PositiveSmallIntegerField(unique=True, validators=[MinValueValidator(1900)])),
            ],
            options={"ordering": ["year"]},
        ),
        migrations.CreateModel(
            name="MetricDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.SlugField()),
                ("label", models.CharField(max_length=160)),
                (
                    "unit_type",
                    models.CharField(
                        choices=[
                            ("money", "Money"),
                            ("percent", "Percent"),
                            ("ratio", "Ratio"),
                            ("count", "Count"),
                            ("text", "Text"),
                        ],
                        default="money",
                        max_length=20,
                    ),
                ),
                ("aliases", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "category",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="metrics", to="dashboards.dashboardcategory"),
                ),
            ],
            options={"ordering": ["category__name", "label"]},
        ),
        migrations.CreateModel(
            name="WorkbookImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("original_filename", models.CharField(max_length=255)),
                ("workbook_file", models.FileField(upload_to="private_workbooks/%Y/%m/")),
                ("file_sha256", models.CharField(blank=True, max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("parser_version", models.CharField(default="bwa-v1", max_length=40)),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("warning_count", models.PositiveIntegerField(default=0)),
                ("error_summary", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="workbook_imports",
                        to="dashboards.dashboardcategory",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="workbook_imports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DashboardNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("body", models.TextField(blank=True)),
                (
                    "category",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notes", to="dashboards.dashboardcategory"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dashboard_notes", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="FinancialValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("value", models.DecimalField(decimal_places=6, max_digits=24)),
                (
                    "category",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="financial_values", to="dashboards.dashboardcategory"),
                ),
                (
                    "company",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="financial_values", to="dashboards.company"),
                ),
                (
                    "metric",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="financial_values", to="dashboards.metricdefinition"),
                ),
                (
                    "period",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="financial_values", to="dashboards.financialperiod"),
                ),
                (
                    "source_import",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="financial_values",
                        to="dashboards.workbookimport",
                    ),
                ),
            ],
            options={"ordering": ["category__name", "period__year", "company__name", "metric__label"]},
        ),
        migrations.CreateModel(
            name="ImportChange",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("old_value", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("new_value", models.DecimalField(decimal_places=6, max_digits=24)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="dashboards.dashboardcategory")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="dashboards.company")),
                (
                    "import_record",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="changes", to="dashboards.workbookimport"),
                ),
                ("metric", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="dashboards.metricdefinition")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="dashboards.financialperiod")),
            ],
            options={"ordering": ["period__year", "company__name", "metric__label"]},
        ),
        migrations.CreateModel(
            name="MarketShareValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "metric_type",
                    models.CharField(
                        choices=[("revenue", "Revenue"), ("profitability", "Profitability"), ("enterprise", "Enterprise Value")],
                        max_length=32,
                    ),
                ),
                ("value", models.DecimalField(decimal_places=8, max_digits=16)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="market_share_values",
                        to="dashboards.dashboardcategory",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="market_share_values", to="dashboards.company"),
                ),
                (
                    "period",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="market_share_values", to="dashboards.financialperiod"),
                ),
                (
                    "source_import",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="market_share_values",
                        to="dashboards.workbookimport",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RegulatoryFeeValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("invoice_issued", models.DecimalField(decimal_places=6, default=0, max_digits=24)),
                ("payment_received", models.DecimalField(decimal_places=6, default=0, max_digits=24)),
                ("outstanding", models.DecimalField(decimal_places=6, default=0, max_digits=24)),
                ("fee_to_revenue", models.DecimalField(decimal_places=8, default=0, max_digits=16)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="regulatory_fee_values",
                        to="dashboards.dashboardcategory",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="regulatory_fee_values", to="dashboards.company"),
                ),
                (
                    "period",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="regulatory_fee_values", to="dashboards.financialperiod"),
                ),
                (
                    "source_import",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="regulatory_fee_values",
                        to="dashboards.workbookimport",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="metricdefinition",
            constraint=models.UniqueConstraint(fields=("category", "key"), name="unique_metric_key_per_category"),
        ),
        migrations.AddConstraint(
            model_name="dashboardnote",
            constraint=models.UniqueConstraint(fields=("category", "user"), name="unique_dashboard_note_per_user"),
        ),
        migrations.AddConstraint(
            model_name="financialvalue",
            constraint=models.UniqueConstraint(fields=("category", "company", "period", "metric"), name="unique_financial_value"),
        ),
        migrations.AddConstraint(
            model_name="marketsharevalue",
            constraint=models.UniqueConstraint(
                fields=("category", "company", "period", "metric_type"),
                name="unique_market_share_value",
            ),
        ),
        migrations.AddConstraint(
            model_name="regulatoryfeevalue",
            constraint=models.UniqueConstraint(fields=("category", "company", "period"), name="unique_regulatory_fee_value"),
        ),
    ]
