import logging
from typing import Dict, Any
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from backend.config.settings import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Validates a JWT token and returns the user_id (subject).
    Performs real signature, issuer, audience, and expiry validation.
    """
    token = credentials.credentials
    try:
        # In a real environment, we'd fetch JWKS or a shared secret.
        # Here we assume a symmetric secret configured in settings.
        secret = getattr(settings, "JWT_SECRET", "dummy_secret_for_dev")
        issuer = getattr(settings, "JWT_ISSUER", "agentos.auth")
        audience = getattr(settings, "JWT_AUDIENCE", "agentos.api")
        
        # Real validation: signature, expiry, issuer, audience
        payload = jwt.decode(
            token, 
            secret, 
            algorithms=["HS256"], 
            issuer=issuer, 
            audience=audience
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing subject (sub)")
            
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
