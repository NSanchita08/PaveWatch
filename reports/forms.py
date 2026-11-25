from django import forms
from django.conf import settings


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    """FileField that accepts multiple uploaded files from MultiFileInput."""

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data if d]
        return [single_file_clean(data, initial)] if data else []


class ReportForm(forms.Form):
    """Form for submitting a new obstruction report."""

    category = forms.ModelChoiceField(
        queryset=None,  # set in __init__
        label="Category",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    description = forms.CharField(
        required=False,
        label="Description",
        widget=forms.Textarea(attrs={
            "rows": 3,
            "class": "form-control",
            "placeholder": "Describe the obstruction…",
        }),
    )
    landmark = forms.CharField(
        required=False,
        max_length=200,
        label="Nearby Landmark",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Near City Bus Stop",
        }),
    )
    severity = forms.ChoiceField(
        choices=[(1, "Low (1)"), (2, "Medium (2)"), (3, "High (3)")],
        initial=2,
        label="Severity",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # Accessibility checkboxes
    affects_wheelchair = forms.BooleanField(required=False, label="Wheelchair users")
    affects_visually_impaired = forms.BooleanField(required=False, label="Visually impaired")
    affects_elderly = forms.BooleanField(required=False, label="Elderly")
    affects_children = forms.BooleanField(required=False, label="Children")

    # Hidden lat/lon filled by the Leaflet map JS
    lat = forms.FloatField(
        widget=forms.HiddenInput(),
        error_messages={"required": "Please drop a pin on the map to select a location."},
    )
    lon = forms.FloatField(
        widget=forms.HiddenInput(),
        error_messages={"required": "Please drop a pin on the map to select a location."},
    )
    ai_label = forms.CharField(required=False, max_length=80, widget=forms.HiddenInput())
    ai_confidence = forms.FloatField(required=False, widget=forms.HiddenInput())

    photos = MultiFileField(
        widget=MultiFileInput(attrs={
            "multiple": True,
            "accept": "image/jpeg,image/png,image/webp",
            "class": "form-control",
        }),
        required=False,
        label="Photos (up to 3, JPG/PNG/WebP, max 5 MB each)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import Category
        self.fields["category"].queryset = Category.objects.all()

    def clean_severity(self):
        return int(self.cleaned_data["severity"])

    def clean(self):
        cleaned = super().clean()
        lat = cleaned.get("lat")
        lon = cleaned.get("lon")
        if lat is not None and lon is not None:
            bounds = getattr(settings, "BLR_BOUNDS", {})
            lat_min = bounds.get("lat_min", -90)
            lat_max = bounds.get("lat_max", 90)
            lon_min = bounds.get("lon_min", -180)
            lon_max = bounds.get("lon_max", 180)
            if not (lat_min <= lat <= lat_max):
                self.add_error("lat", "Pin must be within Bengaluru city limits (latitude out of range).")
            if not (lon_min <= lon <= lon_max):
                self.add_error("lon", "Pin must be within Bengaluru city limits (longitude out of range).")
        return cleaned
