import io
import uuid
from datetime import datetime
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

ALLOWED = {"JPEG", "PNG", "WEBP"}

def _dms(v, ref):
    d = float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
    return -d if ref in ("S", "W") else d

def read_exif(img):
    """Return (lat, lon, taken_datetime) or Nones. Never raises."""
    try:
        exif = img.getexif()
        gps = exif.get_ifd(0x8825)
        lat = lon = None
        if gps and 2 in gps and 4 in gps:
            lat = _dms(gps[2], gps.get(1, "N"))
            lon = _dms(gps[4], gps.get(3, "E"))
        raw = exif.get_ifd(0x8769).get(36867) or exif.get(306)
        taken = datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S") if raw else None
        return lat, lon, taken
    except Exception:
        return None, None, None

def process_upload(uploaded, max_mb=5):
    """Validate an uploaded image. Return (ContentFile jpeg, exif_tuple). Raises ValidationError."""
    if uploaded.size > max_mb * 1024 * 1024:
        raise ValidationError(f"Image must be under {max_mb} MB.")
    try:
        img = Image.open(uploaded)
        img.verify()
        uploaded.seek(0)
        img = Image.open(uploaded)
    except Exception:
        raise ValidationError("Unsupported or corrupt image. Use JPG, PNG or WebP (not HEIC).")
    if img.format not in ALLOWED:
        raise ValidationError("Only JPG, PNG or WebP images are allowed.")
    exif = read_exif(img)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)  # re-encoding strips EXIF
    return ContentFile(buf.getvalue(), name=f"{uuid.uuid4().hex}.jpg"), exif
