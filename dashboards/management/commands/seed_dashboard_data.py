"""
Seed the embedded financial data from the static HTML dashboards into the
database so every dashboard shows data immediately, without requiring an
admin workbook upload first.

Run after seed_reference_data:
    python manage.py seed_reference_data
    python manage.py seed_dashboard_data

Safe to re-run — uses update_or_create throughout.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from dashboards.models import (
    Company,
    DashboardCategory,
    FinancialPeriod,
    FinancialValue,
    MetricDefinition,
    RegulatoryFeeValue,
)

# ---------------------------------------------------------------------------
# Embedded financial data (lifted from the static HTML DEFAULT_PAYLOAD blocks)
# Keys match MetricDefinition.key values (hyphenated slugs).
# Values are raw numbers; percent metrics stored as decimals (0.0358 = 3.58 %).
# None means no data for that metric/year — row is skipped.
# ---------------------------------------------------------------------------

BWA_DATA = {
    "category": "bwa",
    "company":  "telesol",
    "years": {
        2021: {
            "revenue": 1720193, "expenditure": 1012443, "cost-of-sales": 646121,
            "gross-profit": 1074072, "ebitda": 61629, "ebitda-margin": 0.0358,
            "net-profit": 1939, "capex": None,
            "net-profit-margin": 0.0011, "net-profit-before-tax": 10384,
            "current-assets": 515942, "non-current-assets": 29257902,
            "total-assets": 29773844, "current-liabilities": 210501,
            "non-current-liabilities": 62034092, "total-liabilities": 62244593,
            "cash": 312993, "total-equity": -32470749,
            "total-debt": 715107, "enterprise-value": -32068635,
        },
        2022: {
            "revenue": 1589611, "expenditure": 1077219, "cost-of-sales": 380123,
            "gross-profit": 1209488, "ebitda": 132269, "ebitda-margin": 0.0832,
            "net-profit": 67136, "capex": None,
            "net-profit-margin": 0.0422, "net-profit-before-tax": 83707,
            "current-assets": 474247, "non-current-assets": 29228919,
            "total-assets": 29703166, "current-liabilities": 220145,
            "non-current-liabilities": 61886633, "total-liabilities": 62106778,
            "cash": 467108, "total-equity": -32403613,
            "total-debt": 565997, "enterprise-value": -32304724,
        },
    },
}

ICH_DATA = {
    "category": "ich",
    "company":  "afriwave",
    "years": {
        2021: {
            "revenue": 37410476, "expenditure": 17177933, "cost-of-sales": 18753687,
            "gross-profit": 18656789, "ebitda": 11455107, "ebitda-margin": 0.3062,
            "net-profit": -4893501, "capex": 39829752,
            "net-profit-margin": -0.1308, "net-profit-before-tax": -4893501,
            "current-assets": 23084743, "non-current-assets": 65136722,
            "total-assets": 88221465, "current-liabilities": 78684711,
            "non-current-liabilities": 48364902, "total-liabilities": 127049613,
            "cash": 1540680, "total-equity": -38828147,
            "total-debt": 50458077, "enterprise-value": 10089250,
        },
        2022: {
            "revenue": 56516635, "expenditure": 25087850, "cost-of-sales": 27354581,
            "gross-profit": 29162054, "ebitda": 12399347, "ebitda-margin": 0.2194,
            "net-profit": -10747351, "capex": None,
            "net-profit-margin": -0.1902, "net-profit-before-tax": -3953726,
            "current-assets": 32424087, "non-current-assets": 57381263,
            "total-assets": 89805350, "current-liabilities": 89835228,
            "non-current-liabilities": 49545620, "total-liabilities": 139380848,
            "cash": 1481612, "total-equity": -49575498,
            "total-debt": 45676316, "enterprise-value": -5380794,
        },
        2023: {
            "revenue": 62316482, "expenditure": 19805544, "cost-of-sales": 29846345,
            "gross-profit": 32470137, "ebitda": 25958628, "ebitda-margin": 0.4166,
            "net-profit": 4129747, "capex": 0,
            "net-profit-margin": 0.0663, "net-profit-before-tax": 4129747,
            "current-assets": 39956804, "non-current-assets": 49671705,
            "total-assets": 89628509, "current-liabilities": 85708331,
            "non-current-liabilities": 49365929, "total-liabilities": 135074260,
            "cash": 3502488, "total-equity": -45445751,
            "total-debt": 43260700, "enterprise-value": -5687539,
        },
        2024: {
            "revenue": 67224916, "expenditure": 20698132, "cost-of-sales": 32698132,
            "gross-profit": 34526784, "ebitda": 31493584, "ebitda-margin": 0.4685,
            "net-profit": 10638244, "capex": 0,
            "net-profit-margin": 0.1582, "net-profit-before-tax": 16650072,
            "current-assets": 53620180, "non-current-assets": 43085589,
            "total-assets": 96705769, "current-liabilities": 88788718,
            "non-current-liabilities": 42724558, "total-liabilities": 131513276,
            "cash": 2998276, "total-equity": -34807507,
            "total-debt": 35931635, "enterprise-value": -1874148,
        },
    },
    # 1 % regulatory payments received (from the ICH payments sheet)
    "payments": {
        2017: {"invoice_issued": 0,         "payment_received": 7573837.16,   "outstanding": -7573837.16},
        2018: {"invoice_issued": 0,         "payment_received": 32959374.78,  "outstanding": -32959374.78},
        2019: {"invoice_issued": 0,         "payment_received": 40416718.87,  "outstanding": -40416718.87},
        2020: {"invoice_issued": 0,         "payment_received": 46152772.33,  "outstanding": -46152772.33},
        2021: {"invoice_issued": 0,         "payment_received": 58170086.00,  "outstanding": -58170086.00},
        2022: {"invoice_issued": 0,         "payment_received": 79169470.99,  "outstanding": -79169470.99},
        2023: {"invoice_issued": 0,         "payment_received": 104234913.33, "outstanding": -104234913.33},
        2024: {"invoice_issued": 0,         "payment_received": 131649797.25, "outstanding": -131649797.25},
        2025: {"invoice_issued": 0,         "payment_received": 129315514.87, "outstanding": -129315514.87},
    },
}

PAY_TV_DATA = {
    "category": "pay-television",
    "company":  "dstv",
    "years": {
        2020: {
            "revenue": 92395421, "expenditure": 29406456, "cost-of-sales": 60772609,
            "gross-profit": 31622812, "ebitda": 5273225, "ebitda-margin": 0.0571,
            "net-profit": 2525771, "capex": 4102411,
            "net-profit-margin": 0.0273, "net-profit-before-tax": 1914556,
            "current-assets": 28286339, "non-current-assets": 38473029,
            "total-assets": 66759368, "current-liabilities": 24395445,
            "non-current-liabilities": 1354447, "total-liabilities": 25749892,
            "cash": 9133466, "total-equity": 41009476,
            "total-debt": 6448906, "enterprise-value": 38324916,
        },
        2021: {
            "revenue": 96360812, "expenditure": 31458409, "cost-of-sales": 61349467,
            "gross-profit": 35011345, "ebitda": 6615983, "ebitda-margin": 0.0687,
            "net-profit": 956377, "capex": 4822488,
            "net-profit-margin": 0.0099, "net-profit-before-tax": 2785706,
            "current-assets": 3955072, "non-current-assets": 35288678,
            "total-assets": 39243750, "current-liabilities": 34122502,
            "non-current-liabilities": 1037184, "total-liabilities": 35159686,
            "cash": 11377265, "total-equity": 39679712,
            "total-debt": 12732089, "enterprise-value": 41034536,
        },
        2022: {
            "revenue": 117052853, "expenditure": 45827174, "cost-of-sales": 63276043,
            "gross-profit": 53776810, "ebitda": 7949636, "ebitda-margin": 0.0679,
            "net-profit": 1330559, "capex": 5904431,
            "net-profit-margin": 0.0114, "net-profit-before-tax": 2638602,
            "current-assets": 58134995, "non-current-assets": 38747329,
            "total-assets": 96882324, "current-liabilities": 53633024,
            "non-current-liabilities": 2169480, "total-liabilities": 55802504,
            "cash": 11561233, "total-equity": 41079820,
            "total-debt": 19674636, "enterprise-value": 49193223,
        },
        2023: {
            "revenue": 155125849, "expenditure": 64027798, "cost-of-sales": 74656288,
            "gross-profit": 80469561, "ebitda": 16441763, "ebitda-margin": 0.1060,
            "net-profit": -24284082, "capex": 7802342,
            "net-profit-margin": -0.1565, "net-profit-before-tax": -27505805,
            "current-assets": 53570724, "non-current-assets": 47308630,
            "total-assets": 100879354, "current-liabilities": 86183506,
            "non-current-liabilities": 2299547, "total-liabilities": 88483053,
            "cash": 6973325, "total-equity": 12396301,
            "total-debt": 49066572, "enterprise-value": 54489548,
        },
        2024: {
            "revenue": 175271931, "expenditure": 75018470, "cost-of-sales": 85430709,
            "gross-profit": 89841222, "ebitda": 14822752, "ebitda-margin": 0.0846,
            "net-profit": -649655, "capex": 6738927,
            "net-profit-margin": -0.0037, "net-profit-before-tax": 1114783,
            "current-assets": 60058998, "non-current-assets": 47075237,
            "total-assets": 107134235, "current-liabilities": 89663063,
            "non-current-liabilities": 4595733, "total-liabilities": 35159686,
            "cash": 5722783, "total-equity": 12875439,
            "total-debt": 32451634, "enterprise-value": 39604290,
        },
    },
}

TOWER_DATA = {
    "category": "tower-infrastructure",
    "company":  "african-towers",
    "years": {
        2022: {
            "revenue": 1263611000, "expenditure": 363501000, "cost-of-sales": 446950000,
            "gross-profit": 816661000, "ebitda": 883228000, "ebitda-margin": 0.6990,
            "net-profit": 261076000, "capex": 315897000,
            "net-profit-margin": 0.2066, "net-profit-before-tax": 211331000,
            "current-assets": 997098000, "non-current-assets": 2918725000,
            "total-assets": 3915823000, "current-liabilities": 3915823000,
            "non-current-liabilities": 1675435000, "total-liabilities": 5591258000,
            "cash": 161017000, "total-equity": 1376868000,
            "total-debt": 1443886000, "enterprise-value": 2659737000,
        },
        2023: {
            "revenue": 1496900000, "expenditure": 276433000, "cost-of-sales": 530411000,
            "gross-profit": 966489000, "ebitda": 742610000, "ebitda-margin": 0.4961,
            "net-profit": -274277000, "capex": 0,
            "net-profit-margin": -0.1832, "net-profit-before-tax": -336812000,
            "current-assets": 1173119000, "non-current-assets": 2600397000,
            "total-assets": 3773516000, "current-liabilities": 846995000,
            "non-current-liabilities": 1823930000, "total-liabilities": 2670925000,
            "cash": 428979000, "total-equity": 1102591000,
            "total-debt": 1563838000, "enterprise-value": 2237450000,
        },
        2024: {
            "revenue": 1810400000, "expenditure": 283581000, "cost-of-sales": 598673000,
            "gross-profit": 1211727000, "ebitda": 967863000, "ebitda-margin": 0.5346,
            "net-profit": 131238000, "capex": 0,
            "net-profit-margin": 0.0725, "net-profit-before-tax": 325223000,
            "current-assets": 1328546000, "non-current-assets": 2315851000,
            "total-assets": 3644397000, "current-liabilities": 650435000,
            "non-current-liabilities": 1760133000, "total-liabilities": 2410568000,
            "cash": 476006000, "total-equity": 1233829000,
            "total-debt": 1564441000, "enterprise-value": 2322264000,
        },
    },
}

ALL_DATASETS = [BWA_DATA, ICH_DATA, PAY_TV_DATA, TOWER_DATA]


class Command(BaseCommand):
    help = (
        "Seed the embedded dashboard financial data into the database. "
        "Run seed_reference_data first."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        total_rows = 0
        total_fees = 0

        for dataset in ALL_DATASETS:
            cat_slug     = dataset["category"]
            company_slug = dataset["company"]

            try:
                category = DashboardCategory.objects.get(slug=cat_slug)
            except DashboardCategory.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"Category '{cat_slug}' not found — run seed_reference_data first. Skipping."
                ))
                continue

            try:
                company = Company.objects.get(slug=company_slug)
            except Company.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"Company '{company_slug}' not found — run seed_reference_data first. Skipping."
                ))
                continue

            # Build metric lookup for this category
            metrics = {
                m.key: m
                for m in MetricDefinition.objects.filter(category=category, is_active=True)
            }

            # ── Financial values ──────────────────────────────────────────────
            for year, row in dataset.get("years", {}).items():
                period, _ = FinancialPeriod.objects.get_or_create(year=year)
                for metric_key, raw_value in row.items():
                    if raw_value is None:
                        continue  # no data for this metric/year
                    metric = metrics.get(metric_key)
                    if metric is None:
                        self.stdout.write(self.style.WARNING(
                            f"  Metric '{metric_key}' not found for {cat_slug}. Skipping."
                        ))
                        continue
                    FinancialValue.objects.update_or_create(
                        category=category,
                        company=company,
                        period=period,
                        metric=metric,
                        defaults={"value": Decimal(str(raw_value))},
                    )
                    total_rows += 1

            # ── Regulatory fee values (ICH payments) ──────────────────────────
            for year, fee in dataset.get("payments", {}).items():
                period, _ = FinancialPeriod.objects.get_or_create(year=year)
                RegulatoryFeeValue.objects.update_or_create(
                    category=category,
                    company=company,
                    period=period,
                    defaults={
                        "invoice_issued":   Decimal(str(fee["invoice_issued"])),
                        "payment_received": Decimal(str(fee["payment_received"])),
                        "outstanding":      Decimal(str(fee["outstanding"])),
                    },
                )
                total_fees += 1

            self.stdout.write(f"  ✓ {cat_slug} / {company_slug}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. {total_rows} financial values and {total_fees} fee rows seeded."
        ))
