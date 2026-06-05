from decimal import Decimal

from django.test import SimpleTestCase

from dashboards.models import MetricDefinition
from workbooks.services.importer import normalize_label, parse_decimal


class WorkbookImporterUtilityTests(SimpleTestCase):
    def test_normalize_label_collapses_case_and_hyphens(self):
        self.assertEqual(normalize_label("Non-current  Assets"), "NON CURRENT ASSETS")

    def test_parse_decimal_money_removes_grouping(self):
        self.assertEqual(parse_decimal("1,234.50", MetricDefinition.UnitType.MONEY), Decimal("1234.50"))

    def test_parse_decimal_percent_normalizes_whole_percent(self):
        self.assertEqual(parse_decimal("12.5%", MetricDefinition.UnitType.PERCENT), Decimal("0.125"))
