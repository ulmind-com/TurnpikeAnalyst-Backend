"""Seed the singleton homepage CMS document with the current site content.

Idempotent upsert into `site_content/_id=homepage`. Mirrors the values that
were previously hardcoded in the frontend so the public site renders
identically until an admin edits it.

Run: ./.venv/bin/python -m scripts.seed_homepage
"""

import asyncio
import logging

from app.db.mongodb import db_client, get_db
from app.schemas.homepage import HomepageUpdate
from app.crud.homepage import set_homepage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_homepage")

HERO_TILES = [
    {"type": "solid", "bg": "#ef5d44", "tag": "ARCHIVE"},
    {"type": "photo", "tag": "MIGRATION"},
    {"type": "photo", "tag": "PRECISION"},
    {"type": "solid", "bg": "#9fd5f7", "tag": "AUTOMATION"},
    {"type": "photo", "tag": "ORCHESTRATE"},
    {"type": "solid", "bg": "#fcdd71", "tag": "INTELLIGENCE"},
    {"type": "photo", "tag": "ENTERPRISE"},
    {"type": "solid", "bg": "#151515", "tag": "WATSONX"},
    {"type": "photo", "tag": "GOVERNANCE"},
    {"type": "solid", "bg": "#ef5d44", "tag": "SCALE"},
    {"type": "solid", "bg": "#9fd5f7", "tag": "PIPELINES"},
    {"type": "solid", "bg": "#f9f6f1", "tag": "FIDELITY"},
    {"type": "photo", "tag": "SECURITY"},
    {"type": "solid", "bg": "#fcdd71", "tag": "RUNTIME"},
    {"type": "photo", "tag": "RECORDS"},
]

HOMEPAGE = {
    "hero": {
        "badge": "ENTERPRISE ARCHIVE & AUTOMATION",
        "title_lines": ["We Are Solution", "Oriented"],
        "highlight_word": "Digital",
        "title_suffix": "Agency",
        "subtitle": (
            "Enterprise content migration, intelligent automation and "
            "practitioner-led engineering — purpose-built for regulated "
            "organisations that cannot afford to lose a single record."
        ),
        "primary_cta": {"label": "Get Started", "href": "#contact"},
        "secondary_cta": {"label": "How It Works", "href": "#services"},
        "tiles": HERO_TILES,
    },
    "hero_claims": [
        {
            "title": "Empowering Innovation With Artificial Intelligence",
            "body": "JAMES WEBB Server enables seamless migration between any ECM platforms — FileNet, OpenText, Documentum and SharePoint — with secure, automated transfers of content and metadata across on-premises, cloud or hybrid estates.",
        },
        {
            "title": "The Global Leader in ECM & Data Migration",
            "body": "Turnpike Analyst is a global leader in ECM, ETL and ESB solutions. Our tooling and deep expertise enable lossless ECM-to-ECM migrations that modernise content platforms, unify data and optimise performance.",
        },
        {
            "title": "Machine Learning: Unlocking Intelligent Insights",
            "body": "Advanced platforms that combine powerful AI capability with intuitive interfaces — delivering actionable insight, smarter automation and measurable operational impact across every industry we serve.",
        },
    ],
    "platform_stats": {
        "service_label": "Service capabilities",
        "product_label": "Platform products",
        "product_value": 2,
        "course_label": "Academy courses",
    },
    "tech_heading": {
        "eyebrow": "Technology",
        "title": "Our Enterprise Technology Stack",
        "description": "The platforms, clouds and languages we deliver migrations and automation on.",
    },
    "tech_stack": [
        {"category": "Platforms", "items": ["IBM FileNet P8", "OpenText", "Documentum", "SharePoint", "Hyland OnBase", "Nuxeo", "Box"]},
        {"category": "Cloud", "items": ["AWS", "Azure", "Kubernetes", "RHOCP"]},
        {"category": "Database", "items": ["Oracle", "MS SQL Server", "PostgreSQL"]},
        {"category": "Languages", "items": ["Java", "Python", "Node.js"]},
        {"category": "Automation", "items": ["MuleSoft", "Datacap", "Kofax"]},
    ],
    "services_heading": {
        "eyebrow": "What we do",
        "title": "Enterprise services, delivered by specialists",
        "description": "From estate discovery to cutover and enablement — the full migration and automation lifecycle.",
    },
    "industries_heading": {
        "eyebrow": "Industries",
        "title": "Trusted across regulated sectors",
        "description": "Deep domain delivery for the industries where content integrity is non-negotiable.",
    },
    "flagships": [
        {
            "id": "agent-p8",
            "eyebrow": "Agent P8",
            "title": "Goodbye, IBM FileNet P8 administrator",
            "body": "Agent P8 is an AI-powered operator that monitors and manages the entire IBM FileNet P8 suite across every supported operating system, cloud (AWS, Azure) and database (DB2, Oracle, PostgreSQL). It gives real-time visibility into CPE, ICN, BAW, BAI, RPA, LDAP and any supported application server — detecting issues, applying intelligent fixes and raising tickets in ServiceNow or Jira automatically.",
            "bullets": [
                {"title": "24/7 virtual engineer with an optional chat interface", "body": "Always active and monitoring the state of your infrastructure."},
                {"title": "Automatic detection, diagnosis and remediation", "body": "Self-healing capabilities that resolve issues before users notice."},
                {"title": "Class creation and object store configuration on request", "body": "Instantly translate natural language into platform configurations."},
                {"title": "Native ServiceNow and Jira integration", "body": "Automated ticket generation, updating, and closure."},
            ],
            "cta": "Request an Agent P8 demo",
        },
        {
            "id": "james-webb",
            "eyebrow": "James Webb Server",
            "title": "Universal ECM migration, any platform to any platform",
            "body": "JAMES WEBB Server migrates content and metadata from any ECM platform to any other — regardless of vendor or format. Whether you are moving off FileNet, OpenText, SharePoint or Documentum, it delivers a secure, structured and lossless migration tailored to your industry and deployment model.",
            "bullets": [
                {"title": "Vendor-neutral source and target connectors", "body": "Direct native API connections to over 25 enterprise content management platforms for lossless extraction without intermediate mapping."},
                {"title": "Full metadata, version and permission fidelity", "body": "Preserve the exact document history, security models, and custom metadata properties during transit to ensure total compliance."},
                {"title": "On-premises, cloud and hybrid deployment models", "body": "Run the migration engine exactly where your data is—fully containerized, scalable, and compliant with strict data sovereignty laws."},
                {"title": "Auditable reconciliation reporting at every stage", "body": "Cryptographic hashing and chain-of-custody reporting guarantees every single record is accounted for and verifiable."},
            ],
            "cta": "View price plans",
        },
    ],
    "capabilities": [
        {"icon": "briefcase", "title": "Business Consultancy", "body": "Estate discovery, platform assessment and a migration business case your board can sign off on — grounded in the real state of your content systems."},
        {"icon": "code", "title": "Business Development", "body": "Custom engineering around your ECM core: connectors, ingestion pipelines, viewers and workflow services built to your governance standards."},
        {"icon": "search", "title": "Search & Findability", "body": "Metadata modelling, indexing strategy and search tuning so migrated content stays discoverable, auditable and defensible after cutover."},
        {"icon": "users", "title": "Business Management", "body": "Programme governance, role-based access design and lifecycle policy management across every repository in scope."},
        {"icon": "megaphone", "title": "Adoption & Enablement", "body": "Change programmes, playbooks and practitioner training that get real users onto the new platform, not just the data."},
        {"icon": "flask", "title": "Usability & Assurance", "body": "Reconciliation harnesses, fidelity testing and usability validation — every object, version and permission verified against source."},
    ],
    "why_heading": {
        "eyebrow": "Why Turnpike",
        "title": "Why teams choose us",
        "description": "The hard trade-offs we solve so your migration lands on time, on budget and audit-clean.",
    },
    "why_choose": [
        {"title": "Budget vs Quality Trade-offs", "body": "Every startup and SMB faces the same tension: building quickly and cheaply creates technical debt that slows you down later. Building perfectly takes too long. We find the exact right balance."},
        {"title": "Finding the Right Technical Partner", "body": "Most early-stage companies lack the internal technical expertise to evaluate what they are being told about technology choices, timelines and estimates. We provide transparent, honest engineering."},
        {"title": "Scaling from MVP to Product", "body": "The architecture that works for your first 100 users often fails at 10,000. Building for scale from day one adds cost. We build modular systems that scale intelligently when you need them to."},
    ],
    "why_cta_label": "Book a discovery call",
    "counters": [
        {"label": "Years Experience", "value": 20, "suffix": "+"},
        {"label": "Countries Covered", "value": 15, "suffix": "+"},
        {"label": "Recent Projects", "value": 140, "suffix": ""},
        {"label": "Succeeded Projects", "value": 3, "suffix": "K+"},
    ],
    "awards_heading": {
        "eyebrow": "Excellence",
        "title": "Recent Awards & Certifications",
        "description": "Recognised by industry leaders for our commitment to quality, security, and innovation.",
    },
    "reviews_heading": {
        "eyebrow": "Read more reviews",
        "title": "Driving technology for leading brands",
        "description": "Programme leaders describe what changed after the migration completed.",
    },
    "insights_heading": {
        "eyebrow": "Insights",
        "title": "From the Turnpike Analyst blog",
        "description": "Field notes on ECM migration, automation and applied AI.",
    },
}


async def main() -> None:
    db_client.connect_db()
    db = get_db()
    await set_homepage(db, HomepageUpdate(**HOMEPAGE))
    logger.info("Homepage CMS document seeded (site_content/_id=homepage).")


if __name__ == "__main__":
    asyncio.run(main())
