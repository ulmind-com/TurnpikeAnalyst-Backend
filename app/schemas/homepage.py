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


class WhyChooseItem(BaseModel):
    title: str = ""
    body: str = ""


class Counter(BaseModel):
    label: str = ""
    value: float = 0
    suffix: str = ""


class HomepageContent(BaseModel):
    """The full editable homepage. All fields optional → always renders."""

    hero: HeroSection = Field(default_factory=HeroSection)
    hero_claims: List[HeroClaim] = Field(default_factory=list)
    platform_stats: PlatformStats = Field(default_factory=PlatformStats)

    tech_heading: SectionHeading = Field(default_factory=SectionHeading)
    tech_stack: List[TechStackGroup] = Field(default_factory=list)

    services_heading: SectionHeading = Field(default_factory=SectionHeading)
    industries_heading: SectionHeading = Field(default_factory=SectionHeading)

    flagships: List[Flagship] = Field(default_factory=list)
    capabilities: List[Capability] = Field(default_factory=list)

    why_heading: SectionHeading = Field(default_factory=SectionHeading)
    why_choose: List[WhyChooseItem] = Field(default_factory=list)
    why_cta_label: str = "Book a discovery call"

    counters: List[Counter] = Field(default_factory=list)

    awards_heading: SectionHeading = Field(default_factory=SectionHeading)
    reviews_heading: SectionHeading = Field(default_factory=SectionHeading)
    insights_heading: SectionHeading = Field(default_factory=SectionHeading)


class HomepageUpdate(HomepageContent):
    """Admin PUT body — identical shape; the whole document is replaced."""

    pass


class ImageUploadResponse(BaseModel):
    url: str
    key: str
