import asyncio
import logging
from app.db.mongodb import db_client, get_db
from app.models.enums import (
    UserRole, ParentCategory, SubServiceType, 
    CourseCategory, CourseLevel, BlogCategory
)
from app.schemas.user import UserCreate
from app.schemas.service import ServiceCreate
from app.schemas.training import CourseCreate
from app.schemas.blog import BlogCreate
from app.crud.user import get_user_by_email, create_user, ensure_user_indexes
from app.crud.service import get_service_by_slug, create_service, ensure_service_indexes
from app.crud.training import get_course_by_slug, create_course, ensure_training_indexes
from app.crud.blog import get_blog_by_slug, create_blog, ensure_blog_indexes
from app.schemas.content import TestimonialCreate, AwardCreate, StatCreate
from app.crud.content import create_testimonial, create_award, create_stat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_data")

async def seed():
    logger.info("Initializing database connection for data seeding...")
    db_client.connect_db()
    db = get_db()
    
    # Ensure indexes
    await ensure_user_indexes(db)
    await ensure_service_indexes(db)
    await ensure_training_indexes(db)
    await ensure_blog_indexes(db)
    
    # 1. Seed Admin User & Standard Roles
    logger.info("Checking & seeding default Admin user...")
    admin_email = "admin@turnpikeanalyst.com"
    existing_admin = await get_user_by_email(db, admin_email)
    if not existing_admin:
        admin_user = UserCreate(
            full_name="Platform Administrator",
            email=admin_email,
            phone="+1-800-555-0199",
            password="AdminPass123!",
            company="Turnpike Analyst",
            role=UserRole.ADMIN
        )
        await create_user(db, admin_user, role=UserRole.ADMIN)
        logger.info(f"Created Admin User: {admin_email}")
    else:
        logger.info(f"Admin User {admin_email} already exists.")

    consultant_email = "consultant@turnpikeanalyst.com"
    if not await get_user_by_email(db, consultant_email):
        await create_user(db, UserCreate(
            full_name="Enterprise ECM Consultant",
            email=consultant_email,
            password="ConsultantPass123!",
            company="Turnpike Analyst Consulting Group",
            role=UserRole.CONSULTANT
        ), role=UserRole.CONSULTANT)
        logger.info(f"Created Consultant User: {consultant_email}")

    # 2. Seed All Dropdown Service Categories & Sub-Services (15 Categories covered)
    logger.info("Seeding comprehensive Enterprise Service catalog...")
    services_data = [
        ServiceCreate(
            title="Enterprise FileNet to Cloud Digital Content Migration",
            slug="filenet-to-cloud-migration",
            parent_category=ParentCategory.DIGITAL_CONTENT_SERVICES,
            sub_service_type=SubServiceType.DIGITAL_CONTENT_MIGRATION,
            short_description="High-speed, petabyte-scale content migration from legacy on-prem FileNet and Documentum repositories to cloud storage using JAMES WEBB.",
            full_description="Our proprietary migration methodology eliminates operational downtime while migrating unstructured data, workflows, and complex metadata structures to AWS, Azure, and OpenShift architectures.",
            supported_platforms=["FileNet", "OpenText Documentum", "SharePoint", "AWS S3", "Azure Blob"],
            is_featured=True,
            sections=[
                {
                    "heading": "",
                    "text": "Turnpike Analyst understands the challenges of migrating and consolidating large volumes of documents from on-premise systems to the cloud. Whether you’re looking to replace an expensive, difficult-to-maintain legacy system or seeking a seamless transition from on-premises solutions to the cloud, our migration platform streamlines the entire process. With our comprehensive mechanism, we ensure the success of your legacy modernization project at speed."
                },
                {
                    "heading": "Efficient and Secure Mass Migrations",
                    "text": "Turnpike Analyst’s migration solution enables you to quickly migrate and consolidate billions of documents while significantly reducing processing times. Our platform ensures the security and consistency of your data, without the risk of data loss. With our expertise, you can seamlessly move content and data between a wide range of leading business applications and ECM systems in a matter of days."
                },
                {
                    "heading": "Meet Complex Business Requirements with Ease",
                    "text": "Choose from our catalog of over 100 tasks to easily map data, eliminating the need for heavy coding or custom scripts. Our migration platform leverages a standard API, allowing for simple configuration of custom tasks to meet even the most complex business requirements. With our solution, you can accelerate your legacy transformation without compromising on quality or precision."
                },
                {
                    "heading": "Streamline Legacy Transformation",
                    "text": "Our migration platform simplifies the process by seamlessly managing the transfer of files, metadata, version history, and permissions. We ensure that you get the most out of your new cloud-based system. Built-in insights provide real-time optimization, minimizing the impact on your business operations. With our solution, you can migrate millions of files per day, migrate content, keywords, versions, permissions, users, and annotations, and convert large volumes of files from one format to another."
                },
                {
                    "heading": "Support for Various Source Systems",
                    "text": "Our migration solution offers flexibility by allowing you to migrate from any source system. Whether it’s content repositories, business applications, network drives, emails, or more, our platform can handle it all. Choose from a catalog of pre-configured templates or build your own connectors to ensure a seamless transition. You can also configure custom rules to migrate content over time or as needed, giving you full control over the migration process."
                },
                {
                    "heading": "Track Progress and Ensure Data Security",
                    "text": "With our migration solution, you can easily track activity and monitor migration progress with advanced reports. Our built-in insights provide intelligent assessments, enabling you to make data-driven decisions throughout the migration process. We prioritize data security and content integrity, ensuring that your valuable information is safeguarded throughout the migration journey."
                },
                {
                    "heading": "",
                    "text": "Turnpike Analyst is committed to simplifying your legacy modernization journey. With our migration platform, you can quickly and securely migrate and consolidate billions of documents from on-premise to the cloud. Our comprehensive solution empowers your organization to embrace modern technologies, optimize data management, and unlock the full potential of the cloud."
                },
                {
                    "heading": "",
                    "text": "Book a consultation with our experts today to embark on a streamlined legacy modernization journey with Turnpike Analyst."
                }
            ]
        ),
        ServiceCreate(
            title="Cognitive Intelligent Document Capture with Kofax & AI",
            slug="cognitive-capture-kofax",
            parent_category=ParentCategory.DIGITAL_CONTENT_SERVICES,
            sub_service_type=SubServiceType.DIGITAL_CONTENT_CAPTURE,
            short_description="AI-enhanced high-volume ingestion and OCR data extraction leveraging Kofax TotalAgility and IBM watsonx neural engines.",
            full_description="Transform unstructured invoices, legal agreements, and corporate filings into actionable database records with automated classification and anomaly detection.",
            supported_platforms=["Kofax", "Hyland OnBase", "IBM watsonx", "FileNet"],
            is_featured=True
        ),
        ServiceCreate(
            title="Managed ECM Infrastructure Support & 24/7 SLA Monitoring",
            slug="managed-ecm-infrastructure-support",
            parent_category=ParentCategory.INFRASTRUCTURE,
            sub_service_type=SubServiceType.MANAGED_SERVICES,
            short_description="Dedicated infrastructure operations, container tuning, and proactive health diagnostics for enterprise content clusters.",
            full_description="Ensure 99.999% uptime for core enterprise content platforms across Red Hat OpenShift, Kubernetes, and hybrid multi-cloud environments.",
            supported_platforms=["Red Hat OpenShift", "AWS", "Azure", "IBM FileNet", "Kubernetes"],
            is_featured=False
        ),
        ServiceCreate(
            title="Enterprise Software Application Maintenance & SLAs",
            slug="enterprise-software-support",
            parent_category=ParentCategory.APPLICATIONS,
            sub_service_type=SubServiceType.SOFTWARE_SUPPORT,
            short_description="Custom API support, legacy module debugging, and continuous integration upgrades for SharePoint, AEM, and Documentum deployments.",
            full_description="Receive rapid resolution from certified content architects and senior backend engineers with guaranteed 8-hour reply SLA tracking.",
            supported_platforms=["SharePoint", "AEM", "OpenText Documentum", "Hyland OnBase"],
            is_featured=False
        ),
        ServiceCreate(
            title="Business Process Management & RPA Intelligent Workflow Automation",
            slug="bpm-rpa-process-automation",
            parent_category=ParentCategory.BUSINESS_PROCESS,
            sub_service_type=SubServiceType.BPM_RPA,
            short_description="Automate repetitive operational tasks, loan processing, and claim routing with robotic process automation and AI decisioning.",
            full_description="We unify IBM FileNet Workflow engines with enterprise RPA tools to orchestrate seamless end-to-end processing across banking and healthcare departments.",
            supported_platforms=["IBM watsonx", "FileNet Workflow", "UiPath", "Blue Prism", "Kofax RPA"],
            is_featured=True
        ),
        ServiceCreate(
            title="Enterprise CRM & ERP Bi-Directional Content Integration",
            slug="crm-erp-enterprise-integration",
            parent_category=ParentCategory.BUSINESS_SOLUTIONS,
            sub_service_type=SubServiceType.CRM_ERP_INTEGRATION,
            short_description="Bridge data silos between SAP, Oracle ERP, Salesforce CRM, and enterprise ECM repositories for real-time document sync.",
            full_description="Embed secure document archival, retrieval, and signature workflows directly into accounting and customer service dashboard screens.",
            supported_platforms=["SAP", "Salesforce", "Oracle ERP", "Hyland OnBase", "FileNet"],
            is_featured=False
        ),
        ServiceCreate(
            title="SEO Marketing & Omnichannel Brand Interaction Strategy",
            slug="seo-digital-marketing-strategy",
            parent_category=ParentCategory.DIGITAL_MARKETING_INTERACTION,
            sub_service_type=SubServiceType.SEO_MARKETING,
            short_description="Data-driven technical SEO, core web vitals optimization, and digital interaction analytics for corporate web portals.",
            full_description="Maximize global enterprise visibility and lead conversions by combining technical site architecture mastery with Adobe Experience Manager (AEM) delivery.",
            supported_platforms=["AEM", "Google Analytics", "Adobe Analytics", "FastAPI"],
            is_featured=False
        ),
        ServiceCreate(
            title="Custom Cloud Microservices & Distributed Engineering",
            slug="custom-cloud-microservices-engineering",
            parent_category=ParentCategory.ENGINEERING,
            sub_service_type=SubServiceType.CUSTOM_ENGINEERING,
            short_description="Tailored cloud-native REST APIs, event-driven architectures, and Python/FastAPI enterprise service buses.",
            full_description="Build secure, scalable backends designed for high throughput, low latency, and robust horizontal auto-scaling across AWS and Azure container fabrics.",
            supported_platforms=["AWS", "Azure", "OpenShift", "Kubernetes", "FastAPI", "MongoDB"],
            is_featured=True
        ),
        ServiceCreate(
            title="Watsonx AI & Augmented Intelligence Enterprise Transformation",
            slug="watsonx-ai-augmented-intelligence-consulting",
            parent_category=ParentCategory.ARTIFICIAL_AUGMENTED_INTELLIGENCE,
            sub_service_type=SubServiceType.CUSTOM_ENGINEERING,
            short_description="Deploy governed generative AI, RAG pipelines, and specialized LLM agents securely inside your corporate perimeter using Agent P8.",
            full_description="Harness IBM watsonx to synthesize proprietary historical documents without exposing intellectual property to public model vendors.",
            supported_platforms=["IBM watsonx", "Agent P8", "LangChain", "OpenAI", "PyTorch"],
            is_featured=True
        ),
        ServiceCreate(
            title="Cloud Transformation & Multi-Cloud Governance Consulting",
            slug="cloud-transformation-consulting",
            parent_category=ParentCategory.CLOUD,
            sub_service_type=SubServiceType.MANAGED_SERVICES,
            short_description="Strategic architecture roadmaps, cost optimization, and safe cloud migration planning for Fortune 500 infrastructure.",
            full_description="Our enterprise fellows evaluate legacy workloads, build comprehensive ROI analyses, and execute step-by-step hybrid cloud implementations.",
            supported_platforms=["AWS", "Azure", "Google Cloud", "RedHat OpenShift"],
            is_featured=False
        ),
        ServiceCreate(
            title="Executive Technology Architecture & Compliance Consulting",
            slug="executive-governance-consulting",
            parent_category=ParentCategory.CONSULTING,
            sub_service_type=SubServiceType.MANAGED_SERVICES,
            short_description="C-suite IT strategy, software procurement auditing, and enterprise architecture modernization consulting.",
            full_description="Align technical execution with long-term financial growth through formalized TOGAF and ITIL framework reviews.",
            supported_platforms=["Enterprise Architecture", "COBIT", "ITIL", "TOGAF"],
            is_featured=False
        ),
        ServiceCreate(
            title="Zero-Trust Cybersecurity & Regulatory Compliance Shielding",
            slug="zero-trust-cybersecurity-compliance",
            parent_category=ParentCategory.CYBERSECURITY,
            sub_service_type=SubServiceType.SOFTWARE_SUPPORT,
            short_description="End-to-end repository encryption, IAM zero-trust enforcement, and automated audit trails for GDPR, HIPAA, and SEC compliance.",
            full_description="Protect sensitive unstructured records from ransomware and internal leaks with continuous intrusion monitoring and role-based cryptographic access.",
            supported_platforms=["Palo Alto", "CrowdStrike", "AWS IAM", "Azure AD", "FileNet Security"],
            is_featured=False
        ),
        ServiceCreate(
            title="Advanced Enterprise Data Analytics & Content BI Platforms",
            slug="advanced-data-analytics-bi",
            parent_category=ParentCategory.DATA_ANALYTICS,
            sub_service_type=SubServiceType.CUSTOM_ENGINEERING,
            short_description="Unify structured database warehouses with unstructured document metadata to power predictive analytical executive dashboards.",
            full_description="We integrate Snowflake, Databricks, and PowerBI with enterprise content engines to reveal real-time business operational metrics.",
            supported_platforms=["Snowflake", "Databricks", "PowerBI", "Tableau", "MongoDB"],
            is_featured=False
        ),
        ServiceCreate(
            title="Omnichannel UI/UX Design & Customer Experience Architecture (AEM)",
            slug="ui-ux-omnichannel-experience",
            parent_category=ParentCategory.DESIGN_EXPERIENCE,
            sub_service_type=SubServiceType.CUSTOM_ENGINEERING,
            short_description="World-class user interface design, design system tokenization, and dynamic customer portals built on Adobe Experience Manager.",
            full_description="Deliver breathtaking, highly responsive web experiences that delight clients and maximize conversion across mobile and desktop breakpoints.",
            supported_platforms=["Figma", "Adobe Experience Manager (AEM)", "React", "Next.js", "FastAPI"],
            is_featured=False
        ),
        ServiceCreate(
            title="Sustainable IT & Green Datacenter Footprint Optimization",
            slug="sustainable-it-green-datacenter",
            parent_category=ParentCategory.SUSTAINABILITY,
            sub_service_type=SubServiceType.MANAGED_SERVICES,
            short_description="Reduce server carbon footprint, optimize cloud compute resource allocation, and implement verifiable green IT sustainability reporting.",
            full_description="Meet ESG corporate mandates by migrating inefficient on-prem legacy hardware to carbon-neutral solar/wind powered cloud nodes.",
            supported_platforms=["Green Cloud", "Carbon Footprint Monitoring", "AWS Sustainability Hub"],
            is_featured=False
        ),
        ServiceCreate(
            title="Talent Cloud On-Demand ECM & AI Specialist Staff Augmentation",
            slug="talent-cloud-staffing-augmentation",
            parent_category=ParentCategory.TALENT_CLOUD,
            sub_service_type=SubServiceType.MANAGED_SERVICES,
            short_description="Direct access to top 1% certified IBM FileNet architects, OpenShift engineers, and watsonx AI developers for your project teams.",
            full_description="Scale your implementation capability overnight with vetted senior engineering leaders embedded directly within your agile scrum methodology.",
            supported_platforms=["Certified IBM Experts", "AWS Certified Solutions Architects", "ECM Developers"],
            is_featured=True
        )
    ]
    for s_in in services_data:
        if not await get_service_by_slug(db, s_in.slug):
            await create_service(db, s_in)
            logger.info(f"Seeded Service: {s_in.title}")

    # 4. Seed Sample Training Courses & CMS Articles
    logger.info("Seeding Training Courses and CMS Articles...")
    courses_data = [
        CourseCreate(
            title="IBM FileNet P8 Architecture & Advanced ECM Mastery",
            slug="filenet-p8-architecture-mastery",
            category=CourseCategory.ECM_TRAINING,
            duration_hours=40,
            level=CourseLevel.ADVANCED,
            price=1499.00,
            curriculum=[
                {"module": 1, "title": "FileNet Content Engine & Object Store Topology", "duration": "10h"},
                {"module": 2, "title": "Process Engine Advanced Workflow Customization", "duration": "15h"},
                {"module": 3, "title": "High-Speed Migrations using JAMES WEBB Server", "duration": "15h"}
            ],
            is_published=True
        ),
        CourseCreate(
            title="Red Hat OpenShift (OCP) Containerization for Enterprise ECM",
            slug="openshift-ocp-containerization-training",
            category=CourseCategory.OCP_TRAINING,
            duration_hours=32,
            level=CourseLevel.INTERMEDIATE,
            price=1299.00,
            curriculum=[
                {"module": 1, "title": "Kubernetes Architecture & OpenShift Operators", "duration": "16h"},
                {"module": 2, "title": "Deploying ECM Containers on OCP & Persistent Storage", "duration": "16h"}
            ],
            is_published=True
        ),
        CourseCreate(
            title="AI & ML Enterprise Document Automation with Watsonx & Agent P8",
            slug="ai-ml-document-automation-watsonx",
            category=CourseCategory.AI_ML_TRAINING,
            duration_hours=24,
            level=CourseLevel.ADVANCED,
            price=1899.00,
            curriculum=[
                {"module": 1, "title": "Cognitive OCR Capture & Neural Embedding Pipelines", "duration": "12h"},
                {"module": 2, "title": "Building Autonomous Agents with Agent P8 Toolkit", "duration": "12h"}
            ],
            is_published=True
        )
    ]
    for c_in in courses_data:
        if not await get_course_by_slug(db, c_in.slug):
            await create_course(db, c_in)
            logger.info(f"Seeded Course: {c_in.title}")

    articles_data = [
        BlogCreate(
            title="Modernizing Legacy FileNet Implementations with Zero-Downtime JAMES WEBB Migration",
            slug="modernizing-legacy-filenet-james-webb",
            category=BlogCategory.ICC,
            author="Platform Administrator",
            summary="Discover how Turnpike Analyst helped Global 2000 enterprises transfer over 50 million legacy documents from on-premises IBM FileNet to AWS Cloud without losing a single hour of operational uptime.",
            content_html="<h2>The Enterprise ECM Migration Challenge</h2><p>Legacy repositories create massive data silos that cripple agility and increase infrastructure maintenance costs. When planning an enterprise-wide cloud transformation, traditional export-import methods introduce catastrophic risk and weeks of business downtime.</p><h3>Why Zero-Downtime Matters</h3><p>With our proprietary JAMES WEBB Server, enterprise metadata mapping happens on the fly with real-time delta synchronization, ensuring continuous read/write capability for hospital and financial branch networks during cutover.</p>",
            tags=["FileNet", "JAMES WEBB", "Cloud Migration", "ECM"],
            is_published=True
        ),
        BlogCreate(
            title="Unlocking Cognitive Capture: Transforming Document Ingestion with Kofax and AI",
            slug="unlocking-cognitive-capture-kofax-ai",
            category=BlogCategory.KOFAX,
            author="Enterprise Consulting Team",
            summary="Explore how modern neural networks and Kofax TotalAgility OCR integration empower automated processing of invoices, legal agreements, and unstructured corporate records.",
            content_html="<h2>From Simple OCR to Cognitive Comprehension</h2><p>Traditional capture tools rely heavily on fragile zonal coordinate templates. By embedding advanced neural AI models directly into the ingestion funnel, organizations achieve over 98% touchless extraction accuracy across diverse document layouts.</p>",
            tags=["Kofax", "Cognitive Capture", "AI Innovation", "OCR"],
            is_published=True
        ),
        BlogCreate(
            title="Introducing Agent P8: Autonomous Generative AI for Enterprise ECM Governance",
            slug="introducing-agent-p8-autonomous-ai",
            category=BlogCategory.AI_INNOVATION,
            author="Turnpike Engineering Labs",
            summary="Learn how Agent P8 integrates with IBM watsonx to bring self-governing compliance monitoring, natural language repository synthesis, and automated RPA directly into your IBM FileNet P8 content cluster.",
            content_html="<h2>The Dawn of Autonomous ECM Agents</h2><p>By leveraging enterprise privacy shields in IBM watsonx, Agent P8 operates entirely inside your protected corporate network perimeter. Agents actively audit document retention dates and generate instant executive summaries of 500-page regulatory filings in seconds.</p>",
            tags=["Agent P8", "watsonx", "AI", "FileNet", "Generative AI"],
            is_published=True
        ),
        BlogCreate(
            title="Hyland OnBase Workflow Modernization and ERP Hybrid Connector Strategies",
            slug="hyland-onbase-workflow-erp-connectors",
            category=BlogCategory.HYLAND,
            author="Solutions Consulting Practice",
            summary="Best practices for integrating Hyland OnBase document workflows with SAP and Oracle ERP systems across hybrid cloud and on-premises environments.",
            content_html="<h2>Bridging ECM and ERP Silos</h2><p>Financial and supply chain documentation requires instant two-way synchronization between content stores and transaction engines. Here is our blueprint for scalable hybrid API connector integration.</p>",
            tags=["Hyland", "OnBase", "ERP", "SAP Integration"],
            is_published=True
        )
    ]
    
    existing_blogs = await db.blogs.count_documents({})
    if existing_blogs == 0:
        for b in articles_data:
            if not await get_blog_by_slug(db, b.slug):
                await create_blog(db, b)
        logger.info(f"Seeded {len(articles_data)} CMS Blog Articles.")
    else:
        logger.info("Blogs already seeded, skipping.")

    # 7. Seed Dynamic Content (Testimonials, Awards, Stats)
    logger.info("Seeding dynamic UI content (Testimonials, Awards, Stats)...")
    
    # Check if we already seeded content by checking for any award
    existing_awards = await db.awards.count_documents({})
    if existing_awards == 0:
        # Awards
        awards_data = [
            AwardCreate(title="ECM Modernisation Partner", body="Recognised for large-scale regulated migration delivery."),
            AwardCreate(title="Automation Excellence", body="Awarded for autonomous platform operations with Agent P8."),
            AwardCreate(title="Cloud Transformation", body="Honoured for hybrid and cloud-native ECM programmes."),
            AwardCreate(title="Training Provider of the Year", body="For practitioner-led enablement across enterprise teams.")
        ]
        for a in awards_data: await create_award(db, a)
        
        # Testimonials
        testimonials_data = [
            TestimonialCreate(quote="They moved 40 million objects off Image Services without a single reconciliation exception. The audit team signed off first time.", name="Programme Director", role="Global insurance group"),
            TestimonialCreate(quote="Agent P8 has replaced an entire on-call rota. Incidents get diagnosed and closed before our team even opens the console.", name="Head of Platform Operations", role="Retail banking"),
            TestimonialCreate(quote="The training was the difference. Six weeks after cutover our own people were running the estate end to end.", name="Director of Information Management", role="Public sector agency")
        ]
        for t in testimonials_data: await create_testimonial(db, t)
        
        # Stats (Counters)
        stats_data = [
            StatCreate(label="Years Experience", value="20", suffix="+"),
            StatCreate(label="Countries Covered", value="15", suffix="+"),
            StatCreate(label="Recent Projects", value="140", suffix=""),
            StatCreate(label="Succeeded Projects", value="3", suffix="K+"),
            # Impact Stats
            StatCreate(label="In-house experts", value="50+", suffix=""),
            StatCreate(label="Awards in 20 years", value="500+", suffix=""),
            StatCreate(label="Clients worldwide", value="700+", suffix=""),
            StatCreate(label="Five-star reviews", value="150+", suffix=""),
        ]
        for s in stats_data: await create_stat(db, s)
        
        logger.info("Successfully seeded dynamic UI content.")
    else:
        logger.info("Dynamic UI content already seeded, skipping.")

    logger.info("Database seeding execution completed successfully!")
    db_client.close_db()

if __name__ == "__main__":
    asyncio.run(seed())
