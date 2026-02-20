"""
ATLAS Security Layer
--------------------

Handles:
- API Key authentication
- Tenant resolution
- Secure hash comparison
- Key status validation
- Tenant suspension enforcement
- FastAPI dependency integration
"""

from typing import Optional

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.api_key import TenantAPIKey
from app.models.tenant import Tenant
from app.core.api_key_utils import hash_api_key, verify_api_key

from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)


# ============================================================
# CONFIG
# ============================================================

API_KEY_HEADER = "x-api-key"


# ============================================================
# CORE AUTH LOGIC
# ============================================================

def authenticate_api_key(
    raw_api_key: str,
    db: Session,
) -> Tenant:
    """
    Validates API key and returns Tenant.

    Steps:
    1. Extract prefix
    2. Hash raw key
    3. Lookup key in DB
    4. Validate key active + not revoked
    5. Validate tenant active + not suspended
    """

    if not raw_api_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key missing"
        )

    # Extract prefix for fast lookup
    key_prefix = raw_api_key[:20]

    api_key_record: Optional[TenantAPIKey] = (
        db.query(TenantAPIKey)
        .filter(
            TenantAPIKey.key_prefix == key_prefix,
            TenantAPIKey.is_active.is_(True),
            TenantAPIKey.is_revoked.is_(False),
        )
        .first()
    )

    if not api_key_record:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Verify hash securely
    if not verify_api_key(raw_api_key, api_key_record.api_key_hash):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Fetch tenant
    tenant: Optional[Tenant] = (
        db.query(Tenant)
        .filter(Tenant.tenant_id == api_key_record.tenant_id)
        .first()
    )

    if not tenant:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Tenant not found"
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Tenant is inactive"
        )

    if tenant.is_suspended:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Tenant account suspended"
        )

    return tenant


# ============================================================
# FASTAPI DEPENDENCY
# ============================================================

def get_current_tenant(
    x_api_key: str = Header(None, alias=API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> Tenant:
    """
    FastAPI dependency for secured routes.

    Usage:

    @router.post("/evaluate")
    def evaluate(..., tenant: Tenant = Depends(get_current_tenant)):
        ...
    """

    return authenticate_api_key(x_api_key, db)