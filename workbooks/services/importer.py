import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.db import transaction

from dashboards.models import Company, FinancialPeriod, FinancialValue, ImportChange, MetricDefinition


PARSER_VERSION = "bwa-v1"


@dataclass
class ImportResult:
    row_count: int
    change_count: int
    warning_count: int = 0


def normalize_label(value):
    return " ".join(str(value or "").upper().replace("-", " ").split())


def parse_decimal(value, unit_type):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        parsed = value
    else:
        text = str(value).strip().replace(",", "").replace("GHS", "").replace("%", "")
        if text in {"", "-", "N/A"}:
            return None
        try:
            parsed = Decimal(text)
        except InvalidOperation:
            return None

    if unit_type == MetricDefinition.UnitType.PERCENT and abs(parsed) > 1:
        parsed = parsed / Decimal("100")
    return parsed


def workbook_sha256(file_field):
    hasher = hashlib.sha256()
    with file_field.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def import_workbook(import_record):
    if import_record.category.slug != "bwa":
        raise NotImplementedError("Only BWA workbook imports are implemented in this first backend slice.")

    import_record.file_sha256 = workbook_sha256(import_record.workbook_file)
    import_record.parser_version = PARSER_VERSION
    import_record.save(update_fields=["file_sha256", "parser_version", "updated_at"])
    import_record.mark_processing()

    try:
        rows = parse_bwa_workbook(import_record)
        result = persist_financial_rows(import_record, rows)
    except Exception as exc:
        import_record.mark_failed(exc)
        raise

    import_record.mark_completed(row_count=result.row_count, warning_count=result.warning_count)
    return result


def parse_bwa_workbook(import_record):
    from openpyxl import load_workbook

    metrics = list(MetricDefinition.objects.filter(category=import_record.category, is_active=True))
    if not metrics:
        raise ValueError("No metric definitions exist for this dashboard category. Run seed_reference_data.")

    with import_record.workbook_file.open("rb") as handle:
        workbook = load_workbook(handle, data_only=True, read_only=True)
        parsed_rows = []
        for sheet_name in workbook.sheetnames:
            if not str(sheet_name).isdigit() or len(str(sheet_name)) != 4:
                continue
            year = int(sheet_name)
            sheet = workbook[sheet_name]
            sheet_rows = [list(row) for row in sheet.iter_rows(values_only=True)]
            for metric in metrics:
                value = find_metric_value(sheet_rows, metric)
                if value is not None:
                    parsed_rows.append(
                        {
                            "year": year,
                            "company_slug": "telesol",
                            "metric": metric,
                            "value": value,
                        }
                    )
        if not parsed_rows:
            raise ValueError("No values were parsed. Check that sheets are named by year and metric labels match.")
        return parsed_rows


def find_metric_value(sheet_rows, metric):
    aliases = [normalize_label(metric.label)] + [normalize_label(alias) for alias in metric.aliases]
    for row in sheet_rows:
        normalized_cells = [normalize_label(cell) for cell in row]
        for index, label in enumerate(normalized_cells):
            if label in aliases:
                for candidate in row[index + 1 :]:
                    value = parse_decimal(candidate, metric.unit_type)
                    if value is not None:
                        return value
    return None


@transaction.atomic
def persist_financial_rows(import_record, rows):
    company_cache = {company.slug: company for company in Company.objects.all()}
    change_count = 0

    for row in rows:
        period, _ = FinancialPeriod.objects.get_or_create(year=row["year"])
        company = company_cache.get(row["company_slug"])
        if company is None:
            raise ValueError(f"Unknown company slug: {row['company_slug']}")

        existing = FinancialValue.objects.filter(
            category=import_record.category,
            company=company,
            period=period,
            metric=row["metric"],
        ).first()

        old_value = existing.value if existing else None
        value_changed = old_value != row["value"]

        financial_value, _ = FinancialValue.objects.update_or_create(
            category=import_record.category,
            company=company,
            period=period,
            metric=row["metric"],
            defaults={"value": row["value"], "source_import": import_record},
        )

        if value_changed:
            ImportChange.objects.create(
                import_record=import_record,
                category=import_record.category,
                company=company,
                period=period,
                metric=row["metric"],
                old_value=old_value,
                new_value=financial_value.value,
            )
            change_count += 1

    return ImportResult(row_count=len(rows), change_count=change_count)
