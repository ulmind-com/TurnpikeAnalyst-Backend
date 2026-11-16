"""Generate dynamic, publication-grade Internship Offer Letters.

Renders high-fidelity, printable HTML documents (and PDF-ready output)
with official Turnpike Analyst branding, dynamic candidate details,
and tailored track/technology competencies.
"""

from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Static branding assets directory
BRANDING_DIR = Path(__file__).resolve().parent.parent / "static" / "branding"

def _get_base64_image(filename: str) -> str:
    path = BRANDING_DIR / filename
    if path.exists():
        data = path.read_bytes()
        mime = "image/png"
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    return ""

TRACK_COMPETENCIES = {
    "FRONTEND": {
        "role": "Frontend Engineering Intern",
        "technologies": (
            "Modern JavaScript (ES6+), TypeScript, React, Next.js, HTML5, CSS3/Tailwind CSS, "
            "Responsive Web Design, Component Architecture, State Management, REST API Integration, "
            "Client-Side Performance Optimization, and Git/GitHub."
        ),
    },
    "BACKEND": {
        "role": "Backend Engineering Intern",
        "technologies": (
            "Python, FastAPI, Node.js, Express, MongoDB, PostgreSQL, RESTful API Architecture, "
            "JWT Authentication, Microservices Design, Schema Validation, Docker Containerization, "
            "Database Query Optimization, and Git/GitHub."
        ),
    },
    "DESIGN": {
        "role": "UI/UX & Product Design Intern",
        "technologies": (
            "Figma, Wireframing, High-Fidelity Prototyping, Design Systems, Typography & Color Hierarchy, "
            "User Journey Mapping, Information Architecture, Usability Testing, Responsive Layouts, "
            "and Design-to-Code Engineering Handoff."
        ),
    },
    "FULLSTACK": {
        "role": "Full Stack Engineering Intern",
        "technologies": (
            "React, TypeScript, Next.js, Python, FastAPI, Node.js, MongoDB, PostgreSQL, "
            "REST APIs, Authentication, State Management, Cloud Deployment, and End-to-End System Integration."
        ),
    },
    "DATA_ENGINEERING": {
        "role": "Data Engineering & Analytics Intern",
        "technologies": (
            "Python, SQL, PostgreSQL, Pandas, NumPy, Data Pipeline ETL Architecture, Schema Modeling, "
            "Query Optimization, Data Aggregation, and RESTful Reporting Endpoints."
        ),
    },
    "AI": {
        "role": "AI & Machine Learning Intern",
        "technologies": (
            "Python, PyTorch, Large Language Models (LLMs), LangChain, Vector Embeddings, "
            "Retrieval-Augmented Generation (RAG), Prompt Engineering, FastAPI, and Model Serving."
        ),
    },
}

def detect_competencies(track_title: str, project_title: str, summary: str = "") -> Dict[str, str]:
    text = f"{track_title} {project_title} {summary}".lower()
    
    if any(k in text for k in ["ui", "ux", "design", "figma", "wireframe", "prototype"]):
        return TRACK_COMPETENCIES["DESIGN"]
    if any(k in text for k in ["data", "etl", "analytics", "reconciliation"]):
        return TRACK_COMPETENCIES["DATA_ENGINEERING"]
    if any(k in text for k in ["ai", "machine learning", "ml", "llm", "neural", "langchain"]):
        return TRACK_COMPETENCIES["AI"]
    if any(k in text for k in ["backend", "api", "service", "database", "retention", "fastapi", "django"]):
        return TRACK_COMPETENCIES["BACKEND"]
    if any(k in text for k in ["frontend", "ui", "react", "web", "dashboard", "portal", "website"]):
        return TRACK_COMPETENCIES["FRONTEND"]
    
    return TRACK_COMPETENCIES["FULLSTACK"]

def generate_offer_letter_html(
    *,
    recipient_name: str,
    enrollment_id: str,
    track_title: str = "Software Engineering",
    project_title: str = "Enterprise Solution",
    summary: str = "",
    duration_months: int = 1,
    enrolled_at: Optional[datetime] = None,
    college_name: Optional[str] = None,
) -> str:
    now = datetime.now(timezone.utc)
    issue_date = (enrolled_at or now).strftime("%d %B %Y")
    start_month_year = (enrolled_at or now).strftime("%B %Y")
    
    # Consignment number format: e.g. 0875/TPA2026 or derived from enrollment ID
    short_id = enrollment_id[-4:].upper() if len(enrollment_id) >= 4 else "0875"
    consignment_no = f"0875/TPA{now.year}" if not short_id.isdigit() else f"{short_id}/TPA{now.year}"
    
    comp = detect_competencies(track_title, project_title, summary)
    role_title = comp["role"]
    tech_stack = comp["technologies"]
    
    # College sentence
    if college_name and college_name.strip():
        college_clause = f"from your institution, {college_name.strip()}"
    else:
        college_clause = "from leading engineering institutions across India"

    # Images (Base64)
    logo_b64 = _get_base64_image("image2.png")
    msme_b64 = _get_base64_image("image1.png")
    mca_b64 = _get_base64_image("image3.png")
    wb_b64 = _get_base64_image("image4.png")

    duration_text = f"{duration_months} Month{'s' if duration_months > 1 else ''}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>TurnPikeAnalyst - Internship Offer Letter - {recipient_name}</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 12mm 18mm 12mm 18mm;
    }}
    * {{
      box-sizing: border-box;
      -webkit-font-smoothing: antialiased;
    }}
    body {{
      font-family: "Calibri", "Segoe UI", Arial, sans-serif;
      font-size: 10pt;
      line-height: 1.38;
      color: #222222;
      background-color: #f7f9fa;
      margin: 0;
      padding: 24px 0;
    }}
    .sheet {{
      background: #ffffff;
      width: 210mm;
      min-height: 297mm;
      margin: 0 auto;
      padding: 16mm 20mm 14mm 20mm;
      box-shadow: 0 4px 20px rgba(0,0,0,0.08);
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    @media print {{
      body {{
        background: none;
        padding: 0;
      }}
      .sheet {{
        width: 100%;
        min-height: auto;
        box-shadow: none;
        padding: 0;
        margin: 0;
      }}
      .no-print {{
        display: none !important;
      }}
    }}
    
    /* Top Bar: Title & Logo */
    .header-table {{
      width: 100%;
      margin-bottom: 8px;
    }}
    .header-logo {{
      text-align: right;
      vertical-align: top;
      width: 40%;
    }}
    .header-logo img {{
      height: 48px;
      width: auto;
      object-fit: contain;
    }}
    .brand-title {{
      font-family: "High Tower Text", "Georgia", serif;
      font-size: 24pt;
      font-weight: 700;
      color: #0b1a2b;
      margin: 0;
      line-height: 1.1;
    }}
    .doc-subtitle {{
      font-family: "Cambria", "Georgia", serif;
      font-size: 14pt;
      font-weight: 600;
      color: #111111;
      text-decoration: underline;
      text-underline-offset: 3px;
      margin: 4px 0 0 0;
      letter-spacing: 0.5px;
    }}

    /* Metadata right aligned */
    .meta-box {{
      text-align: right;
      font-family: "Verdana", sans-serif;
      font-size: 8.5pt;
      font-weight: 700;
      color: #333333;
      margin-top: 10px;
      margin-bottom: 12px;
      line-height: 1.5;
    }}
    
    /* Salutation */
    .salutation {{
      font-size: 10pt;
      font-weight: 600;
      margin-bottom: 10px;
      color: #111111;
    }}
    .greeting {{
      font-size: 9.5pt;
      font-weight: 600;
      margin-bottom: 10px;
      color: #222222;
    }}

    /* Body Paragraphs */
    .content p {{
      margin: 0 0 10px 0;
      text-align: justify;
      color: #2a2a2a;
    }}
    .highlight {{
      font-weight: 700;
      color: #111111;
    }}

    /* Sign-off & Address */
    .signoff {{
      margin-top: 12px;
      font-family: "Courier New", Courier, monospace;
      font-size: 8.5pt;
      color: #333333;
      line-height: 1.35;
    }}
    .signoff .thank-you {{
      font-family: "Cambria", serif;
      font-size: 11pt;
      color: #333333;
      margin-bottom: 4px;
    }}
    .signoff a {{
      color: #0066cc;
      text-decoration: underline;
    }}
    .signoff .addr-title {{
      font-weight: 700;
      color: #111111;
    }}

    /* Footer Certifications / Seals */
    .footer-seals {{
      margin-top: 14px;
      padding-top: 10px;
      border-top: 1px solid #e2e8f0;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
    }}
    .seal-item {{
      text-align: center;
      flex: 1;
    }}
    .seal-item img {{
      height: 64px;
      width: auto;
      object-fit: contain;
      display: inline-block;
      margin-bottom: 4px;
    }}
    .seal-caption {{
      font-family: "Arial", sans-serif;
      font-size: 7.5pt;
      font-weight: 700;
      color: #222222;
      line-height: 1.2;
    }}

    /* Floating action toolbar for browser preview */
    .toolbar {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #0f172a;
      color: white;
      padding: 10px 18px;
      border-radius: 9999px;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      gap: 12px;
      font-family: system-ui, sans-serif;
      font-size: 13px;
      z-index: 1000;
    }}
    .toolbar button {{
      background: #10b981;
      color: white;
      border: none;
      padding: 6px 14px;
      border-radius: 9999px;
      font-weight: 600;
      font-size: 12px;
      cursor: pointer;
      transition: background 0.2s;
    }}
    .toolbar button:hover {{
      background: #059669;
    }}
  </style>
</head>
<body>

  <!-- Floating Print Toolbar -->
  <div class="toolbar no-print">
    <span>Turnpike Analyst Official Document</span>
    <button onclick="window.print()">🖨️ Print / Save as PDF</button>
  </div>

  <div class="sheet">
    <div>
      <!-- Header Table -->
      <table class="header-table" cellpadding="0" cellspacing="0">
        <tr>
          <td style="vertical-align: middle;">
            <div class="brand-title">TurnPikeAnalyst</div>
            <div class="doc-subtitle">INTERNSHIP OFFER LETTER</div>
          </td>
          <td class="header-logo">
            <img src="{logo_b64}" alt="TurnPikeAnalyst">
          </td>
        </tr>
      </table>

      <!-- Consignment Metadata -->
      <div class="meta-box">
        <div>Consignment no: {consignment_no}</div>
        <div>Date: {issue_date}</div>
      </div>

      <!-- Salutation -->
      <div class="salutation">Dear {recipient_name},</div>
      <div class="greeting">Hope you are doing well!!</div>

      <!-- Content -->
      <div class="content">
        <p>
          TurnPikeAnalyst is pleased to release <span class="highlight">Long Term Contractual Internship in {role_title} ({duration_text})</span> to you. This letter of Internship is a formal agreement between you and TurnPikeAnalyst; you would be associated with TurnPikeAnalyst <span class="highlight">starting from {start_month_year}</span>. After successful completion of the internship, a verified credential and IT experience certificate will be approved and provided.
        </p>

        <p>
          TurnPikeAnalyst is confident that this internship will embrace orientation and place strong emphasis on learning modern industry engineering skills with deeper conceptual understanding through hands-on application of knowledge. Our structured curriculum is designed to help you gain end-to-end practical mastery. You will collaborate with peers and mentors {college_clause}. All mentors are experienced practitioners and confident that you will acknowledge your obligation to perform all work allocated to you to the best of your ability within lawful and reasonable direction given to you.
        </p>

        <p>
          Successful completion of this internship will earn you an accredited IT Experience Letter covering the technologies and architecture patterns considered part of your project track (<span class="highlight">{track_title}</span>), including but not limited to: <span class="highlight">{tech_stack}</span>
        </p>

        <p>
          As an engineering contractor, you will have access to confidential information, architectures, and intellectual assets that remain the exclusive property of TurnPikeAnalyst. This agreement shall be governed, interpreted, and construed in accordance with the laws of Pennsylvania, United States for TurnPikeAnalyst LLC, and West Bengal, India for TurnPikeAnalyst LLP Information Technology laws and jurisdiction in case of violation.
        </p>

        <p>
          This is an educational, self-directed experiential internship program wherein neither TurnPikeAnalyst nor the associate would pay any wages, placement charges, or fees to anyone.
        </p>

        <p>
          We look forward to a worthwhile and fruitful association which will equip you with production-grade engineering competence for future enterprise projects. Wishing you an enjoyable and truly meaningful internship experience.
        </p>
      </div>

      <!-- Signoff -->
      <div class="signoff">
        <div class="thank-you">Thank you.</div>
        <div>Human Resource Department</div>
        <div><a href="https://www.turnpikeanalyst.com">www.turnpikeanalyst.com</a></div>
        <div><a href="mailto:hr@turnpikeanalyst.com">hr@turnpikeanalyst.com</a></div>
        <div style="margin-top: 4px;">
          <span class="addr-title">Global Headquarter:</span><br>
          Hamilton Business Center – Suite 328<br>
          1101 Hamilton St, Allentown, Pennsylvania 18101, United States
        </div>
        <div style="margin-top: 4px;">
          <span class="addr-title">India Division Office:</span> Kolkata, West Bengal, India, 700091
        </div>
      </div>
    </div>

    <!-- Footer Statutory Seals -->
    <div class="footer-seals">
      <div class="seal-item">
        <img src="{msme_b64}" alt="MSME"><br>
        <span class="seal-caption">MICRO, SMALL & MEDIUM ENTERPRISES<br>GOVT. OF INDIA</span>
      </div>
      <div class="seal-item">
        <img src="{mca_b64}" alt="MCA"><br>
        <span class="seal-caption">Ministry of Corporate Affairs<br>Office of Registrar of Companies<br>LLP Identification Number: ABZ-6948</span>
      </div>
      <div class="seal-item">
        <img src="{wb_b64}" alt="Govt of West Bengal"><br>
        <span class="seal-caption">Govt. of West Bengal<br>Trade Registration No: 1318</span>
      </div>
    </div>
  </div>

</body>
</html>"""
    return html
