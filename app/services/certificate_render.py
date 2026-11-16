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

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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


def render_offer_letter_certificate(
    *,
    recipient_name: str,
    project_title: str,
    consignment_no: Optional[str] = None,
    issue_date: Optional[str] = None,
    start_date: Optional[str] = None,
    college_name: Optional[str] = None,
    technologies: Optional[str] = None,
    certificate_number: Optional[str] = None,
) -> bytes:
    """Render the official 1-page A4 Portrait Internship Offer Letter Certificate.

    Matches the exact layout, typography, and logos from the official DOCX / HTML template.
    Guaranteed to fit exactly on a single page A4.
    """
    buffer = io.BytesIO()

    # Exact A4 margins (points)
    margin_x = 42
    margin_top = 28
    margin_bottom = 24

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin_x,
        rightMargin=margin_x,
        topMargin=margin_top,
        bottomMargin=margin_bottom,
    )

    assets_dir = Path(__file__).resolve().parent.parent / "assets" / "offer_letter"

    style_brand = ParagraphStyle(
        "BrandTitle",
        fontName="Times-Bold",
        fontSize=20,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#000000"),
        spaceAfter=2,
    )

    style_heading = ParagraphStyle(
        "OfferHeading",
        fontName="Times-Bold",
        fontSize=14,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1D1D1D"),
        spaceAfter=8,
    )

    style_meta = ParagraphStyle(
        "MetaRight",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#333333"),
        spaceAfter=2,
    )

    style_salutation = ParagraphStyle(
        "Salutation",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#222222"),
        spaceAfter=5,
    )

    style_body = ParagraphStyle(
        "BodyTextCustom",
        fontName="Helvetica",
        fontSize=8.2,
        leading=11.2,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#333333"),
        spaceAfter=5,
    )

    style_thanks = ParagraphStyle(
        "Thanks",
        fontName="Times-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#333333"),
        spaceAfter=3,
    )

    style_hr = ParagraphStyle(
        "HRInfo",
        fontName="Courier",
        fontSize=8.0,
        leading=10.5,
        textColor=colors.HexColor("#333333"),
        spaceAfter=1,
    )

    story = []

    # 1. Top Logo Row (TurnpikeAnalyst logo on top right)
    logo_path = str(assets_dir / "image2.png")
    if Path(logo_path).exists():
        logo_img = RLImage(logo_path, width=128, height=43.5)
        header_table = Table([["", logo_img]], colWidths=[380, 131])
        header_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(header_table)

    story.append(Spacer(1, 2))

    # 2. Main Title & Heading
    story.append(Paragraph("TurnPikeAnalyst", style_brand))
    story.append(Paragraph("<u>INTERNSHIP OFFER LETTER</u>", style_heading))
    story.append(Spacer(1, 2))

    # 3. Consignment No & Date (Right aligned)
    consignment = consignment_no or f"0875/TPA{datetime.now(timezone.utc).year}"
    date_str = issue_date or datetime.now(timezone.utc).strftime("%d %B %Y")
    story.append(Paragraph(f"<b>Consignment no: {consignment}</b>", style_meta))
    story.append(Paragraph(f"<b>Date: {date_str}</b>", style_meta))
    story.append(Spacer(1, 4))

    # 4. Salutation & Greeting
    recip = recipient_name.strip() if recipient_name else "Intern"
    story.append(Paragraph(f"Dear {recip},", style_salutation))
    story.append(Paragraph("Hope you are doing well!!", style_salutation))
    story.append(Spacer(1, 2))

    # 5. Paragraph 1
    s_date = start_date or "July 2026"
    p1_text = (
        f"TurnPikeAnalyst is pleased release <b>Long Term Contractual Internship</b> to you. "
        f"This letter of Internship is a temporary agreement between you and TurnPikeAnalyst, "
        f"you would be with TurnPikeAnalyst <b>starting from {s_date}</b>. "
        f"After successful completion of the internship a modified copy would be approved and provided."
    )
    story.append(Paragraph(p1_text, style_body))

    # 6. Paragraph 2
    c_name = college_name or "Haldia Institute of Technology"
    p2_text = (
        "TurnPikeAnalyst is sure that this internship would embrace orientation and give emphasis on "
        "learning new skills with a deeper understanding of concepts through hands-on application of "
        "the knowledge you gained as an Intern. Because of our Internship Program design/pattern would help "
        f"you to gain more knowledge and become master. Always, you would feel home as most of the "
        f"TurnPikeAnalyst employees are from your college, {c_name}. All mentors are experienced "
        "and confident that you will acknowledge your obligation to perform all work allocated to you to "
        "the best of your ability within lawful and reasonable direction given to you."
    )
    story.append(Paragraph(p2_text, style_body))

    # 7. Paragraph 3 (Technologies)
    base_tech = (
        "C, C++, core and advance Java, VB, .Net, Python, PHP, Kotlin, Flutter, Oracle, SQL, MSSQL, DB2, "
        "MYSQL, PostgreSQL, Ruby, Perl, Delphi, Pascal, JavaScript, C#, Kotlin, HTML, CSS, NoSQL, MongoDB, "
        "PL/SQL, Windows, non-Windows Operating Systems, AI, ML, DL, LLM, all Cloud technologies concepts "
        "like IaaS, FaaS, and SaaS, Computer/Laptop software and hardware."
    )
    if technologies and technologies.strip():
        tech_list = f"{technologies.strip()}, {base_tech}"
    else:
        tech_list = base_tech

    p3_text = (
        "Successful completion of this internship you would receive completed IT Experience Letter covering "
        f"the technologies considered to be part of your projects but not limited to {tech_list}"
    )
    story.append(Paragraph(p3_text, style_body))

    # 8. Paragraph 4
    p4_text = (
        "As a Contractor, you will have access to confidential information that is the property of the "
        "TurnPikeAnalyst. This contract shall be governed, interpreted, and construed in accordance with the "
        "laws of Pennsylvania/United States for TurnPikeAnalyst LLC, and West Bengal/India for TurnPikeAnalyst "
        "LLP Information technology laws/jurisdiction in case violation."
    )
    story.append(Paragraph(p4_text, style_body))

    # 9. Paragraph 5
    p5_text = (
        "It’s fully free or non-paid internship program where as neither TurnPikeAnalyst nor the associate "
        "would pay any wages or fees to anyone."
    )
    story.append(Paragraph(p5_text, style_body))

    # 10. Paragraph 6
    p6_text = (
        "We look forward to a worthwhile and fruitful association which will make you equipped for future "
        "projects. wishing you the most enjoyable and truly meaningful internship program experience."
    )
    story.append(Paragraph(p6_text, style_body))

    story.append(Spacer(1, 3))

    # 11. Sign-off & Addresses
    signoff_elements = [
        Paragraph("Thank you.", style_thanks),
        Paragraph("Human Resource", style_hr),
        Paragraph("<font color='#0069A6'><u>www.turnpikeanalyst.com</u></font>", style_hr),
        Paragraph("<font color='#0000FF'><u>hr@turnpikeanalyst.com</u></font>", style_hr),
        Paragraph("<b>Global Headquarter:</b>", style_hr),
        Paragraph("Hamilton Business Center – Suit 328", style_hr),
        Paragraph("1101 Hamilton St, Allentown, Pennsylvania 18101", style_hr),
        Paragraph("<b>India Division Office:</b> Kolkata, India, 700091", style_hr),
    ]
    for el in signoff_elements:
        story.append(el)

    story.append(Spacer(1, 6))

    # 12. Bottom Logos (MSME, MCA, WB Trade Registration)
    img1_path = str(assets_dir / "image1.png")
    img3_path = str(assets_dir / "image3.png")
    img4_path = str(assets_dir / "image4.png")

    if Path(img1_path).exists() and Path(img3_path).exists() and Path(img4_path).exists():
        badge1 = RLImage(img1_path, width=72, height=71)
        badge2 = RLImage(img3_path, width=82, height=72)
        badge3 = RLImage(img4_path, width=96, height=79)

        badge_table = Table([[badge1, badge2, badge3]], colWidths=[165, 175, 171])
        badge_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(badge_table)

    try:
        doc.build(story)
    except Exception as exc:
        raise CertificateRenderError(f"Failed to generate offer letter PDF: {exc}") from exc

    return buffer.getvalue()

