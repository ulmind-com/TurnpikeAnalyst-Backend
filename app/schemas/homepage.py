"""Homepage CMS content.

The public marketing homepage is assembled from a single editable document
(`site_content` collection, `_id = "homepage"`). Every section below is
optional with a sensible default, so a partially-filled document — or a brand
new one — always renders, and the admin editor can grow a section at a time.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CTA(BaseModel):
    label: str = ""
    href: str = ""


class HeroTile(BaseModel):
    tag: str = ""
    type: str = "solid"  # "solid" | "photo"
    bg: Optional[str] = None
    img: Optional[str] = None


class HeroSection(BaseModel):
    badge: str = "ENTERPRISE ARCHIVE & AUTOMATION"
    title_lines: List[str] = Field(default_factory=lambda: ["We Are Solution", "Oriented"])
    highlight_word: str = "Digital"
    title_suffix: str = "Agency"
    subtitle: str = (
        "Enterprise content migration, intelligent automation and "
        "practitioner-led engineering — purpose-built for regulated "
        "organisations that cannot afford to lose a single record."
    )
    primary_cta: CTA = Field(default_factory=lambda: CTA(label="Get Started", href="#contact"))
    secondary_cta: CTA = Field(default_factory=lambda: CTA(label="How It Works", href="#services"))
    tiles: List[HeroTile] = Field(default_factory=list)


class HeroClaim(BaseModel):
    title: str = ""
    body: str = ""


class PlatformStats(BaseModel):
    service_label: str = "Service capabilities"
    product_label: str = "Platform products"
    product_value: int = 2
    course_label: str = "Academy courses"


class TechStackGroup(BaseModel):
    category: str = ""
    items: List[str] = Field(default_factory=list)


class SectionHeading(BaseModel):
    eyebrow: str = ""
    title: str = ""
    description: str = ""


class Capability(BaseModel):
    icon: str = ""
    title: str = ""
    body: str = ""


class FlagshipBullet(BaseModel):
    title: str = ""
    body: str = ""


class Flagship(BaseModel):
    id: str = ""
    eyebrow: str = ""
    title: str = ""
    body: str = ""
    bullets: List[FlagshipBullet] = Field(default_factory=list)
    cta: str = ""
    image: str = ""
    gradient: str = ""
    badge_icon: str = ""
    badge_color: str = ""
    tags: List[str] = Field(default_factory=list)
    metric: str = ""
    metric_label: str = ""


class WhyChooseItem(BaseModel):
    title: str = ""
    body: str = ""
    image: str = ""


class Counter(BaseModel):
    label: str = ""
    value: float = 0
    suffix: str = ""


class IndustryCard(BaseModel):
    title: str = ""
    body: str = ""
    image: str = ""


class HomepageContent(BaseModel):
    """The full editable homepage. All fields optional → always renders."""

    hero: HeroSection = Field(default_factory=HeroSection)
    hero_claims: List[HeroClaim] = Field(default_factory=list)
    platform_stats: PlatformStats = Field(default_factory=PlatformStats)

    tech_heading: SectionHeading = Field(default_factory=SectionHeading)
    tech_stack: List[TechStackGroup] = Field(default_factory=list)

    services_heading: SectionHeading = Field(default_factory=SectionHeading)
    industries_heading: SectionHeading = Field(default_factory=SectionHeading)
    industries_lead_text: str = ""
    consultants_heading: SectionHeading = Field(default_factory=SectionHeading)

    flagships: List[Flagship] = Field(default_factory=list)
    capabilities: List[Capability] = Field(default_factory=list)

    why_heading: SectionHeading = Field(default_factory=SectionHeading)
    why_choose: List[WhyChooseItem] = Field(default_factory=list)
    why_cta_label: str = "Book a discovery call"

    counters: List[Counter] = Field(default_factory=list)

    awards_heading: SectionHeading = Field(default_factory=SectionHeading)
    reviews_heading: SectionHeading = Field(default_factory=SectionHeading)
    insights_heading: SectionHeading = Field(default_factory=SectionHeading)

    # Controls the order and visibility of the main homepage blocks.
    section_order: List[str] = Field(default_factory=lambda: ["hero", "stats", "technology", "services", "industries", "flagships", "consultants", "why", "awards", "reviews", "insights", "capabilities", "counters"])
    hidden_sections: List[str] = Field(default_factory=lambda: ["capabilities", "counters"])

    industries: List[IndustryCard] = Field(default_factory=lambda: [
        IndustryCard(title="Healthcare & Life Sciences", body="FDA 21 CFR Part 11 and HIPAA compliant data pipelines, automated clinical trial master files, and validated GxP audit trails."),
        IndustryCard(title="Fintech & Banking", body="SEC Rule 17a-4 and SOC2 Type II immutable WORM storage, sub-millisecond transaction archiving, and cryptographic audit ledgers."),
        IndustryCard(title="Energy & Utilities", body="NERC CIP critical infrastructure protection, SCADA sensor telemetry vaults, and sub-second CAD/BIM drawing distribution."),
        IndustryCard(title="Aerospace & Defense", body="ITAR export control boundary enforcement, air-gapped GovCloud architectures, and CMMC Level 3 certification readiness."),
        IndustryCard(title="Logistics & Global Supply", body="Electronic Bill of Lading orchestration, automated customs declaration workflows, and real-time multimodal container tracking."),
    ])


class HomepageUpdate(HomepageContent):
    """Admin PUT body — identical shape; the whole document is replaced."""

    pass


class ImageUploadResponse(BaseModel):
    url: str
    key: str
