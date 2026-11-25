# -*- coding: utf-8 -*-
"""Generate realistic, high-contrast demo photos for PaveWatch obstruction reports."""

import io
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile


def _get_font(size: int):
    for candidate in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def create_demo_photo(category_name: str, kind: str = "BEFORE", index: int = 1) -> ContentFile:
    """Create a crisp, readable footpath scene illustration for demo reports."""
    width, height = 800, 600
    img = Image.new("RGB", (width, height), color=(226, 232, 240))
    draw = ImageDraw.Draw(img)

    # Sky & distant urban silhouette
    draw.rectangle([0, 0, width, 210], fill=(191, 219, 254))
    buildings = [(30, 95, 140, 210), (155, 65, 275, 210), (295, 110, 410, 210),
                 (430, 75, 560, 210), (580, 100, 700, 210), (715, 80, 785, 210)]
    for b in buildings:
        draw.rectangle(b, fill=(148, 163, 184))

    # Footpath surface (warm concrete) & perspective slab lines
    draw.rectangle([0, 210, width, 475], fill=(203, 213, 225))
    for x_top, x_bot in [(120, -40), (280, 180), (400, 400), (520, 620), (680, 840)]:
        draw.line([(x_top, 210), (x_bot, 475)], fill=(148, 163, 184), width=2)
    for y in (260, 320, 395):
        draw.line([(0, y), (width, y)], fill=(148, 163, 184), width=2)

    # Tactile paving strip along footpath
    draw.rectangle([0, 415, width, 445], fill=(250, 204, 21))
    for x in range(15, width, 30):
        draw.ellipse([x, 424, x + 10, 434], fill=(202, 138, 4))

    # Curb & road at bottom
    draw.rectangle([0, 475, width, 505], fill=(51, 65, 85))
    for i, x in enumerate(range(0, width, 60)):
        col = (250, 204, 21) if i % 2 == 0 else (30, 41, 59)
        draw.polygon([(x, 475), (x + 35, 475), (x + 20, 505), (x - 15, 505)], fill=col)
    draw.rectangle([0, 505, width, height], fill=(30, 41, 59))

    # Scene illustration: cleared footpath for AFTER, category obstruction for BEFORE
    if kind == "AFTER":
        draw.rounded_rectangle([180, 235, 620, 395], radius=16, fill=(22, 163, 74), outline=(255, 255, 255), width=4)
        draw.text((235, 275), "FOOTPATH CLEARED", fill=(255, 255, 255), font=_get_font(30))
        draw.text((235, 325), f"Resolved: {category_name}", fill=(220, 252, 231), font=_get_font(20))
    else:
        if category_name == "Illegal Parking":
            # Car silhouette blocking footpath
            draw.rounded_rectangle([220, 275, 580, 380], radius=18, fill=(220, 38, 38))
            draw.polygon([(270, 275), (320, 220), (490, 220), (540, 275)], fill=(185, 28, 28))
            draw.polygon([(330, 230), (480, 230), (515, 270), (295, 270)], fill=(186, 230, 253))
            draw.ellipse([260, 355, 325, 415], fill=(15, 23, 42))
            draw.ellipse([475, 355, 540, 415], fill=(15, 23, 42))
        elif category_name == "Broken Pavement":
            # Broken/sunken concrete slabs & hazard cone
            draw.polygon([(210, 320), (390, 290), (440, 385), (190, 405)], fill=(100, 116, 139), outline=(51, 65, 85), width=3)
            draw.line([(260, 315), (350, 365), (310, 395)], fill=(15, 23, 42), width=5)
            draw.polygon([(475, 385), (515, 255), (555, 385)], fill=(249, 115, 22))
            draw.rectangle([460, 382, 570, 398], fill=(234, 88, 12))
        elif category_name == "Garbage Dumping":
            # Overflowing waste bags
            for cx, cy, r, c in [(310, 345, 55, (34, 197, 94)), (400, 330, 65, (21, 128, 61)), (490, 355, 50, (71, 85, 105))]:
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c, outline=(15, 23, 42), width=2)
        elif category_name == "Construction Debris":
            # Sand/rubble mound & barricade
            draw.polygon([(220, 395), (370, 260), (530, 395)], fill=(180, 130, 70), outline=(120, 80, 30), width=3)
            draw.rectangle([380, 295, 590, 325], fill=(249, 115, 22))
            draw.rectangle([395, 325, 410, 395], fill=(71, 85, 105))
            draw.rectangle([560, 325, 575, 395], fill=(71, 85, 105))
        elif category_name == "Vendor Encroachment":
            # Canopy stall blocking walkway
            draw.rectangle([240, 260, 560, 300], fill=(234, 88, 12))
            draw.rectangle([265, 300, 278, 395], fill=(71, 85, 105))
            draw.rectangle([522, 300, 535, 395], fill=(71, 85, 105))
            draw.rectangle([265, 335, 535, 395], fill=(180, 83, 9))
        else:
            # Generic hazard barrier
            draw.rounded_rectangle([240, 260, 560, 385], radius=12, fill=(37, 99, 235), outline=(255, 255, 255), width=3)
            draw.text((285, 305), "OBSTRUCTION", fill=(255, 255, 255), font=_get_font(30))

    # Top-left category pill
    font_md = _get_font(20)
    font_sm = _get_font(16)
    draw.rounded_rectangle([20, 20, 360, 62], radius=8, fill=(15, 23, 42))
    draw.text((34, 30), f"{category_name.upper()}", fill=(255, 255, 255), font=font_md)

    # Top-right BEFORE / AFTER stamp
    stamp_color = (22, 163, 74) if kind == "AFTER" else (220, 38, 38)
    draw.rounded_rectangle([width - 185, 20, width - 20, 62], radius=8, fill=stamp_color)
    draw.text((width - 165, 30), f"{kind} PHOTO", fill=(255, 255, 255), font=font_md)

    # Bottom GPS / audit caption
    draw.text((24, 536), f"Report #{index}  |  Bengaluru Footpath Audit  |  12.9716 N, 77.5946 E", fill=(226, 232, 240), font=font_sm)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    return ContentFile(buffer.getvalue(), name=f"{category_name.lower().replace(' ', '_')}_{kind.lower()}_{index}.jpg")
