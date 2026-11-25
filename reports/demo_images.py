# -*- coding: utf-8 -*-
"""Generate realistic demo photos for PaveWatch obstruction reports.

Creates clearly identifiable images with textures, borders, hazard stripes,
category badges, and 'BEFORE' / 'AFTER' stamps so they look like actual
footpath obstruction photos instead of solid rectangles.
"""

import io
import os
import random
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.conf import settings

def create_demo_photo(category_name: str, kind: str = "BEFORE", index: int = 1) -> ContentFile:
    """Create a detailed, visually authentic obstruction demo photo."""
    width, height = 800, 600
    
    # Palette per category
    theme_colors = {
        "Illegal Parking": {"bg": (70, 75, 80), "accent": (230, 80, 50), "detail": (140, 145, 150)},
        "Garbage Dumping": {"bg": (65, 75, 60), "accent": (160, 190, 70), "detail": (90, 110, 80)},
        "Vendor Encroachment": {"bg": (85, 70, 60), "accent": (240, 160, 40), "detail": (160, 130, 100)},
        "Construction Debris": {"bg": (90, 85, 75), "accent": (220, 140, 30), "detail": (130, 120, 110)},
        "Broken Pavement": {"bg": (60, 65, 70), "accent": (200, 60, 60), "detail": (110, 115, 120)},
        "Others": {"bg": (55, 60, 75), "accent": (80, 140, 220), "detail": (100, 110, 130)},
    }
    
    t = theme_colors.get(category_name, theme_colors["Others"])
    
    # Background - sidewalk texture pattern
    img = Image.new("RGB", (width, height), color=t["bg"])
    draw = ImageDraw.Draw(img)
    
    # Draw pavement slab grid lines
    slab_size = 80
    for x in range(0, width, slab_size):
        draw.line([(x, 0), (x, height)], fill=t["detail"], width=2)
    for y in range(0, height, slab_size):
        draw.line([(0, y), (width, y)], fill=t["detail"], width=2)
        
    # Draw footpath curb at bottom
    draw.rectangle([0, height - 90, width, height], fill=(45, 50, 55))
    # Curb stripes (black/yellow hazard or white/black)
    stripe_w = 60
    for i, x in enumerate(range(0, width, stripe_w)):
        col = (240, 200, 40) if i % 2 == 0 else (30, 30, 30)
        draw.polygon([(x, height - 90), (x + 30, height - 90), (x + 10, height), (x - 20, height)], fill=col)
        
    # Central obstruction representation box
    box_x0, box_y0 = 160, 120
    box_x1, box_y1 = width - 160, height - 150
    draw.rectangle([box_x0, box_y0, box_x1, box_y1], fill=(20, 25, 30, 200), outline=t["accent"], width=3)
    
    # Draw category badge in the obstruction area
    draw.rectangle([box_x0 + 20, box_y0 + 20, box_x1 - 20, box_y0 + 90], fill=t["accent"])
    
    # If kind is AFTER, show clean resolved footpath badge
    if kind == "AFTER":
        draw.rectangle([box_x0 + 20, box_y0 + 110, box_x1 - 20, box_y1 - 20], fill=(30, 120, 60))
        # Resolved text
        draw.text((box_x0 + 40, box_y0 + 130), "[ RESOLVED / CLEARED ]", fill=(255, 255, 255))
        draw.text((box_x0 + 40, box_y0 + 170), "Footpath restored and accessible.", fill=(220, 240, 220))
        draw.text((box_x0 + 40, box_y0 + 200), f"Ward Officer Resolution Record #{index}", fill=(180, 220, 180))
    else:
        draw.rectangle([box_x0 + 20, box_y0 + 110, box_x1 - 20, box_y1 - 20], fill=(40, 45, 50))
        draw.text((box_x0 + 40, box_y0 + 130), f"[ OBSTRUCTION REPORTED ]", fill=(255, 255, 255))
        draw.text((box_x0 + 40, box_y0 + 170), f"Category: {category_name}", fill=(255, 220, 100))
        draw.text((box_x0 + 40, box_y0 + 200), f"Bengaluru Walkability Audit #{index}", fill=(200, 200, 200))
    
    # Header Category title
    draw.text((box_x0 + 35, box_y0 + 40), f"PAVEWATCH: {category_name.upper()}", fill=(255, 255, 255))
    
    # Top-right watermark stamp
    stamp_color = (40, 167, 69) if kind == "AFTER" else (220, 53, 69)
    draw.rectangle([width - 160, 20, width - 20, 65], fill=stamp_color)
    draw.text((width - 145, 32), f"{kind} PHOTO", fill=(255, 255, 255))
    
    # Bottom GPS stamp simulation
    draw.rectangle([20, height - 40, 360, height - 15], fill=(0, 0, 0, 180))
    draw.text((25, height - 35), f"GPS: 12.9716 N, 77.5946 E | Bengaluru BBMP", fill=(200, 200, 200))
    
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    return ContentFile(buffer.getvalue(), name=f"{category_name.lower().replace(' ', '_')}_{kind.lower()}_{index}.jpg")
