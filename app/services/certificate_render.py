"""Render a certificate PDF from an admin-supplied template.

The template is a background image plus a list of positioned text fields.
Rendering stamps the fields onto the background and saves a PDF, so the
design lives entirely in the admin panel: changing the artwork or moving the
recipient's name needs no code change and no deploy.

Long names are shrunk to fit their declared box rather than overflowing the
artwork, because a certificate that renders wrong is worse than one that
renders a little smaller.
"""

from __future__ import annotations

import io
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

from app.schemas.certificate import TemplateField

logger = logging.getLogger("uvicorn.error")

# Fonts are looked up in order; the first that exists wins. Pillow's default
# bitmap font ignores size, so a real TrueType face matters here.
FONT_CANDIDATES = {
    "bold": [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
    "regular": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
}


class CertificateRenderError(RuntimeError):
    """The certificate could not be produced."""


def _load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES.get(weight, FONT_CANDIDATES["regular"]):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    # Last resort. Sizing will be wrong, but a certificate still renders.
    logger.warning("No TrueType font found for weight %s; falling back to the bitmap font.", weight)
    return ImageFont.load_default()


def _fit_font(
    draw: ImageDraw.ImageDraw, text: str, weight: str, size: int, max_width: Optional[int]
) -> ImageFont.FreeTypeFont:
    font = _load_font(weight, size)
    if not max_width:
        return font
    current = size
    while current > 8:
        width = draw.textlength(text, font=font)
        if width <= max_width:
            return font
        current -= 2
        font = _load_font(weight, current)
    return font


def generate_certificate_number() -> str:
    """A number that is quotable aloud and not guessable in bulk.

    Shape: TA-<year>-<10 random base32 characters>. The random part is wide
    enough that the verification endpoint cannot be walked by enumeration.
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no look-alike characters
    body = "".join(secrets.choice(alphabet) for _ in range(10))
    return f"TA-{datetime.now(timezone.utc).year}-{body}"


def render_certificate(
    *,
    background: bytes,
    width: int,
    height: int,
    fields: List[TemplateField],
    values: Dict[str, str],
) -> bytes:
    """Stamp `values` onto the template and return the PDF bytes.

    Bytes in, bytes out: where the background came from and where the PDF
    goes are the storage layer's business, which is what lets the same
    renderer work on Render's ephemeral disk and on a local checkout.
    """
    try:
        canvas = Image.open(io.BytesIO(background)).convert("RGB")
    except OSError as exc:
        raise CertificateRenderError(f"Template background could not be opened: {exc}") from exc

    if canvas.size != (width, height):
        canvas = canvas.resize((width, height), Image.LANCZOS)

    draw = ImageDraw.Draw(canvas)

    for field in fields:
        text = field.text if field.key == "custom" else values.get(field.key)
        if not text:
            continue

        font = _fit_font(draw, text, field.font_weight, field.font_size, field.max_width)
        anchor = {"left": "la", "center": "ma", "right": "ra"}.get(field.align, "ma")
        draw.text((field.x, field.y), text, font=font, fill=field.color, anchor=anchor)

    buffer = io.BytesIO()
    try:
        canvas.save(buffer, "PDF", resolution=150.0)
    except OSError as exc:
        raise CertificateRenderError(f"Certificate PDF could not be rendered: {exc}") from exc

    return buffer.getvalue()
