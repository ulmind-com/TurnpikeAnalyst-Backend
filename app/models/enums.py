from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CONSULTANT = "CONSULTANT"
    INSTRUCTOR = "INSTRUCTOR"
    CLIENT = "CLIENT"

class ParentCategory(str, Enum):
    APPLICATIONS = "APPLICATIONS"
    ARTIFICIAL_AUGMENTED_INTELLIGENCE = "ARTIFICIAL_AUGMENTED_INTELLIGENCE"
    BUSINESS_PROCESS = "BUSINESS_PROCESS"
    BUSINESS_SOLUTIONS = "BUSINESS_SOLUTIONS"
    CLOUD = "CLOUD"
    CONSULTING = "CONSULTING"
    CYBERSECURITY = "CYBERSECURITY"
    DATA_ANALYTICS = "DATA_ANALYTICS"
    DESIGN_EXPERIENCE = "DESIGN_EXPERIENCE"
    DIGITAL_MARKETING_INTERACTION = "DIGITAL_MARKETING_INTERACTION"
    ENGINEERING = "ENGINEERING"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    SUSTAINABILITY = "SUSTAINABILITY"
    TALENT_CLOUD = "TALENT_CLOUD"
    DIGITAL_CONTENT_SERVICES = "DIGITAL_CONTENT_SERVICES"
    SERVICES_LOWER = "services"
    INDUSTRIES_LOWER = "industries"
    DIGITAL_CONTENT_SERVICES_LOWER = "digital content services"

class SubServiceType(str, Enum):
    DIGITAL_CONTENT_MIGRATION = "DIGITAL_CONTENT_MIGRATION"
    DIGITAL_CONTENT_CAPTURE = "DIGITAL_CONTENT_CAPTURE"
    MANAGED_SERVICES = "MANAGED_SERVICES"
    SOFTWARE_SUPPORT = "SOFTWARE_SUPPORT"
    BPM_RPA = "BPM_RPA"
    CRM_ERP_INTEGRATION = "CRM_ERP_INTEGRATION"
    SEO_MARKETING = "SEO_MARKETING"
    CUSTOM_ENGINEERING = "CUSTOM_ENGINEERING"
    CORE_OFFERING = "Core Offering"
    STRATEGIC_ADVISORY = "STRATEGIC_ADVISORY"

class ProductCode(str, Enum):
    JAMES_WEBB = "JAMES_WEBB"
    AGENT_P8 = "AGENT_P8"

class LeadType(str, Enum):
    BOOK_CALL = "BOOK_CALL"
    REQUIREMENT_FORM = "REQUIREMENT_FORM"
    PRODUCT_DEMO = "PRODUCT_DEMO"

class Department(str, Enum):
    TECHNICAL_TEAM = "TECHNICAL_TEAM"
    MANAGEMENT_TEAM = "MANAGEMENT_TEAM"
    HELP_DESK = "HELP_DESK"

class LeadStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"

class CourseCategory(str, Enum):
    ECM_TRAINING = "ECM_TRAINING"
    OCP_TRAINING = "OCP_TRAINING"
    CLOUD_DEVOPS = "CLOUD_DEVOPS"
    AI_ML_TRAINING = "AI_ML_TRAINING"

class CourseLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"

class ApplicationStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class TrackCategory(str, Enum):
    """Discipline an internship project belongs to."""
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    FULLSTACK = "FULLSTACK"
    DATA_ENGINEERING = "DATA_ENGINEERING"
    DEVOPS = "DEVOPS"
    AI_ML = "AI_ML"


class EnrollmentMode(str, Enum):
    """Where the project came from.

    The programme accepts both: a brief we published, or one the intern
    proposes themselves. The client's own wording is "you can choose
    project/technology of your own choice", and a catalogue still helps the
    interns who do not yet know what to build.
    """
    TRACK = "TRACK"
    OWN = "OWN"


class InternshipStatus(str, Enum):
    """Lifecycle of one intern's attempt at one track.

    The order below is the order a successful attempt moves through:
    the intern enrols, builds, submits a repository, the review service
    reads it and raises follow-up questions, the intern answers, and a
    human makes the final call.
    """
    ENROLLED = "ENROLLED"
    SUBMITTED = "SUBMITTED"
    AI_REVIEWING = "AI_REVIEWING"
    QUESTIONS_PENDING = "QUESTIONS_PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    # The build window closed before anything was submitted.
    EXPIRED = "EXPIRED"
    # The automated review could not run; an admin has to look at it.
    REVIEW_FAILED = "REVIEW_FAILED"


class BlogCategory(str, Enum):
    UNCATEGORIZED = "UNCATEGORIZED"
    ICC = "ICC"
    KOFAX = "KOFAX"
    HYLAND = "HYLAND"
    AI_INNOVATION = "AI_INNOVATION"
