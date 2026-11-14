from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Default used only when SECRET_KEY is absent from the environment. Any
# deployment reaching users must set a real value; see .env.example.
_INSECURE_DEV_SECRET = "insecure-local-development-key-do-not-deploy"


class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "turnpike_analyst"
    SECRET_KEY: str = _INSECURE_DEV_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Origins permitted to call the API with credentials. Comma-separated in
    # the environment; never widened to a wildcard, because the API answers
    # cookie- and token-authenticated requests.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Optional Google sign-in. When the file is missing the API still serves
    # every other route; only /api/v1/auth/google is unavailable.
    FIREBASE_CREDENTIALS_PATH: str = "firebase_service_account.json"
    # For platforms with env vars but no filesystem to upload to (Render).
    # The whole service account JSON, as one value.
    FIREBASE_CREDENTIALS_JSON: str = ""

    # --- First administrator -------------------------------------------
    # Seeded once, at first startup, so a fresh deployment has a way in.
    # After that the account is managed from the console and these values
    # are ignored — changing them here will NOT change a live password.
    SUPER_ADMIN_EMAIL: str = ""
    SUPER_ADMIN_PASSWORD: str = ""
    SUPER_ADMIN_NAME: str = "Platform Administrator"

    # --- Internship programme ---------------------------------------------
    # Raises the GitHub API rate limit from 60/hour to 5000/hour. Only public
    # repositories are read, so a token with no scopes is sufficient.
    GITHUB_TOKEN: str = ""

    # --- Automated review ---------------------------------------------------
    # An ordered, comma-separated chain. Each submission tries the first
    # provider that has a key; if it errors or is rate limited, the next one
    # is tried. Only when every provider in the chain fails is the attempt
    # parked in REVIEW_FAILED for a human — one vendor having a bad day
    # should not cost an intern their review.
    AI_REVIEW_PROVIDERS: str = "openrouter,groq,openai,gemini,anthropic"
    # Per-provider model override; blank uses the default in ai_review.py.
    AI_REVIEW_MODEL: str = ""

    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # --- Support chatbot ----------------------------------------------------
    # Groq is fast and free-tier friendly, which suits an interactive widget
    # where latency is visible to the person typing.
    GROQ_API_KEY: str = ""
    # Blank on purpose. A model name is vendor-specific, and an override
    # applies to the first provider in the chain — naming one here would
    # hand Groq's id to whichever provider happens to be first.
    CHATBOT_MODEL: str = ""
    # No Gemini here: its free tier takes minutes, which a chat widget cannot wait for.
    CHATBOT_PROVIDERS: str = "groq,openrouter,openai"

    # --- Cloudinary ---------------------------------------------------------
    # Render's filesystem is ephemeral: anything written to disk is gone on
    # the next deploy. Certificates and uploaded diagrams therefore live in
    # Cloudinary, not on the instance.
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # --- S3-compatible archive storage (Supabase Storage, R2, MinIO, …) -----
    # Cloudinary's raw free tier caps a single file at 10 MB. Larger project
    # zips go to any S3-compatible bucket instead of Render's ephemeral disk,
    # so they survive until the admin's decision deletes them. When unset,
    # uploads fall back to Cloudinary/local exactly as before. Endpoint is the
    # provider's S3 endpoint, e.g. https://<ref>.storage.supabase.co/storage/v1/s3
    ARCHIVE_S3_ENDPOINT: str = ""
    ARCHIVE_S3_REGION: str = "auto"
    ARCHIVE_S3_BUCKET: str = ""
    ARCHIVE_S3_ACCESS_KEY_ID: str = ""
    ARCHIVE_S3_SECRET_ACCESS_KEY: str = ""

    # --- Resend Transactional Email ----------------------------------------
    # Sends branded notification emails: welcome/account created, internship
    # enrolled, AI review questions ready, and certificate issued.
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "Turnpike Analyst <noreply@turnpikeanalyst.com>"
    SITE_PUBLIC_URL: str = "https://www.turnpikeanalyst.com"

    @property
    def review_provider_chain(self) -> list[str]:
        return [name.strip().lower() for name in self.AI_REVIEW_PROVIDERS.split(",") if name.strip()]

    @property
    def chatbot_provider_chain(self) -> list[str]:
        return [name.strip().lower() for name in self.CHATBOT_PROVIDERS.split(",") if name.strip()]

    @property
    def cloudinary_configured(self) -> bool:
        return bool(
            self.CLOUDINARY_CLOUD_NAME
            and self.CLOUDINARY_API_KEY
            and self.CLOUDINARY_API_SECRET
        )

    @property
    def archive_s3_configured(self) -> bool:
        return bool(
            self.ARCHIVE_S3_ENDPOINT
            and self.ARCHIVE_S3_BUCKET
            and self.ARCHIVE_S3_ACCESS_KEY_ID
            and self.ARCHIVE_S3_SECRET_ACCESS_KEY
        )

    # Certificate backgrounds and rendered PDFs. Mounted read-only at
    # /uploads, so everything in here is world-readable to anyone with the
    # URL. Certificate filenames are unguessable by design.
    UPLOAD_DIR: str = "uploads"

    # Intern-uploaded diagrams. Deliberately NOT under UPLOAD_DIR: these are
    # served only through an authenticated route that checks ownership, and
    # a file under the static mount would be reachable without any check.
    PRIVATE_UPLOAD_DIR: str = "private_uploads"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def secret_key_is_insecure_default(self) -> bool:
        return self.SECRET_KEY == _INSECURE_DEV_SECRET

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
