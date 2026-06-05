import io
from decimal import Decimal
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from openpyxl import Workbook

from dashboards.models import (
    Company,
    DashboardCategory,
    FinancialPeriod,
    FinancialValue,
    ImportChange,
    MetricDefinition,
    RegulatoryFeeValue,
    WorkbookImport,
)
from workbooks.services.importer import import_workbook, normalize_label, parse_decimal
from workbooks.forms import WorkbookUploadForm


class WorkbookImporterUtilityTests(SimpleTestCase):
    def test_normalize_label_collapses_case_and_hyphens(self):
        self.assertEqual(normalize_label("Non-current  Assets"), "NON CURRENT ASSETS")

    def test_parse_decimal_money_removes_grouping(self):
        self.assertEqual(parse_decimal("1,234.50", MetricDefinition.UnitType.MONEY), Decimal("1234.50"))

    def test_parse_decimal_percent_normalizes_whole_percent(self):
        self.assertEqual(parse_decimal("12.5%", MetricDefinition.UnitType.PERCENT), Decimal("0.125"))


class SecurityHeadersMiddlewareTests(TestCase):
    def test_security_headers_present_on_index(self):
        response = self.client.get(reverse("two_factor:login"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("Referrer-Policy"), "same-origin")
        self.assertEqual(response.headers.get("Cross-Origin-Opener-Policy"), "same-origin")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])


class TwoFactorAuthenticationTests(TestCase):
    def test_unauthenticated_user_redirects_to_login(self):
        response = self.client.get(reverse("dashboard-index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("two_factor:login"), response.url)

    def test_admin_login_redirects_or_requires_otp(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url.lower())


class DatabaseConstraintsTests(TestCase):
    def setUp(self):
        self.category = DashboardCategory.objects.create(slug="bwa", name="BWA")
        self.company = Company.objects.create(slug="mtn", name="MTN")
        self.period = FinancialPeriod.objects.create(year=2024)

    def test_unique_metric_key_per_category(self):
        MetricDefinition.objects.create(
            category=self.category,
            key="revenue",
            label="Revenue",
            unit_type=MetricDefinition.UnitType.MONEY,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MetricDefinition.objects.create(
                    category=self.category,
                    key="revenue",
                    label="Another Revenue",
                    unit_type=MetricDefinition.UnitType.MONEY,
                )

    def test_unique_financial_value(self):
        metric = MetricDefinition.objects.create(
            category=self.category,
            key="revenue",
            label="Revenue",
            unit_type=MetricDefinition.UnitType.MONEY,
        )
        FinancialValue.objects.create(
            category=self.category,
            company=self.company,
            period=self.period,
            metric=metric,
            value=Decimal("100.00"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FinancialValue.objects.create(
                    category=self.category,
                    company=self.company,
                    period=self.period,
                    metric=metric,
                    value=Decimal("200.00"),
                )

    def test_unique_regulatory_fee_value(self):
        RegulatoryFeeValue.objects.create(
            category=self.category,
            company=self.company,
            period=self.period,
            invoice_issued=Decimal("50.00"),
            payment_received=Decimal("40.00"),
            outstanding=Decimal("10.00"),
            fee_to_revenue=Decimal("0.05"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RegulatoryFeeValue.objects.create(
                    category=self.category,
                    company=self.company,
                    period=self.period,
                    invoice_issued=Decimal("100.00"),
                    payment_received=Decimal("90.00"),
                    outstanding=Decimal("10.00"),
                    fee_to_revenue=Decimal("0.05"),
                )


class WorkbookUploadFormTests(TestCase):
    def setUp(self):
        self.category = DashboardCategory.objects.create(slug="bwa", name="BWA")

    def test_form_validates_xlsx_file(self):
        file = SimpleUploadedFile("test.xlsx", b"dummy_content", content_type="application/vnd.ms-excel")
        form = WorkbookUploadForm(
            data={"category": self.category.id},
            files={"workbook_file": file}
        )
        self.assertTrue(form.is_valid())

    def test_form_rejects_invalid_extension(self):
        # Reject non-xlsx
        for name in ["test.xls", "test.csv", "test.txt", "test.exe"]:
            file = SimpleUploadedFile(name, b"dummy_content")
            form = WorkbookUploadForm(
                data={"category": self.category.id},
                files={"workbook_file": file}
            )
            self.assertFalse(form.is_valid())
            self.assertIn("workbook_file", form.errors)
            self.assertIn("Upload an .xlsx workbook.", form.errors["workbook_file"][0])

    def test_form_rejects_too_large_file(self):
        # Size limit is 20MB. Mock a file with 21MB size.
        large_content = b"a" * (20 * 1024 * 1024 + 1)
        file = SimpleUploadedFile("test.xlsx", large_content)
        form = WorkbookUploadForm(
            data={"category": self.category.id},
            files={"workbook_file": file}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("workbook_file", form.errors)
        self.assertIn("Workbook uploads are limited to 20 MB.", form.errors["workbook_file"][0])


class AdminUploadViewPermissionTests(TestCase):
    def setUp(self):
        self.category = DashboardCategory.objects.create(slug="bwa", name="BWA")
        self.anonymous_client = self.client
        
        # Regular user (no staff privileges)
        self.regular_user = User.objects.create_user(username="regular", password="password123")
        
        # Staff user
        self.staff_user = User.objects.create_user(username="staff", password="password123", is_staff=True)

    def test_anonymous_user_cannot_access_upload_view(self):
        # Request upload page
        response = self.anonymous_client.get("/admin/dashboards/workbookimport/upload-workbook/")
        # Redirect to login
        self.assertEqual(response.status_code, 302)

    def test_regular_user_cannot_access_upload_view(self):
        self.client.force_login(self.regular_user)
        response = self.client.get("/admin/dashboards/workbookimport/upload-workbook/")
        # Redirected (to admin login since regular user has no admin rights)
        self.assertEqual(response.status_code, 302)


class WorkbookImporterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="password123")
        self.category_bwa = DashboardCategory.objects.create(slug="bwa", name="BWA")
        self.category_ich = DashboardCategory.objects.create(slug="ich", name="ICH")
        self.category_mobile = DashboardCategory.objects.create(slug="mobile-network", name="Mobile Network")
        
        self.company_telesol = Company.objects.create(slug="telesol", name="Telesol")
        self.company_mtn = Company.objects.create(slug="mtn", name="MTN")
        self.company_telecel = Company.objects.create(slug="telecel", name="Telecel")
        self.company_at = Company.objects.create(slug="at", name="AT")

        # BWA Financial Metrics
        self.metric_revenue = MetricDefinition.objects.create(
            category=self.category_bwa,
            key="revenue",
            label="Revenue",
            unit_type=MetricDefinition.UnitType.MONEY,
            aliases=["REVENUE"],
        )
        self.metric_ebitda = MetricDefinition.objects.create(
            category=self.category_bwa,
            key="ebitda",
            label="EBITDA",
            unit_type=MetricDefinition.UnitType.MONEY,
            aliases=["EBITDA"],
        )
        self.metric_ebitda_margin = MetricDefinition.objects.create(
            category=self.category_bwa,
            key="ebitda-margin",
            label="EBITDA Margin",
            unit_type=MetricDefinition.UnitType.PERCENT,
            aliases=["EBITDA MARGIN"],
        )

        # Mobile Network Financial Metrics
        self.mobile_metric_revenue = MetricDefinition.objects.create(
            category=self.category_mobile,
            key="revenue",
            label="Revenue",
            unit_type=MetricDefinition.UnitType.MONEY,
            aliases=["REVENUE"],
        )
        self.mobile_metric_ebitda_margin = MetricDefinition.objects.create(
            category=self.category_mobile,
            key="ebitda-margin",
            label="EBITDA Margin",
            unit_type=MetricDefinition.UnitType.PERCENT,
            aliases=["EBITDA MARGIN"],
        )

    def _create_mock_excel(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "2024"
        ws.append(["REVENUE", "1,234,567.89"])
        ws.append(["EBITDA", "456,789.00"])
        ws.append(["EBITDA Margin", "12.5%"])
        file_stream = io.BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)
        return ContentFile(file_stream.read(), name="test_bwa_2024.xlsx")

    def test_unsupported_category_raises_not_implemented(self):
        import_record = WorkbookImport.objects.create(
            category=self.category_ich,
            uploaded_by=self.user,
            original_filename="test.xlsx",
            workbook_file=self._create_mock_excel(),
        )
        with self.assertRaises(NotImplementedError):
            import_workbook(import_record)

    def test_successful_workbook_import_and_data_persistence(self):
        import_record = WorkbookImport.objects.create(
            category=self.category_bwa,
            uploaded_by=self.user,
            original_filename="test_bwa_2024.xlsx",
            workbook_file=self._create_mock_excel(),
        )

        result = import_workbook(import_record)
        self.assertEqual(result.row_count, 3)
        self.assertEqual(result.change_count, 3)

        period_2024 = FinancialPeriod.objects.get(year=2024)
        val_revenue = FinancialValue.objects.get(
            category=self.category_bwa,
            company=self.company_telesol,
            period=period_2024,
            metric=self.metric_revenue,
        )
        self.assertEqual(val_revenue.value, Decimal("1234567.890000"))

    def test_real_mno_financials_import(self):
        project_dir = settings.BASE_DIR
        file_name = "MNO FINANCIALS TO 2025 working Sheet -edit.xlsx"
        full_path = os.path.join(project_dir, file_name)
        
        self.assertTrue(os.path.exists(full_path), f"Real file {file_name} not found in root.")
        
        with open(full_path, "rb") as f:
            import_record = WorkbookImport.objects.create(
                category=self.category_mobile,
                uploaded_by=self.user,
                original_filename=file_name,
                workbook_file=File(f, name=file_name),
            )
            
            result = import_workbook(import_record)
            self.assertGreater(result.row_count, 0)
            self.assertGreater(result.change_count, 0)
            
            period_2024 = FinancialPeriod.objects.get(year=2024)
            mtn_rev = FinancialValue.objects.get(
                category=self.category_mobile,
                company=self.company_mtn,
                period=period_2024,
                metric=self.mobile_metric_revenue
            )
            self.assertEqual(mtn_rev.value, Decimal("13758565000.000000"))

    def test_real_regulatory_fees_import(self):
        project_dir = settings.BASE_DIR
        file_name = "1% Regulatory Fee- MNOs- V2.xlsx"
        full_path = os.path.join(project_dir, file_name)
        
        self.assertTrue(os.path.exists(full_path), f"Real file {file_name} not found in root.")
        
        with open(full_path, "rb") as f:
            import_record = WorkbookImport.objects.create(
                category=self.category_mobile,
                uploaded_by=self.user,
                original_filename=file_name,
                workbook_file=File(f, name=file_name),
            )
            
            result = import_workbook(import_record)
            self.assertGreater(result.row_count, 0)
            self.assertGreater(result.change_count, 0)
            
            period_2024 = FinancialPeriod.objects.get(year=2024)
            mtn_fee = RegulatoryFeeValue.objects.get(
                category=self.category_mobile,
                company=self.company_mtn,
                period=period_2024
            )
            self.assertAlmostEqual(mtn_fee.payment_received, Decimal("131649797.25"), places=2)

    def test_real_bwa_quarterly_subscriber_import(self):
        project_dir = settings.BASE_DIR
        file_name = "BWA_1st Quarter 2026 - Updated Tables and Figures in Quarterly Statistical Reports 13.03.26.xlsx"
        full_path = os.path.join(project_dir, file_name)
        
        self.assertTrue(os.path.exists(full_path), f"Real file {file_name} not found in root.")
        
        with open(full_path, "rb") as f:
            import_record = WorkbookImport.objects.create(
                category=self.category_bwa,
                uploaded_by=self.user,
                original_filename=file_name,
                workbook_file=File(f, name=file_name),
            )
            
            result = import_workbook(import_record)
            self.assertGreater(result.row_count, 0)
            self.assertGreater(result.change_count, 0)
            
            period_2024 = FinancialPeriod.objects.get(year=2024)
            metric_subs = MetricDefinition.objects.get(
                category=self.category_bwa,
                key="subscribers"
            )
            telesol_subs = FinancialValue.objects.filter(
                category=self.category_bwa,
                company=self.company_telesol,
                period=period_2024,
                metric=metric_subs
            )
            self.assertGreater(telesol_subs.count(), 0)

    def test_import_corrupt_workbook_raises_error(self):
        corrupt_file = SimpleUploadedFile("corrupt.xlsx", b"invalid_binary_excel_content")
        import_record = WorkbookImport.objects.create(
            category=self.category_bwa,
            uploaded_by=self.user,
            original_filename="corrupt.xlsx",
            workbook_file=corrupt_file,
        )
        with self.assertRaises(Exception):
            import_workbook(import_record)
        
        import_record.refresh_from_db()
        self.assertEqual(import_record.status, WorkbookImport.Status.FAILED)
        self.assertTrue(len(import_record.error_summary) > 0)
