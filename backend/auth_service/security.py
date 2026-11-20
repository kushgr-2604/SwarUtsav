
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from fastapi import Depends
from jwt.exceptions import InvalidTokenError

PRIVATE_KEY_PATH = "/run/secrets/jwt_private"
PUBLIC_KEY_PATH = "/run/secrets/jwt_public"

ALGORITHM = "RS256"
ISSUER = "swarutsav-auth"
AUDIENCE = "swarutsav-api"

with open(PRIVATE_KEY_PATH, "r") as f:
    PRIVATE_KEY = f.read()

with open(PUBLIC_KEY_PATH, "r") as f:
    PUBLIC_KEY = f.read()

bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: str, role: str):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "role": role,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "jti": str(uuid4()),
        "type": "access"
    }

    return jwt.encode(
        payload,
        PRIVATE_KEY,
        algorithm=ALGORITHM
    )


def verify_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={
                "require": [
                    "sub", "exp", "iat",
                    "iss", "aud", "jti", "type"
                ]
            }
        )

        if payload.get("type") != "access":
            raise InvalidTokenError("Wrong token type")

        if payload.get("role") not in ["candidate", "admin"]:
            raise InvalidTokenError("Invalid role")

        return payload

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(
    credentials = Depends(bearer_scheme)
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    return verify_access_token(credentials.credentials)
