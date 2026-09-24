import io
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, PageBreak, HRFlowable
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

def _resolve_image_to_flowable(image_path_or_url: Optional[str], width: float, height: float) -> Optional[RLImage]:
    """Safely loads and resizes an image for ReportLab flowables, returning None on failure."""
    if not image_path_or_url:
        return None
    try:
        pil_img = None
        # Case 1: Local file in uploads
        if "/uploads/" in image_path_or_url or image_path_or_url.startswith("uploads/"):
            filename = image_path_or_url.split("/uploads/")[-1]
            local_file = Path(__file__).resolve().parent.parent.parent / settings.UPLOAD_DIR / filename
            if local_file.exists():
                pil_img = PILImage.open(local_file)
        
        # Case 2: Local images directory
        if not pil_img and "images/" in image_path_or_url:
            filename = image_path_or_url.split("images/")[-1]
            proj_img = Path(__file__).resolve().parent.parent.parent.parent / "images" / filename
            if proj_img.exists():
                pil_img = PILImage.open(proj_img)

        # Case 3: Remote URL
        if not pil_img and image_path_or_url.startswith(("http://", "https://")):
            import httpx
            resp = httpx.get(image_path_or_url, timeout=3.0)
            if resp.status_code == 200:
                pil_img = PILImage.open(io.BytesIO(resp.content))

        if pil_img:
            # Ensure RGB mode
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
    """Returns a styled avatar box when photo is not present."""
    initials = "".join([part[0].upper() for part in text.split()[:2]]) or "ARK"
    data = [[initials]]
    t = Table(data, colWidths=[width], rowHeights=[height])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY_MID),
        ('TEXTCOLOR', (0,0), (-1,-1), GOLD),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 12),
        ('BOX', (0,0), (-1,-1), 1, GOLD),
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
        spaceBefore=12,
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
        name='ArkBody',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
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

def generate_team_hierarchy_pdf(
    directors: List[Dict[str, Any]],
    agents_by_director: Dict[str, List[Dict[str, Any]]],
    ceo_info: Optional[Dict[str, Any]] = None
) -> bytes:
    """Generates the Complete Team Structure Report with CEO, Directors, and all Agents."""
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
    story.append(Paragraph(f"COMPLETE ORGANIZATIONAL TEAM HIERARCHY & ROSTER — {datetime.now().strftime('%d %B %Y')}", styles['ArkSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=15))

    # Executive Leadership (CEO)
    if ceo_info:
        ceo_name = ceo_info.get("name", "Konathala Hanumantharao (Arun)")
        ceo_role = ceo_info.get("role", "Chief Executive Officer (CEO)")
        ceo_phone = ceo_info.get("phone", "+91 81255 47801")
        ceo_bio = ceo_info.get("bio", "Oversees company strategic vision, acquisitions, and prime developments.")
        
        ceo_img = _resolve_image_to_flowable(ceo_info.get("image", "images/ceo-arun.webp"), 55, 55) or _create_placeholder_avatar(ceo_name, 55, 55)
        
        ceo_text = [
            Paragraph(f"<b>{ceo_name}</b>", styles['ArkCardTitle']),
            Paragraph(ceo_role, styles['ArkCardRole']),
            Paragraph(f"<b>Direct Contact:</b> {ceo_phone}", styles['ArkBody']),
            Paragraph(ceo_bio, styles['ArkMuted'])
        ]
        
        ceo_table = Table([[ceo_img, ceo_text]], colWidths=[65, 465])
        ceo_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BG_CARD),
            ('BOX', (0,0), (-1,-1), 1.5, GOLD),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(ceo_table)
        story.append(Spacer(1, 15))

    # Directors and their Agents
    for d_idx, director in enumerate(directors, start=1):
        d_id = str(director.get("id") or director.get("_id", ""))
        d_name = director.get("name", "Director")
        d_role = director.get("role", "Director")
        d_bio = director.get("bio", "Executive leadership at ARK Infra.")
        d_phone = director.get("phone", "N/A")
        d_img_url = director.get("profile_image", "")
        
        d_img = _resolve_image_to_flowable(d_img_url, 50, 50) or _create_placeholder_avatar(d_name, 50, 50)
        
        d_content = [
            Paragraph(f"DIRECTOR {d_idx}: <b>{d_name}</b>", styles['ArkCardTitle']),
            Paragraph(f"{d_role} &nbsp;|&nbsp; Phone: {d_phone}", styles['ArkCardRole']),
            Paragraph(d_bio[:250] + ("..." if len(d_bio) > 250 else ""), styles['ArkBody'])
        ]
        
        d_card = Table([[d_img, d_content]], colWidths=[60, 470])
        d_card.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
            ('BOX', (0,0), (-1,-1), 1, NAVY_MID),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))

        d_elements = [Spacer(1, 10), d_card, Spacer(1, 6)]

        # Assigned Agents under this Director
        assigned_agents = agents_by_director.get(d_id, [])
        if assigned_agents:
            agent_rows = []
            # Table Header
            agent_rows.append([
                Paragraph("<b>Photo</b>", styles['ArkMuted']),
                Paragraph("<b>Agent Name & Designation</b>", styles['ArkMuted']),
                Paragraph("<b>Phone / Contact</b>", styles['ArkMuted']),
                Paragraph("<b>Reporting Team Head</b>", styles['ArkMuted'])
            ])

            for agent in assigned_agents:
                a_name = agent.get("full_name", "Agent")
                a_phone = agent.get("phone", "N/A")
                a_desig = agent.get("designation", "Real Estate Agent")
                a_team = agent.get("team_head_name", d_name)
                a_img = _resolve_image_to_flowable(agent.get("profile_image", ""), 32, 32) or _create_placeholder_avatar(a_name, 32, 32)

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
            d_elements.append(Paragraph("<i>No agents currently assigned under this director.</i>", styles['ArkMuted']))

        d_elements.append(Spacer(1, 12))
        story.append(KeepTogether(d_elements))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()

def generate_director_pdf(director: Dict[str, Any], agents: List[Dict[str, Any]]) -> bytes:
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

    d_name = director.get("name", "Director")
    d_role = director.get("role", "Director")
    d_phone = director.get("phone", "N/A")
    d_email = director.get("email", "info@arkinfravizag.com")
    d_bio = director.get("bio", "")

    # Header
    story.append(Paragraph("ARK INFRA", styles['ArkTitle']))
    story.append(Paragraph(f"DIRECTOR TEAM DOSSIER — {d_name.upper()}", styles['ArkSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=15))

    # Director Profile Card
    d_img = _resolve_image_to_flowable(director.get("profile_image", ""), 75, 75) or _create_placeholder_avatar(d_name, 75, 75)
    
    d_info = [
        Paragraph(f"<b>{d_name}</b>", styles['ArkTitle']),
        Paragraph(f"<b>Role:</b> {d_role} &nbsp;|&nbsp; <b>Direct Phone:</b> {d_phone}", styles['ArkCardRole']),
        Paragraph(f"<b>Email:</b> {d_email}", styles['ArkBody']),
        Spacer(1, 4),
        Paragraph(d_bio, styles['ArkBody'])
    ]

    card_table = Table([[d_img, d_info]], colWidths=[85, 445])
    card_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_CARD),
        ('BOX', (0,0), (-1,-1), 1.5, GOLD),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 20))

    # Associated Agents Section
    story.append(Paragraph(f"Direct Reporting Agents & Field Executives ({len(agents)})", styles['ArkSectionHeader']))
    story.append(Paragraph(f"All agents assigned to the portfolio of Director {d_name}:", styles['ArkMuted']))
    story.append(Spacer(1, 8))

    if agents:
        agent_rows = []
        agent_rows.append([
            Paragraph("<b>Photo</b>", styles['ArkMuted']),
            Paragraph("<b>Agent Name & Designation</b>", styles['ArkMuted']),
            Paragraph("<b>Contact Phone</b>", styles['ArkMuted']),
            Paragraph("<b>Assigned Team Head</b>", styles['ArkMuted'])
        ])

        for agent in agents:
            a_name = agent.get("full_name", "Agent")
            a_phone = agent.get("phone", "N/A")
            a_desig = agent.get("designation", "Real Estate Agent")
            a_team = agent.get("team_head_name", d_name)
            a_img = _resolve_image_to_flowable(agent.get("profile_image", ""), 36, 36) or _create_placeholder_avatar(a_name, 36, 36)

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
        story.append(Paragraph("<i>No agents currently assigned to this Director.</i>", styles['ArkMuted']))

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
    story.append(Paragraph(f"CUSTOMER LEADS & SITE VISIT REPORT — STATUS: {filter_status.upper()}", styles['ArkSubtitle']))
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
                Paragraph("<b>Customer Name</b>", styles['ArkMuted']),
                Paragraph("<b>Phone / Contact</b>", styles['ArkMuted']),
                Paragraph("<b>Submission Date</b>", styles['ArkMuted']),
                Paragraph("<b>Site Visit Status</b>", styles['ArkMuted']),
                Paragraph("<b>Project / Notes</b>", styles['ArkMuted'])
            ]
        ]

        for idx, cust in enumerate(customers, start=1):
            c_name = cust.get("customer_name", "Customer")
            c_phone = cust.get("phone") or "N/A"
            c_date = cust.get("submission_date") or "-"
            c_status = cust.get("site_visit_status") or "Pending"
            c_notes = cust.get("notes") or cust.get("project_interested") or "-"

            # Status color tag
            status_color = "#eab308"  # Yellow for pending
            if c_status == "Site Visit Completed":
                status_color = "#3b82f6"  # Blue
            elif c_status == "Registration Completed":
                status_color = "#22c55e"  # Green

            rows.append([
                Paragraph(str(idx), styles['ArkMuted']),
                Paragraph(f"<b>{c_name}</b>", styles['ArkBody']),
                Paragraph(c_phone, styles['ArkBody']),
                Paragraph(c_date, styles['ArkBody']),
                Paragraph(f"<font color='{status_color}'><b>{c_status}</b></font>", styles['ArkBody']),
                Paragraph(c_notes[:80] + ("..." if len(c_notes) > 80 else ""), styles['ArkMuted'])
            ])

        cust_table = Table(rows, colWidths=[25, 125, 95, 80, 105, 100])
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
