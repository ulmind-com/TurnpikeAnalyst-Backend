import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

MIGRATION_DESC = """
<h2>Digital Content Migration Solutions</h2>
<p>Moving petabytes of data securely requires precision, scale, and zero-downtime cutovers. Our JAMES WEBB migration server ensures that metadata, compliance trails, and complex folder structures are faithfully replicated to modern cloud endpoints like AWS or Azure without interrupting business operations.</p>
<p>From legacy ECM systems (FileNet, OpenText, Documentum) to modern architectures, we provide end-to-end extraction, transformation, and checksum validation.</p>
<ul>
<li>PB-Scale Multi-threaded extraction</li>
<li>100% Checksum Verification</li>
<li>Compliance & Audit Trail preservation</li>
</ul>
"""

CAPTURE_DESC = """
<h2>Intelligent Digital Content Capture</h2>
<p>Transform unstructured physical documents and legacy files into actionable, structured data using Cognitive AI and OCR platforms like Kofax.</p>
<p>Our Intelligent Capture services automate document sorting, data extraction, and ERP routing, drastically reducing manual data entry and human error. We integrate seamlessly with SAP, Oracle, and your core business systems to make information instantly available.</p>
<ul>
<li>Cognitive OCR and Handwriting Recognition</li>
<li>Automated Invoice & PO matching</li>
<li>Seamless ERP Integration</li>
</ul>
"""

MANAGED_DESC = """
<h2>24/7 Managed Content Services</h2>
<p>Maintain peak performance for your enterprise content management systems with our proactive Managed Services. We provide round-the-clock monitoring, patch management, and SLA-driven support to ensure maximum uptime.</p>
<p>Let our specialized L2 and L3 support teams handle the infrastructure so your internal IT can focus on driving strategic business value. We offer customized SLAs tailored to your mission-critical applications.</p>
<ul>
<li>Proactive System Monitoring & Tuning</li>
<li>ITIL-aligned Incident Management</li>
<li>Disaster Recovery & Backup Validation</li>
</ul>
"""

SERVICES = [
    {
        "title": "Digital Content Migration",
        "slug": "digital-content-migration",
        "parent_category": "DIGITAL_CONTENT_SERVICES",
        "sub_service_type": "CONSULTING",
        "short_description": "PB-scale, zero-downtime legacy ECM migrations to the cloud.",
        "full_description": MIGRATION_DESC,
        "supported_platforms": ["AWS", "Azure", "FileNet", "OpenText"],
        "is_featured": True,
    },
    {
        "title": "Digital Content Capture",
        "slug": "digital-content-capture",
        "parent_category": "DIGITAL_CONTENT_SERVICES",
        "sub_service_type": "IMPLEMENTATION",
        "short_description": "Cognitive AI OCR to digitize unstructured documents seamlessly.",
        "full_description": CAPTURE_DESC,
        "supported_platforms": ["Kofax", "ABBYY", "SAP"],
        "is_featured": True,
    },
    {
        "title": "Managed Services",
        "slug": "managed-services",
        "parent_category": "DIGITAL_CONTENT_SERVICES",
        "sub_service_type": "MANAGED_SERVICES",
        "short_description": "24/7 proactive monitoring and SLA-driven ECM support.",
        "full_description": MANAGED_DESC,
        "supported_platforms": ["ITIL", "ServiceNow"],
        "is_featured": False,
    }
]

from dotenv import load_dotenv
load_dotenv()

async def main():
    print("Connecting to database...")
    url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DATABASE_NAME", "turnpike_analyst")
    client = AsyncIOMotorClient(url)
    db = client[db_name]

    print("Deleting old DIGITAL_CONTENT_SERVICES...")
    await db.services.delete_many({"parent_category": "DIGITAL_CONTENT_SERVICES"})

    print("Inserting new unique services...")
    for service in SERVICES:
        await db.services.insert_one(service)
        print(f"Inserted: {service['title']}")

    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
