from django import forms

from dashboards.models import DashboardCategory

from .validation import MAX_UPLOAD_BYTES, ALLOWED_EXTENSIONS, ValidationError, validate_upload


class WorkbookUploadForm(forms.Form):
    category = forms.ModelChoiceField(queryset=DashboardCategory.objects.filter(is_active=True))
    workbook_file = forms.FileField()

    def clean_workbook_file(self):
        upload = self.cleaned_data["workbook_file"]
        content = b"".join(upload.chunks())
        try:
            validated = validate_upload(upload.name, content)
        except ValidationError as exc:
            raise forms.ValidationError(str(exc)) from exc
        # Stash the validated result so the view doesn't need to re-read the file.
        self._validated_upload = validated
        # Seek back so Django's FileField storage can still read it.
        upload.seek(0)
        return upload

    @property
    def validated_upload(self):
        return getattr(self, "_validated_upload", None)
