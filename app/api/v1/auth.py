import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import firebase_admin.auth
from motor.motor_asyncio import AsyncIOMotorDatabase
from jose import JWTError
from app.db.mongodb import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.schemas.auth import (
    Token,
    LoginResponse,
    RefreshTokenRequest,
    FirebaseLoginRequest,
    RegisterCodeRequest,
    RegisterVerifyRequest,
)
from app.crud.user import get_user_by_email, get_user_by_id, create_user
from app.models.enums import UserRole
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.api.deps import get_current_active_user
from app.services.email import send_welcome_email, send_verification_code_email

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    background: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Public self-registration (manual sign-up).

    The role is forced to CLIENT and never taken from the request body. Elevated
    roles require administrative elevation.
    """
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists.")
    user = await create_user(db, user_in, role=UserRole.CLIENT)
    background.add_task(send_welcome_email, user_in.email, user_in.full_name)
    return user


# --------------------------------------------------------------------------
# Email-verified manual sign-up (one-time code)
#
# Two steps so a password is only ever set for an address the person can
# actually receive mail at: request a 6-digit code, then verify it and set a
# password. Codes are stored hashed (never in clear), one per email, expire in
# 10 minutes, and are rate limited and attempt limited.
# --------------------------------------------------------------------------

_CODE_TTL = timedelta(minutes=10)
_CODE_RESEND_COOLDOWN = timedelta(seconds=45)
_CODE_MAX_ATTEMPTS = 5


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _aware(value: Any) -> Any:
    """Mongo may hand back naive datetimes; compare them as UTC."""
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


@router.post("/register/send-code", status_code=status.HTTP_202_ACCEPTED)
async def register_send_code(
    payload: RegisterCodeRequest,
    background: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Step 1: email a one-time verification code for manual sign-up."""
    email = payload.email.strip().lower()
    local, _, domain = email.partition("@")
    if not local or "." not in domain:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    full_name = payload.full_name.strip()
    if not full_name:
        raise HTTPException(status_code=422, detail="Please enter your name.")
    if await get_user_by_email(db, email):
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists. Please sign in instead.",
        )

    now = datetime.now(timezone.utc)
    existing = await db.email_verification_codes.find_one({"_id": email})
    if existing and existing.get("last_sent_at"):
        if now - _aware(existing["last_sent_at"]) < _CODE_RESEND_COOLDOWN:
            raise HTTPException(
                status_code=429,
                detail="Please wait a few seconds before requesting another code.",
            )

    code = _generate_code()
    await db.email_verification_codes.update_one(
        {"_id": email},
        {
            "$set": {
                "code_hash": get_password_hash(code),
                "full_name": full_name,
                "expires_at": now + _CODE_TTL,
                "attempts": 0,
                "last_sent_at": now,
                "purpose": "register",
            }
        },
        upsert=True,
    )
    background.add_task(send_verification_code_email, email, code, full_name)
    return {"sent": True}


@router.post("/register/verify", response_model=LoginResponse)
async def register_verify(
    payload: RegisterVerifyRequest,
    background: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Step 2: verify the code, set the password, create the account, sign in."""
    email = payload.email.strip().lower()
    if len(payload.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters.")

    record = await db.email_verification_codes.find_one({"_id": email})
    if not record:
        raise HTTPException(status_code=400, detail="Request a verification code first.")

    if datetime.now(timezone.utc) > _aware(record.get("expires_at") or datetime.min.replace(tzinfo=timezone.utc)):
        await db.email_verification_codes.delete_one({"_id": email})
        raise HTTPException(status_code=400, detail="Your code has expired. Please request a new one.")

    if record.get("attempts", 0) >= _CODE_MAX_ATTEMPTS:
        await db.email_verification_codes.delete_one({"_id": email})
        raise HTTPException(
            status_code=429, detail="Too many incorrect attempts. Please request a new code."
        )

    if not verify_password(payload.code.strip(), record["code_hash"]):
        await db.email_verification_codes.update_one({"_id": email}, {"$inc": {"attempts": 1}})
        raise HTTPException(status_code=400, detail="That code is incorrect. Please check and try again.")

    # Code is valid — guard against the email being registered in a race.
    if await get_user_by_email(db, email):
        await db.email_verification_codes.delete_one({"_id": email})
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists. Please sign in instead.",
        )

    full_name = (payload.full_name or record.get("full_name") or "").strip() or local_part(email)
    user = await create_user(
        db,
        UserCreate(
            full_name=full_name,
            email=email,
            password=payload.password,
            company=(payload.company.strip() if payload.company and payload.company.strip() else None),
        ),
        role=UserRole.CLIENT,
    )
    await db.email_verification_codes.delete_one({"_id": email})
    background.add_task(send_welcome_email, email, full_name)

    sub = str(user["_id"])
    return {
        "access_token": create_access_token(sub),
        "refresh_token": create_refresh_token(sub),
        "token_type": "bearer",
        "user": user,
    }


def local_part(email: str) -> str:
    return email.split("@", 1)[0]


@router.post("/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    
    sub = str(user["_id"])
    access_token = create_access_token(sub)
    refresh_token = create_refresh_token(sub)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }


async def _handle_firebase_social_auth(
    firebase_token: str,
    provider_label: str,
    background: BackgroundTasks,
    db: AsyncIOMotorDatabase,
) -> Dict[str, Any]:
    if not firebase_admin._apps:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider_label} sign-in is not configured on this server.",
        )

    try:
        decoded_token = firebase_admin.auth.verify_id_token(
            firebase_token, clock_skew_seconds=60
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase {provider_label} token: {exc}")

    email = decoded_token.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No email found in token")

    # Google and Apple verification check
    is_verified = decoded_token.get("email_verified", True)
    if not is_verified:
        raise HTTPException(
            status_code=403, detail=f"Your {provider_label} account email is not verified."
        )

    name = decoded_token.get("name") or email.split("@")[0]
    picture = decoded_token.get("picture")

    user = await get_user_by_email(db, email)
    if not user:
        user = await create_user(
            db,
            UserCreate(
                full_name=name,
                email=email,
                avatar_url=picture,
                password=secrets.token_urlsafe(32),
            ),
            role=UserRole.CLIENT,
        )
        background.add_task(send_welcome_email, email, name)
    elif picture and not user.get("avatar_url"):
        # Update user avatar if Google/Apple returns one and user has none
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"avatar_url": picture}})
        user["avatar_url"] = picture

    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
        
    sub = str(user["_id"])
    access_token = create_access_token(sub)
    refresh_token = create_refresh_token(sub)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/google", response_model=LoginResponse)
async def login_with_google(
    request: FirebaseLoginRequest,
    background: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Google sign-in and automated client onboarding."""
    return await _handle_firebase_social_auth(
        request.firebase_token, "Google", background, db
    )


@router.post("/apple", response_model=LoginResponse)
async def login_with_apple(
    request: FirebaseLoginRequest,
    background: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Apple sign-in and automated client onboarding."""
    return await _handle_firebase_social_auth(
        request.firebase_token, "Apple", background, db
    )


@router.post("/refresh-token", response_model=Token)
async def refresh_token(token_in: RefreshTokenRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        payload = decode_token(token_in.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=400, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate refresh token")
    
    user = await get_user_by_id(db, sub)
    if not user and "@" in sub:
        user = await get_user_by_email(db, sub)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=404, detail="User not found or inactive")
    
    new_access_token = create_access_token(str(user["_id"]))
    new_refresh_token = create_refresh_token(str(user["_id"]))
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_user_me(user_in: UserUpdate, db: AsyncIOMotorDatabase = Depends(get_db), current_user: dict = Depends(get_current_active_user)):
    from app.crud.user import update_user
    user = await update_user(db, str(current_user["_id"]), user_in)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
