from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.models.trust_config import TrustConfig

# ✅ FIXED IMPORT
from app.api.schemas_trust_config import (
    TrustConfigCreate,
    TrustConfigUpdate,
    TrustConfigResponse,
)

router = APIRouter()


# ===================================================
# Utility: Normalize Environment
# ===================================================
def normalize_env(env: Optional[str]) -> str:
    return (env or "production").strip().lower()


# ===================================================
# CREATE CONFIG
# ===================================================
@router.post("/config", response_model=TrustConfigResponse)
def create_config(
    payload: TrustConfigCreate,
    db: Session = Depends(get_db),
):

    environment = normalize_env(payload.environment)

    existing = db.query(TrustConfig).filter(
        TrustConfig.tenant_id == payload.tenant_id,
        TrustConfig.environment == environment,
        TrustConfig.is_active == True,
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Active config already exists for this tenant + environment",
        )

    config = TrustConfig(
        tenant_id=payload.tenant_id,
        environment=environment,
        is_active=True if payload.is_active is None else payload.is_active,

        base_score=payload.base_score if payload.base_score is not None else 100.0,

        hallucination_weight=payload.hallucination_weight or 50.0,
        grounding_weight=payload.grounding_weight or 30.0,

        high_risk_penalty=payload.high_risk_penalty or 15.0,
        medium_risk_penalty=payload.medium_risk_penalty or 8.0,
        critical_risk_penalty=payload.critical_risk_penalty or 25.0,

        number_conflict_penalty=payload.number_conflict_penalty or 15.0,
        confidence_mismatch_penalty=payload.confidence_mismatch_penalty or 12.0,
        semantic_risk_penalty=payload.semantic_risk_penalty or 15.0,

        version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(config)
    db.commit()
    db.refresh(config)

    return config


# ===================================================
# GET CONFIG
# ===================================================
@router.get("/config", response_model=TrustConfigResponse)
def get_config(
    tenant_id: str = Query(...),
    environment: Optional[str] = Query("production"),
    db: Session = Depends(get_db),
):

    environment = normalize_env(environment)

    config = db.query(TrustConfig).filter(
        TrustConfig.tenant_id == tenant_id,
        TrustConfig.environment == environment,
        TrustConfig.is_active == True,
    ).first()

    if not config:
        raise HTTPException(
            status_code=404,
            detail="Active config not found",
        )

    return config


# ===================================================
# UPDATE CONFIG (PATCH + VERSION INCREMENT)
# ===================================================
@router.patch("/config", response_model=TrustConfigResponse)
def update_config(
    tenant_id: str = Query(...),
    environment: Optional[str] = Query("production"),
    payload: TrustConfigUpdate = None,
    db: Session = Depends(get_db),
):

    environment = normalize_env(environment)

    config = db.query(TrustConfig).filter(
        TrustConfig.tenant_id == tenant_id,
        TrustConfig.environment == environment,
        TrustConfig.is_active == True,
    ).first()

    if not config:
        raise HTTPException(
            status_code=404,
            detail="Config not found",
        )

    if payload is None:
        raise HTTPException(
            status_code=400,
            detail="No update payload provided",
        )

    update_data = payload.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    for field, value in update_data.items():
        setattr(config, field, value)

    config.version += 1
    config.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(config)

    return config


# ===================================================
# SOFT DELETE (Deactivate Config)
# ===================================================
@router.delete("/config")
def delete_config(
    tenant_id: str = Query(...),
    environment: Optional[str] = Query("production"),
    db: Session = Depends(get_db),
):

    environment = normalize_env(environment)

    config = db.query(TrustConfig).filter(
        TrustConfig.tenant_id == tenant_id,
        TrustConfig.environment == environment,
        TrustConfig.is_active == True,
    ).first()

    if not config:
        raise HTTPException(
            status_code=404,
            detail="Config not found",
        )

    config.is_active = False
    config.version += 1
    config.updated_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Config deactivated successfully",
        "tenant_id": tenant_id,
        "environment": environment,
        "new_version": config.version,
    }