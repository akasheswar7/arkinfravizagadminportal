import io
import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
from PIL import Image as PILImage

from app.core.config import settings

logger = logging.getLogger(__name__)

# ARK Infra Brand Colors
NAVY_DEEP = colors.HexColor("#050d1a")
NAVY_MID = colors.HexColor("#122a47")
NAVY_LIGHT = colors.HexColor("#1e3d66")
GOLD = colors.HexColor("#c9a962")
GOLD_LIGHT = colors.HexColor("#e4d4a8")
TEXT_MUTED = colors.HexColor("#64748b")
TEXT_DARK = colors.HexColor("#1e293b")
BG_CARD = colors.HexColor("#f8fafc")
BORDER_COLOR = colors.HexColor("#e2e8f0")

def _clean_text(text: Optional[str]) -> str:
    """Sanitizes text for ReportLab Helvetica rendering by converting Unicode punctuation to ASCII."""
    if not text:
        return ""
    t = (
        str(text)
        .replace("—", " - ")
        .replace("–", " - ")
        .replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("…", "...")
    )
    t = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|nbsp);)', '&amp;', t)
    return t

class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages dynamically and adds running headers & footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(GOLD)

        # Header running line
        self.setStrokeColor(GOLD)
        self.setLineWidth(1)
        self.line(40, letter[1] - 40, letter[0] - 40, letter[1] - 40)
        self.drawString(40, letter[1] - 35, "ARK INFRA  |  OFFICIAL EXECUTIVE REPORT")

        # Footer running line & page number
        self.line(40, 45, letter[0] - 40, 45)
        self.setFont("Helvetica", 8)
        self.setFillColor(TEXT_MUTED)
        self.drawString(40, 32, "Confidential - For Internal Management & Real Estate Operations")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 40, 32, page_text)
        self.restoreState()

async def _resolve_image_to_flowable(image_path_or_url: Optional[str], width: float, height: float) -> Optional[RLImage]:
    """Safely loads and resizes an image for ReportLab flowables, checking local disk, MongoDB GridFS, or HTTP."""
    if not image_path_or_url:
        return None
    try:
        raw_bytes = None

        # 0. Base64 data URL
        if image_path_or_url.startswith("data:image/"):
            try:
                import base64
                if "," in image_path_or_url:
                    raw_bytes = base64.b64decode(image_path_or_url.split(",", 1)[1])
            except Exception as e:
                logger.warning(f"Could not decode base64 image: {e}")

        # 1. Local or GridFS upload: check for uploads path or filename
        if not raw_bytes and ("/uploads/" in image_path_or_url or "api/uploads/" in image_path_or_url or image_path_or_url.startswith("uploads/")):
            filename = image_path_or_url.split("/")[-1].split("?")[0]
            try:
                from app.services.storage_service import storage_service
                res = await storage_service.get_file(filename)
                if res:
                    raw_bytes = res[0]
            except Exception as e:
                logger.warning(f"StorageService fetch error for {filename}: {e}")

        # 2. Local images directory
        if not raw_bytes and "images/" in image_path_or_url and not image_path_or_url.startswith("http"):
            filename = image_path_or_url.split("images/")[-1]
            for base in [
                Path(__file__).resolve().parent.parent.parent.parent / "images",
                Path(__file__).resolve().parent.parent.parent / "images",
                Path("/tmp/images")
            ]:
                p = base / filename
                if p.exists():
                    try:
                        with open(p, "rb") as f:
                            raw_bytes = f.read()
                            break
                    except Exception:
                        pass

        # 3. Remote URL
        if not raw_bytes and image_path_or_url.startswith(("http://", "https://")):
            # If the remote URL points to our own app uploads, extract filename directly
            if "/uploads/" in image_path_or_url:
                filename = image_path_or_url.split("/")[-1].split("?")[0]
                try:
                    from app.services.storage_service import storage_service
                    res = await storage_service.get_file(filename)
                    if res:
                        raw_bytes = res[0]
                except Exception as e:
                    logger.warning(f"StorageService fetch error for {filename}: {e}")

            if not raw_bytes:
                import httpx
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(image_path_or_url)
                    if resp.status_code == 200:
                        raw_bytes = resp.content

        if raw_bytes:
            pil_img = PILImage.open(io.BytesIO(raw_bytes))
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=85)
            buf.seek(0)
            return RLImage(buf, width=width, height=height)
    except Exception as e:
        logger.warning(f"Could not load image for PDF ({image_path_or_url}): {e}")
    return None

def _create_placeholder_avatar(text: str, width: float, height: float) -> Table:
    """Returns a clean passport photo placeholder box when digital photo is not attached."""
    from reportlab.platypus import Paragraph
    styles = _get_styles()
    data = [[Paragraph("<font size='7' color='#64748b'><b>AFFIX<br/>PASSPORT<br/>PHOTO<br/>HERE</b></font>", styles['ArkBody'])]]
    t = Table(data, colWidths=[width], rowHeights=[height])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#94a3b8")),
    ]))
    return t

def _get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ArkTitle',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=NAVY_DEEP,
        alignment=0,
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name='ArkSubtitle',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=GOLD,
        alignment=0,
        spaceAfter=15
    ))
    styles.add(ParagraphStyle(
        name='ArkSectionHeader',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=NAVY_MID,
        spaceBefore=14,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='ArkCardTitle',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=NAVY_DEEP
    ))
    styles.add(ParagraphStyle(
        name='ArkCardRole',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=GOLD
    ))
    styles.add(ParagraphStyle(
        name='ArkQuote',
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#9a7b3a"),
        spaceBefore=2,
        spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name='ArkBody',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT_DARK
    ))
    styles.add(ParagraphStyle(
        name='ArkMuted',
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=TEXT_MUTED
    ))
    return styles

async def generate_team_hierarchy_pdf(
    directors: List[Dict[str, Any]],
    agents_by_director: Dict[str, List[Dict[str, Any]]],
    ceo_info: Optional[Dict[str, Any]] = None
) -> bytes:
    """Generates the Complete Team Structure Report with dynamic Executive Leadership, Directors, and all Agents."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=55,
        bottomMargin=55
    )
    styles = _get_styles()
    story = []

    # Title Banner
    story.append(Paragraph("ARK INFRA", styles['ArkTitle']))
    story.append(Paragraph(f"COMPLETE ORGANIZATIONAL TEAM HIERARCHY & ROSTER | {datetime.now().strftime('%d %B %Y')}", styles['ArkSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=15))

    # Identify Executive Leadership (Managing Director & CEO) dynamically from MongoDB directors
    md_candidates = [d for d in directors if any(k in (d.get("role") or "").lower() for k in ["managing", "md"])]
    ceo_candidates = [d for d in directors if any(k in (d.get("role") or "").lower() for k in ["ceo", "chief executive"])]

    leadership_directors = []
    if md_candidates:
        leadership_directors.extend(md_candidates)
    if ceo_candidates:
        for c in ceo_candidates:
            if c not in leadership_directors:
                leadership_directors.append(c)

    # Fallback to ceo_info if no leadership found in directors
    if not leadership_directors and ceo_info:
        leadership_directors = [ceo_info]

    # Executive Leadership Section
    if leadership_directors:
        story.append(Paragraph("Executive Leadership & Apex Management", styles['ArkSectionHeader']))
        story.append(HRFlowable(width="100%", thickness=0.8, color=GOLD, spaceAfter=8))

        for leader in leadership_directors:
            l_id = str(leader.get("id") or leader.get("_id", ""))
            l_name = _clean_text(leader.get("name", "Executive Leader"))
            l_role = _clean_text(leader.get("role", "Executive"))
            l_phone = _clean_text(leader.get("phone", "N/A"))
            l_email = _clean_text(leader.get("email", ""))
            l_bio = _clean_text(leader.get("bio", ""))
            l_quote = _clean_text(leader.get("quote", ""))
            l_img_url = leader.get("profile_image") or leader.get("image", "")

            l_img = await _resolve_image_to_flowable(l_img_url, 60, 60) or _create_placeholder_avatar(l_name, 60, 60)

            contact_parts = [f"<b>Phone:</b> {l_phone}"]
            if l_email:
                contact_parts.append(f"<b>Email:</b> {l_email}")
            contact_str = " &nbsp;|&nbsp; ".join(contact_parts)

            l_content = [
                Paragraph(f"<b>{l_name}</b>", styles['ArkCardTitle']),
                Paragraph(f"{l_role} &nbsp;|&nbsp; {contact_str}", styles['ArkCardRole']),
            ]
            if l_quote:
                l_content.append(Paragraph(f'"{l_quote}"', styles['ArkQuote']))
            if l_bio:
                l_content.append(Paragraph(l_bio, styles['ArkBody']))

            l_table = Table([[l_img, l_content]], colWidths=[70, 460])
            l_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), BG_CARD),
                ('BOX', (0,0), (-1,-1), 1.5, GOLD),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(l_table)

            # Assigned Agents under this leader
            leader_agents = agents_by_director.get(l_id, [])
            if leader_agents:
                agent_rows = [[
                    Paragraph("<b>Photo</b>", styles['ArkMuted']),
                    Paragraph("<b>Agent Name & Designation</b>", styles['ArkMuted']),
                    Paragraph("<b>Phone / Contact</b>", styles['ArkMuted']),
                    Paragraph("<b>Reporting Team Head</b>", styles['ArkMuted'])
                ]]
                for agent in leader_agents:
                    a_name = _clean_text(agent.get("full_name", "Agent"))
                    a_phone = _clean_text(agent.get("phone", "N/A"))
                    a_desig = _clean_text(agent.get("designation", "Real Estate Agent"))
                    a_team = _clean_text(agent.get("team_head_name", l_name))
                    a_img = await _resolve_image_to_flowable(agent.get("profile_image", ""), 32, 32) or _create_placeholder_avatar(a_name, 32, 32)
                    agent_rows.append([
                        a_img,
                        Paragraph(f"<b>{a_name}</b><br/><font color='#64748b'>{a_desig}</font>", styles['ArkBody']),
                        Paragraph(f"<font color='#0a1628'>{a_phone}</font>", styles['ArkBody']),
                        Paragraph(f"<font color='#c9a962'><b>{a_team}</b></font>", styles['ArkBody'])
                    ])
                agent_table = Table(agent_rows, colWidths=[45, 195, 140, 150])
                agent_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('PADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(agent_table)

            story.append(Spacer(1, 10))

    # Board of Directors & Operations Heads (excluding already-shown top leaders)
    board_directors = [d for d in directors if d not in leadership_directors]

    if board_directors:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Directors & Departmental Heads", styles['ArkSectionHeader']))
        story.append(HRFlowable(width="100%", thickness=0.8, color=GOLD, spaceAfter=8))

        for d_idx, director in enumerate(board_directors, start=1):
            d_id = str(director.get("id") or director.get("_id", ""))
            d_name = _clean_text(director.get("name", "Director"))
            d_role = _clean_text(director.get("role", "Director"))
            d_bio = _clean_text(director.get("bio", ""))
            d_phone = _clean_text(director.get("phone", "N/A"))
            d_email = _clean_text(director.get("email", ""))
            d_quote = _clean_text(director.get("quote", ""))
            d_img_url = director.get("profile_image", "")

            d_img = await _resolve_image_to_flowable(d_img_url, 50, 50) or _create_placeholder_avatar(d_name, 50, 50)

            contact_parts = [f"<b>Phone:</b> {d_phone}"]
            if d_email:
                contact_parts.append(f"<b>Email:</b> {d_email}")
            contact_str = " &nbsp;|&nbsp; ".join(contact_parts)

            d_content = [
                Paragraph(f"DIRECTOR {d_idx}: <b>{d_name}</b>", styles['ArkCardTitle']),
                Paragraph(f"<b>{d_role}</b> &nbsp;|&nbsp; {contact_str}", styles['ArkCardRole']),
            ]
            if d_quote:
                d_content.append(Paragraph(f'"{d_quote}"', styles['ArkQuote']))
            if d_bio:
                d_content.append(Paragraph(d_bio, styles['ArkBody']))

            d_card = Table([[d_img, d_content]], colWidths=[60, 470])
            d_card.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
                ('BOX', (0,0), (-1,-1), 1, NAVY_MID),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))

            d_elements = [d_card, Spacer(1, 4)]

            # Assigned Agents under this Director
            assigned_agents = agents_by_director.get(d_id, [])
            if assigned_agents:
                agent_rows = [[
                    Paragraph("<b>Photo</b>", styles['ArkMuted']),
                    Paragraph("<b>Agent Name & Designation</b>", styles['ArkMuted']),
                    Paragraph("<b>Phone / Contact</b>", styles['ArkMuted']),
                    Paragraph("<b>Reporting Team Head</b>", styles['ArkMuted'])
                ]]
                for agent in assigned_agents:
                    a_name = _clean_text(agent.get("full_name", "Agent"))
                    a_phone = _clean_text(agent.get("phone", "N/A"))
                    a_desig = _clean_text(agent.get("designation", "Real Estate Agent"))
                    a_team = _clean_text(agent.get("team_head_name", d_name))
                    a_img = await _resolve_image_to_flowable(agent.get("profile_image", ""), 32, 32) or _create_placeholder_avatar(a_name, 32, 32)
                    agent_rows.append([
                        a_img,
                        Paragraph(f"<b>{a_name}</b><br/><font color='#64748b'>{a_desig}</font>", styles['ArkBody']),
                        Paragraph(f"<font color='#0a1628'>{a_phone}</font>", styles['ArkBody']),
                        Paragraph(f"<font color='#c9a962'><b>{a_team}</b></font>", styles['ArkBody'])
                    ])

                agent_table = Table(agent_rows, colWidths=[45, 195, 140, 150])
                agent_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('PADDING', (0,0), (-1,-1), 4),
                ]))
                d_elements.append(agent_table)
            else:
                d_elements.append(Paragraph("<i>No field agents currently assigned under this director.</i>", styles['ArkMuted']))

            d_elements.append(Spacer(1, 10))
            story.append(KeepTogether(d_elements))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()

async def generate_director_pdf(director: Dict[str, Any], agents: List[Dict[str, Any]]) -> bytes:
    """Generates a dedicated report for an individual Director and their specific team of agents."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=55,
        bottomMargin=55
    )
    styles = _get_styles()
    story = []

    d_name = _clean_text(director.get("name", "Director"))
    d_role = _clean_text(director.get("role", "Director"))
    d_phone = _clean_text(director.get("phone", "N/A"))
    d_email = _clean_text(director.get("email", "arkinfraproperties@gmail.com"))
    d_bio = _clean_text(director.get("bio", ""))
    d_quote = _clean_text(director.get("quote", ""))

    # Header
    story.append(Paragraph("ARK INFRA", styles['ArkTitle']))
    story.append(Paragraph(f"DIRECTOR TEAM DOSSIER | {d_name.upper()}", styles['ArkSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=15))

    # Director Profile Card
    d_img = await _resolve_image_to_flowable(director.get("profile_image", ""), 75, 75) or _create_placeholder_avatar(d_name, 75, 75)

    d_info = [
        Paragraph(f"<b>{d_name}</b>", styles['ArkTitle']),
        Paragraph(f"<b>Role:</b> {d_role} &nbsp;|&nbsp; <b>Direct Phone:</b> {d_phone}", styles['ArkCardRole']),
        Paragraph(f"<b>Email:</b> {d_email}", styles['ArkBody']),
    ]
    if d_quote:
        d_info.extend([Spacer(1, 3), Paragraph(f'"{d_quote}"', styles['ArkQuote'])])
    if d_bio:
        d_info.extend([Spacer(1, 4), Paragraph(d_bio, styles['ArkBody'])])

    card_table = Table([[d_img, d_info]], colWidths=[85, 445])
    card_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_CARD),
        ('BOX', (0,0), (-1,-1), 1.5, GOLD),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 18))

    # Associated Agents Section
    story.append(Paragraph(f"Direct Reporting Agents & Field Executives ({len(agents)})", styles['ArkSectionHeader']))
    story.append(Paragraph(f"All agents assigned to the portfolio of Director {d_name}:", styles['ArkMuted']))
    story.append(Spacer(1, 8))

    if agents:
        agent_rows = [[
            Paragraph("<b>Photo</b>", styles['ArkMuted']),
            Paragraph("<b>Agent Name & Designation</b>", styles['ArkMuted']),
            Paragraph("<b>Contact Phone</b>", styles['ArkMuted']),
            Paragraph("<b>Assigned Team Head</b>", styles['ArkMuted'])
        ]]

        for agent in agents:
            a_name = _clean_text(agent.get("full_name", "Agent"))
            a_phone = _clean_text(agent.get("phone", "N/A"))
            a_desig = _clean_text(agent.get("designation", "Real Estate Agent"))
            a_team = _clean_text(agent.get("team_head_name", d_name))
            a_img = await _resolve_image_to_flowable(agent.get("profile_image", ""), 36, 36) or _create_placeholder_avatar(a_name, 36, 36)

            agent_rows.append([
                a_img,
                Paragraph(f"<b>{a_name}</b><br/><font color='#64748b'>{a_desig}</font>", styles['ArkBody']),
                Paragraph(f"<font color='#0a1628'>{a_phone}</font>", styles['ArkBody']),
                Paragraph(f"<font color='#c9a962'><b>{a_team}</b></font>", styles['ArkBody'])
            ])

        agent_table = Table(agent_rows, colWidths=[50, 190, 140, 150])
        agent_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(agent_table)
    else:
        story.append(Paragraph("<i>No field agents currently assigned to this Director.</i>", styles['ArkMuted']))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()

def generate_customers_pdf(customers: List[Dict[str, Any]], filter_status: str = "All") -> bytes:
    """Generates the Customer Site Visit and Registration Status Report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=55,
        bottomMargin=55
    )
    styles = _get_styles()
    story = []

    # Title Banner
    story.append(Paragraph("ARK INFRA", styles['ArkTitle']))
    story.append(Paragraph(f"CUSTOMER LEADS & SITE VISIT REPORT | STATUS: {filter_status.upper()}", styles['ArkSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=15))

    # Summary Statistics
    total = len(customers)
    pending = sum(1 for c in customers if c.get("site_visit_status") == "Pending")
    completed = sum(1 for c in customers if c.get("site_visit_status") == "Site Visit Completed")
    registered = sum(1 for c in customers if c.get("site_visit_status") == "Registration Completed")

    summary_data = [
        [
            Paragraph(f"<b>Total Records:</b> {total}", styles['ArkBody']),
            Paragraph(f"<b>Pending Visits:</b> {pending}", styles['ArkBody']),
            Paragraph(f"<b>Completed Visits:</b> {completed}", styles['ArkBody']),
            Paragraph(f"<b>Registrations:</b> {registered}", styles['ArkBody']),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[130, 130, 135, 135])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_CARD),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    # Customers Table
    if customers:
        rows = [
            [
                Paragraph("<b>#</b>", styles['ArkMuted']),
                Paragraph("<b>Customer Name & Contact</b>", styles['ArkMuted']),
                Paragraph("<b>Director & Agent</b>", styles['ArkMuted']),
                Paragraph("<b>Status & Date</b>", styles['ArkMuted']),
                Paragraph("<b>Venture & Plot Details</b>", styles['ArkMuted']),
                Paragraph("<b>Advance Paid & Notes</b>", styles['ArkMuted'])
            ]
        ]

        for idx, cust in enumerate(customers, start=1):
            c_name = _clean_text(cust.get("customer_name", "Customer"))
            c_phone = _clean_text(cust.get("phone") or "N/A")
            c_addr = _clean_text(cust.get("address") or "")
            c_contact_str = f"<b>{c_name}</b><br/>{c_phone}" + (f"<br/><font color='#64748b'>{c_addr}</font>" if c_addr else "")
            
            c_dir = _clean_text(cust.get("director_name") or "-")
            c_agent = _clean_text(cust.get("agent_name") or "-")
            c_team_str = f"<b>Dir:</b> {c_dir}<br/><b>Agent:</b> {c_agent}"

            c_date = _clean_text(cust.get("submission_date") or "-")
            c_status = _clean_text(cust.get("site_visit_status") or "Pending")

            status_color = "#eab308"
            if c_status in ["Registration Completed", "Amount Paid", "Positive"]:
                status_color = "#22c55e"
            elif c_status in ["Site Visit Completed"]:
                status_color = "#3b82f6"
            elif c_status in ["Fail", "Negative"]:
                status_color = "#ef4444"

            c_status_str = f"<font color='{status_color}'><b>{c_status}</b></font><br/><font color='#64748b'>{c_date}</font>"

            c_proj = _clean_text(cust.get("project_interested") or "-")
            c_plot_no = _clean_text(cust.get("plot_number") or "")
            c_plot_size = _clean_text(cust.get("plot_size") or "")
            c_plot_str = f"<b>{c_proj}</b>"
            if c_plot_no or c_plot_size:
                c_plot_str += f"<br/>Plot #{c_plot_no}" if c_plot_no else ""
                c_plot_str += f" ({c_plot_size})" if c_plot_size else ""

            c_adv = _clean_text(cust.get("advance_amount") or "")
            c_notes = _clean_text(cust.get("notes") or "")
            c_adv_str = f"<b>Adv:</b> {c_adv}" if c_adv else "<b>Adv:</b> None"
            if c_notes:
                c_adv_str += f"<br/><font color='#64748b'>{c_notes[:50]}</font>"

            rows.append([
                Paragraph(str(idx), styles['ArkMuted']),
                Paragraph(c_contact_str, styles['ArkBody']),
                Paragraph(c_team_str, styles['ArkBody']),
                Paragraph(c_status_str, styles['ArkBody']),
                Paragraph(c_plot_str, styles['ArkBody']),
                Paragraph(c_adv_str, styles['ArkBody'])
            ])

        cust_table = Table(rows, colWidths=[25, 115, 105, 95, 105, 85])
        cust_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(cust_table)
    else:
        story.append(Paragraph("<i>No customer records matching this status criteria.</i>", styles['ArkMuted']))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()

async def generate_site_application_pdf(app_data: Dict[str, Any]) -> bytes:
    """
    Generates an official, authorized, sensitive Customer Application & Advance Booking Receipt PDF
    for ARK Infra Developers, complete with customer photograph, site details, advance payment
    receipt acknowledgment, legal terms, authentic company stamp/seal, and signatures of MD and CEO.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=32
    )
    styles = _get_styles()
    story = []

    # 1. Header with Logo, Company Details & Application Box
    logo_img = await _resolve_image_to_flowable("images/logo.webp", 60, 60)

    app_no = _clean_text(app_data.get("application_no") or f"ARK-APP-{datetime.now().strftime('%Y%m%d%H%M')}")
    app_date = _clean_text(app_data.get("payment_date") or app_data.get("created_at_str") or datetime.now().strftime("%d-%m-%Y"))

    company_info = [
        Paragraph("<b><font size='14' color='#050d1a'>ARK INFRA AND DEVELOPERS</font></b>", styles['ArkTitle']),
        Paragraph("<font size='8' color='#9a7b3a'><b>OFFICIAL REAL ESTATE &amp; TOWNSHIP PROMOTERS</b></font>", styles['ArkBody']),
        Paragraph("<font size='7' color='#64748b'>Corporate Office: Visakhapatnam, Andhra Pradesh &bull; Regd. No: 132/2020 &bull; ISO 9001:2015 Certified<br/>Phone: +91 98484 98070 &bull; Email: arkinfraproperties@gmail.com &bull; Web: arkinfravizag.com</font>", styles['ArkBody'])
    ]

    badge_data = [
        [Paragraph(f"<b>APPLICATION NO:</b><br/><font color='#9a7b3a'><b>{app_no}</b></font>", styles['ArkBody'])],
        [Paragraph(f"<b>DATE:</b> {app_date}", styles['ArkBody'])]
    ]
    badge_table = Table(badge_data, colWidths=[140])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))

    header_table = Table([[logo_img or "", company_info, badge_table]], colWidths=[65, 335, 140])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=5, spaceBefore=3))

    # Title Bar
    title_data = [[
        Paragraph("<font size='9' color='#ffffff'><b>CUSTOMER APPLICATION &amp; ADVANCE PAYMENT FORM</b></font>", styles['ArkBody']),
        Paragraph("<font size='7' color='#e4d4a8'><b>OFFICIAL RECORD</b></font>", styles['ArkBody'])
    ]]
    title_table = Table(title_data, colWidths=[400, 140])
    title_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY_DEEP),
        ('PADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(title_table)
    story.append(Spacer(1, 4))

    # Customer Photo & Particulars
    c_name = _clean_text(app_data.get("customer_name", ""))
    cust_photo_url = app_data.get("photo_url") or app_data.get("photo_or_id") or app_data.get("customer_photo_url")
    cust_photo = await _resolve_image_to_flowable(cust_photo_url, 80, 95) or _create_placeholder_avatar(c_name, 80, 95)

    c_parent = _clean_text(app_data.get("father_or_spouse_name") or "-")
    c_phone = _clean_text(app_data.get("phone", ""))
    c_alt = _clean_text(app_data.get("alt_phone") or "-")
    c_email = _clean_text(app_data.get("email") or "-")
    c_address = _clean_text(app_data.get("address") or "-")
    c_aadhaar = _clean_text(app_data.get("aadhaar_or_id") or "-")

    customer_table_data = [
        [Paragraph("<b>Customer Name:</b>", styles['ArkBody']), Paragraph(f"<b>{c_name}</b>", styles['ArkBody']), cust_photo],
        [Paragraph("<b>S/o, W/o, D/o:</b>", styles['ArkBody']), Paragraph(c_parent, styles['ArkBody']), ""],
        [Paragraph("<b>Contact Phone:</b>", styles['ArkBody']), Paragraph(f"{c_phone}" + (f" (Alt: {c_alt})" if c_alt != "-" else ""), styles['ArkBody']), ""],
        [Paragraph("<b>Email Address:</b>", styles['ArkBody']), Paragraph(c_email, styles['ArkBody']), ""],
        [Paragraph("<b>Residential Address:</b>", styles['ArkBody']), Paragraph(c_address, styles['ArkBody']), ""],
        [Paragraph("<b>Aadhaar / ID No:</b>", styles['ArkBody']), Paragraph(c_aadhaar, styles['ArkBody']), ""]
    ]

    c_table = Table(customer_table_data, colWidths=[115, 335, 90])
    c_table.setStyle(TableStyle([
        ('SPAN', (2,0), (2,-1)),
        ('BACKGROUND', (0,0), (-1,-1), BG_CARD),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
        ('ALIGN', (2,0), (2,-1), 'CENTER'),
    ]))
    story.append(c_table)
    story.append(Spacer(1, 4))

    # Property Particulars
    v_name = _clean_text(app_data.get("venture_name") or app_data.get("project_interested") or "-")
    p_num = _clean_text(app_data.get("plot_number") or "-")
    p_size = _clean_text(app_data.get("plot_size") or "-")
    p_facing = _clean_text(app_data.get("plot_facing") or "-")

    story.append(Paragraph("<font size='8' color='#122a47'><b>PROPERTY &amp; VENTURE PARTICULARS</b></font>", styles['ArkBody']))

    prop_table_data = [
        [
            Paragraph("<b>Venture / Layout:</b>", styles['ArkBody']), Paragraph(f"<b>{v_name}</b>", styles['ArkBody']),
            Paragraph("<b>Plot Number:</b>", styles['ArkBody']), Paragraph(f"<b>{p_num}</b>", styles['ArkBody'])
        ],
        [
            Paragraph("<b>Plot Extent / Size:</b>", styles['ArkBody']), Paragraph(p_size, styles['ArkBody']),
            Paragraph("<b>Plot Facing:</b>", styles['ArkBody']), Paragraph(p_facing, styles['ArkBody'])
        ]
    ]
    p_table = Table(prop_table_data, colWidths=[120, 160, 110, 150])
    p_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_CARD),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(p_table)
    story.append(Spacer(1, 4))

    # Financial & Advance Payment Receipt Section (Clean & Prominent)
    adv_amt = _clean_text(app_data.get("advance_amount") or "0")
    adv_words = _clean_text(app_data.get("advance_amount_words") or "")
    pay_mode = _clean_text(app_data.get("payment_mode") or "Online / UPI Transfer")
    txn_id = _clean_text(app_data.get("transaction_id") or "Token Advance Verified")
    bal_amt = _clean_text(app_data.get("balance_amount") or "-")
    due_date = _clean_text(app_data.get("balance_due_date") or "As per agreed schedule")

    story.append(Paragraph("<font size='8' color='#166534'><b>ADVANCE PAYMENT &amp; MONEY TRANSACTION DETAILS</b></font>", styles['ArkBody']))

    fin_table_data = [
        [
            Paragraph("<b>Advance Amount Paid:</b>", styles['ArkBody']),
            Paragraph(f"<b><font size='10' color='#166534'>Rs. {adv_amt}</font></b>" + (f"<br/><font size='7' color='#475569'>({adv_words})</font>" if adv_words else ""), styles['ArkBody']),
            Paragraph("<b>Payment Date:</b>", styles['ArkBody']),
            Paragraph(app_date, styles['ArkBody'])
        ],
        [
            Paragraph("<b>Payment Mode:</b>", styles['ArkBody']),
            Paragraph(pay_mode, styles['ArkBody']),
            Paragraph("<b>Txn / Reference No:</b>", styles['ArkBody']),
            Paragraph(txn_id, styles['ArkBody'])
        ],
        [
            Paragraph("<b>Balance Consideration:</b>", styles['ArkBody']),
            Paragraph(f"Rs. {bal_amt}" if bal_amt != "-" and not bal_amt.startswith("Rs") and not bal_amt.startswith("₹") else bal_amt, styles['ArkBody']),
            Paragraph("<b>Payment Terms / Schedule:</b>", styles['ArkBody']),
            Paragraph(due_date, styles['ArkBody'])
        ]
    ]
    fin_table = Table(fin_table_data, colWidths=[120, 160, 110, 150])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0fdf4")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#86efac")),
        ('PADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(fin_table)
    story.append(Spacer(1, 4))

    # Clean Declaration
    declaration_text = (
        "<b>DECLARATION:</b> I hereby apply for the provisional booking and allotment of the cited plot "
        "and confirm that the particulars provided above are true and accurate. "
        "I agree to adhere to the payment schedule and terms of ARK Infra and Developers."
    )
    decl_table = Table([[Paragraph(declaration_text, styles['ArkMuted'])]], colWidths=[540])
    decl_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(decl_table)
    story.append(Spacer(1, 8))

    # Physical Signatures & Official Stamp Seal Area (Clean, Decent for Management Signing & Stamping)
    seal_table = Table(
        [[Paragraph("<font size='8' color='#475569'><b>OFFICIAL SEAL AREA</b><br/><font size='7' color='#94a3b8'>(COMPANY STAMP)</font></font>", styles['ArkBody'])]],
        colWidths=[150],
        rowHeights=[55]
    )
    seal_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#94a3b8")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    sig_data = [
        [
            Paragraph("<br/><br/><br/>___________________________________<br/><b>SIGNATURE OF APPLICANT</b><br/><font color='#64748b' size='7'>(" + c_name + ")</font>", styles['ArkBody']),
            seal_table,
            Paragraph("<br/><br/><br/>___________________________________<br/><b>AUTHORIZED SIGNATORY</b><br/><font color='#050d1a' size='8'><b>ARK Infra and Developers</b></font><br/><font color='#64748b' size='6'>Management Desk</font>", styles['ArkBody'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[190, 160, 190])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('ALIGN', (2,0), (2,0), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(sig_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()

