from django import forms
from .models import Report, ReportPhoto
from django.forms import ClearableFileInput

# Custom widget to allow multiple file selection
class MultiFileInput(ClearableFileInput):
    allow_multiple_selected = True


class ReportForm(forms.ModelForm):
    """Form for creating a new report.

    Fields:
        - category
        - description
        - landmark (optional)
        - location (latitude & longitude as a string "lat,lon")
        - severity (choice)
        - photos (multiple optional images)
    """

    photos = forms.FileField(
        widget=MultiFileInput(attrs={"multiple": True}),
        required=False,
        label="Photos",
        help_text="Upload one or more photos (optional).",
    )

    location = forms.CharField(
        max_length=100,
        required=True,
        label="Location",
        help_text="Enter latitude and longitude as 'lat,lon'.",
    )

    class Meta:
        model = Report
        fields = ["category", "description", "landmark", "location", "severity"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_location(self):
        """Validate and split latitude/longitude.

        Returns a tuple (lat, lon) as floats.
        """
        value = self.cleaned_data["location"].strip()
        try:
            lat_str, lon_str = value.split(",")
            lat = float(lat_str)
            lon = float(lon_str)
        except Exception:
            raise forms.ValidationError(
                "Enter location as 'latitude,longitude' with numeric values."
            )
        # Optionally enforce bounds (India lat/long range as example)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise forms.ValidationError("Latitude must be between -90 and 90 and longitude between -180 and 180.")
        return (lat, lon)
