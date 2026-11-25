"""Optional AI photo classification assistant. Never raises or blocks report saving."""

import base64
import json
import os

from core.models import Category

SYSTEM = (
    "You classify photos of blocked footpaths. Reply with JSON only, no markdown: "
    '{"is_obstruction": true/false, "category": "<one of the allowed names>", '
    '"severity": 1-3, "confidence": 0-1}'
)


def suggest_from_image(jpeg_bytes: bytes) -> dict | None:
    """Return AI classification dict for jpeg_bytes, or None when disabled/on any error."""
    if os.getenv("AI_ENABLED", "False") != "True":
        return None
    if not jpeg_bytes:
        return None
    try:
        import anthropic

        names = list(Category.objects.values_list("name", flat=True))
        if not names:
            return None

        client = anthropic.Anthropic(timeout=10.0)  # reads ANTHROPIC_API_KEY
        msg = client.messages.create(
            model=os.getenv("AI_MODEL", "claude-haiku-5-5"),
            max_tokens=200,
            system=SYSTEM + " Allowed categories: " + ", ".join(names),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64.b64encode(jpeg_bytes).decode(),
                            },
                        },
                        {"type": "text", "text": "Classify this image."},
                    ],
                }
            ],
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        if data.get("category") not in names:
            return None
        return data
    except Exception:
        return None
