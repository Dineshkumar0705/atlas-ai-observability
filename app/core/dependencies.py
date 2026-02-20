from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import hmac

from app.core.database import get_db
from app.models.api_key import TenantAPIKey
from app.models.tenant import Tenant
from app.core.security import hash_api_key


class AuthContext:
    """
    Structured authentication context.
    Returned to endpoints after successful validation.
    """

    def __init__(self, tenant_id: str, api_key_id: int):
        self.tenant_id = tenant_id
        self.api_key_id = api_key_id


# ======================================================
# 🔐 Tenant API Key Authentication Dependency
# ======================================================
def get_current_tenant(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> AuthContext:

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key"
        )

    # --------------------------------------------------
    # Hash Incoming Key
    # --------------------------------------------------
    hashed_input = hash_api_key(x_api_key)

    # --------------------------------------------------
    # Lookup Key Record
    # --------------------------------------------------
    key_record = db.query(TenantAPIKey).filter(
        TenantAPIKey.is_active == True
    ).all()

    # Use constant-time comparison
    matched_key = None

    for record in key_record:
        if hmac.compare_digest(record.api_key_hash, hashed_input):
            matched_key = record
            break

    if not matched_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    # --------------------------------------------------
    # Check Key Expiry (if column exists)
    # --------------------------------------------------
    if hasattr(matched_key, "expires_at") and matched_key.expires_at:
        if matched_key.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=401,
                detail="API key expired"
            )

    # --------------------------------------------------
    # Validate Tenant Status
    # --------------------------------------------------
    tenant = db.query(Tenant).filter(
        Tenant.tenant_id == matched_key.tenant_id,
        Tenant.is_active == True
    ).first()

    if not tenant:
        raise HTTPException(
            status_code=403,
            detail="Tenant inactive or suspended"
        )

    return AuthContext(
        tenant_id=tenant.tenant_id,
        api_key_id=matched_key.id
    )