from django import forms

from dashboards.models import DashboardCategory


class WorkbookUploadForm(forms.Form):
    category = forms.ModelChoiceField(queryset=DashboardCategory.objects.filter(is_active=True))
    workbook_file = forms.FileField()

    def clean_workbook_file(self):
        upload = self.cleaned_data["workbook_file"]
        allowed_extensions = (".xlsx",)
        if not upload.name.lower().endswith(allowed_extensions):
            raise forms.ValidationError("Upload an .xlsx workbook.")
        if upload.size > 20 * 1024 * 1024:
            raise forms.ValidationError("Workbook uploads are limited to 20 MB.")
        return upload
