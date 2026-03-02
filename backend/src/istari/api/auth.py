"""Session token signing and verification using itsdangerous."""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

COOKIE_NAME = "istari_session"
_SALT = "auth"
_MAX_AGE = 86400 * 30  # 30 days


def sign_token(secret_key: str) -> str:
    """Return a signed, tamper-proof session token."""
    return URLSafeTimedSerializer(secret_key).dumps("ok", salt=_SALT)


def verify_token(token: str, secret_key: str) -> bool:
    """Return True iff the token is valid and not expired."""
    if not token or not secret_key:
        return False
    try:
        URLSafeTimedSerializer(secret_key).loads(token, salt=_SALT, max_age=_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False
