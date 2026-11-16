from typing import Optional
from app.schemas.common import BaseSchema
from app.schemas.user import UserResponse

class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseSchema):
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None

class RefreshTokenRequest(BaseSchema):
    refresh_token: str

class FirebaseLoginRequest(BaseSchema):
    firebase_token: str

class LoginResponse(Token):
    user: UserResponse

class RegisterCodeRequest(BaseSchema):
    """Step 1 of email-verified manual sign-up: request a code to an email."""
    email: str
    full_name: str

class RegisterVerifyRequest(BaseSchema):
    """Step 2: verify the code and set a password to create the account."""
    email: str
    code: str
    password: str
    full_name: Optional[str] = None
    company: Optional[str] = None
