from django.core.management.base import BaseCommand

from dashboards.models import Company, DashboardCategory, MetricDefinition


CATEGORIES = [
    ("mobile-network", "Mobile Network"),
    ("bwa", "BWA"),
    ("ich", "ICH"),
    ("pay-television", "Pay Television"),
    ("terrestrial-fibre", "Terrestrial Fibre"),
    ("tower-infrastructure", "Tower Infrastructure"),
]

COMPANIES = [
    ("mtn", "MTN"),
    ("telecel", "Telecel"),
    ("at", "AT"),
    ("telesol", "Telesol"),
    ("dstv", "DSTV"),
    ("afriwave", "AFRIWAVE"),
    ("spectrum-fibre", "Spectrum Fibre"),
    ("african-towers", "African Towers"),
]

BWA_METRICS = [
    ("revenue", "Revenue", "money", ["REVENUE"]),
    ("expenditure", "Expenditure", "money", ["EXPENDITURE"]),
    ("cost-of-sales", "Cost of Sales", "money", ["COST OF SALES"]),
    ("gross-profit", "Gross Profit", "money", ["GROSS PROFIT"]),
    ("ebitda", "EBITDA", "money", ["EBITDA"]),
    ("ebitda-margin", "EBITDA Margin", "percent", ["EBITDA MARGIN"]),
    ("net-profit", "Net Profit", "money", ["NET PROFIT"]),
    ("capex", "CAPEX", "money", ["CAPEX"]),
    ("net-profit-margin", "Net Profit Margin", "percent", ["NET PROFIT MARGIN"]),
    ("net-profit-before-tax", "Net Profit Before Tax", "money", ["NET PROFIT BEFORE TAX"]),
    ("current-assets", "Current Assets", "money", ["CURRENT ASSETS"]),
    ("non-current-assets", "Non-current Assets", "money", ["NON-CURRENT ASSETS", "NON CURRENT ASSETS"]),
    ("total-assets", "Total Assets", "money", ["TOTAL ASSETS"]),
    ("current-liabilities", "Current Liabilities", "money", ["CURRENT LIABILITIES"]),
    (
        "non-current-liabilities",
        "Non-current Liabilities",
        "money",
        ["NON-CURRENT LIABILITIES", "NON CURRENT LIABILITIES"],
    ),
    ("total-liabilities", "Total Liabilities", "money", ["TOTAL LIABILITIES"]),
    ("cash", "Cash and Cash Equivalents", "money", ["TOTAL CASH AND CASH EQUIVALENTS", "CASH AND CASH EQUIVALENTS"]),
    ("total-equity", "Total Equity", "money", ["TOTAL EQUITY"]),
    ("total-debt", "Total Debt", "money", ["TOTAL DEBT"]),
    ("enterprise-value", "Total Enterprise Value", "money", ["TOTAL ENTERPRISE VALUE", "ENTERPRISE VALUE"]),
]


class Command(BaseCommand):
    help = "Seed dashboard categories, companies, and first-pass metric definitions."

    def handle(self, *args, **options):
        categories = {}
        for slug, name in CATEGORIES:
            category, _ = DashboardCategory.objects.update_or_create(slug=slug, defaults={"name": name})
            categories[slug] = category

        for slug, name in COMPANIES:
            Company.objects.update_or_create(slug=slug, defaults={"name": name})

        bwa = categories["bwa"]
        for key, label, unit_type, aliases in BWA_METRICS:
            MetricDefinition.objects.update_or_create(
                category=bwa,
                key=key,
                defaults={"label": label, "unit_type": unit_type, "aliases": aliases},
            )

        # Seed the same financial metrics for all remaining categories
        for cat_slug in ["mobile-network", "ich", "pay-television", "tower-infrastructure", "terrestrial-fibre"]:
            cat = categories[cat_slug]
            for key, label, unit_type, aliases in BWA_METRICS:
                MetricDefinition.objects.update_or_create(
                    category=cat,
                    key=key,
                    defaults={"label": label, "unit_type": unit_type, "aliases": aliases},
                )

        self.stdout.write(self.style.SUCCESS("Reference data seeded."))
