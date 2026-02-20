from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List
from decimal import Decimal
import hashlib
import json
import time

from app.api.schemas import AtlasRequest, AtlasResponse
from app.core.database import get_db
from app.core.trust_engine import TrustEngine, TrustWeights
from app.core.dependencies import get_current_tenant, AuthContext

from app.models.evaluation_log import EvaluationLog
from app.models.trust_config import TrustConfig
from app.models.tenant import Tenant
from app.models.usage_meter import UsageMeter

from app.engines.hallucination import HallucinationEngine
from app.engines.grounding import GroundingEngine
from app.engines.business_risk import BusinessRiskEngine
from app.engines.number_conflict import NumberConflictEngine
from app.engines.confidence_mismatch import ConfidenceMismatchEngine
from app.engines.semantic_contradiction import SemanticContradictionEngine

router = APIRouter()


# ===================================================
# 🔐 Deterministic Request Hash
# ===================================================
def generate_request_hash(tenant_id: str, request: AtlasRequest) -> str:
    payload = {
        "tenant_id": tenant_id,
        "app_name": request.app_name,
        "user_query": request.user_query,
        "retrieved_context": request.retrieved_context,
        "llm_response": request.llm_response,
        "model_info": request.model_info.dict() if request.model_info else None,
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


# ===================================================
# 🎛 Load Trust Weights
# ===================================================
def load_trust_weights(db: Session, tenant_id: str) -> TrustWeights:
    config = db.query(TrustConfig).filter(
        TrustConfig.tenant_id == tenant_id,
        TrustConfig.is_active == True
    ).first()

    if not config:
        return TrustWeights()

    weights = TrustWeights(
        base_score=config.base_score,
        hallucination_weight=config.hallucination_weight,
        grounding_weight=config.grounding_weight,
        high_risk_penalty=config.high_risk_penalty,
        medium_risk_penalty=config.medium_risk_penalty,
        critical_risk_penalty=config.critical_risk_penalty,
        number_conflict_penalty=config.number_conflict_penalty,
        confidence_mismatch_penalty=config.confidence_mismatch_penalty,
        semantic_risk_penalty=config.semantic_risk_penalty,
    )

    setattr(weights, "version", config.version)
    return weights


# ===================================================
# 🚀 MAIN EVALUATION
# ===================================================
@router.post("/evaluate", response_model=AtlasResponse)
def evaluate(
    request: AtlasRequest,
    auth: AuthContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    start_time = time.time()
    tenant_id = auth.tenant_id

    try:
        explanations: List[str] = []

        tenant = db.query(Tenant).filter(
            Tenant.tenant_id == tenant_id,
            Tenant.is_active == True,
            Tenant.is_suspended == False
        ).first()

        if not tenant:
            raise HTTPException(status_code=403, detail="Tenant inactive")

        # --------- Engines ----------
        number_result = NumberConflictEngine().detect_conflict(
            request.retrieved_context,
            request.llm_response
        )

        number_conflict = number_result["conflict"]
        explanations.extend(number_result.get("details", []))

        hallucination_score = HallucinationEngine().score(
            request.retrieved_context,
            request.llm_response,
            number_conflict=number_conflict
        )["hallucination_score"]

        grounding_score = GroundingEngine().score(
            request.retrieved_context,
            request.llm_response
        )["grounding_score"]

        risk_result = BusinessRiskEngine().assess(request.user_query)
        business_risk = risk_result["risk_level"]

        confidence_result = ConfidenceMismatchEngine().evaluate(
            request.llm_response,
            grounding_score
        )

        confidence_mismatch = confidence_result["mismatch"]

        if confidence_result.get("explanation"):
            explanations.append(confidence_result["explanation"])

        semantic_risk = False
        similarity_score = None

        if grounding_score < 0.75 or hallucination_score > 0.3:
            semantic_result = SemanticContradictionEngine().evaluate(
                request.retrieved_context,
                request.llm_response
            )

            semantic_risk = semantic_result["semantic_risk"]
            similarity_score = semantic_result["similarity_score"]

            if semantic_result.get("explanation"):
                explanations.append(semantic_result["explanation"])

        weights = load_trust_weights(db, tenant_id)

        trust_result = TrustEngine(weights=weights).compute(
            hallucination=hallucination_score,
            grounding=grounding_score,
            risk=business_risk,
            number_conflict=number_conflict,
            confidence_mismatch=confidence_mismatch,
            semantic_risk=semantic_risk
        )

        trust_score = trust_result["trust_score"]

        recommendation = (
            "BLOCK" if trust_score < 40
            else "WARN" if trust_score < 70
            else "ALLOW"
        )

        log = EvaluationLog(
            tenant_id=tenant_id,
            app_name=request.app_name,
            trust_score=trust_score,
            hallucination_probability=hallucination_score,
            grounding_score=grounding_score,
            business_risk=business_risk,
            number_conflict=number_conflict,
            confidence_mismatch=confidence_mismatch,
            semantic_risk=semantic_risk,
            semantic_similarity=similarity_score,
            recommendation=recommendation,
            explanations=explanations,
            user_query=request.user_query,
            retrieved_context=request.retrieved_context,
            llm_response=request.llm_response,
            created_at=datetime.utcnow(),
        )

        db.add(log)
        db.commit()

        return AtlasResponse(
            trust_score=trust_score,
            hallucination_probability=hallucination_score,
            grounding_score=grounding_score,
            business_risk=business_risk,
            recommendation=recommendation,
            number_conflict=number_conflict,
            confidence_mismatch=confidence_mismatch,
            explanations=explanations,
            evaluated_at=datetime.utcnow()
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================
# 📈 DASHBOARD STATS (FRONTEND CRITICAL)
# ===================================================
@router.get("/stats/trend")
def stats_trend(
    auth: AuthContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    tenant_id = auth.tenant_id

    total = db.query(EvaluationLog).filter(
        EvaluationLog.tenant_id == tenant_id
    ).count()

    avg_trust = db.query(func.avg(EvaluationLog.trust_score)).filter(
        EvaluationLog.tenant_id == tenant_id
    ).scalar() or 0

    blocked = db.query(EvaluationLog).filter(
        EvaluationLog.tenant_id == tenant_id,
        EvaluationLog.recommendation == "BLOCK"
    ).count()

    warned = db.query(EvaluationLog).filter(
        EvaluationLog.tenant_id == tenant_id,
        EvaluationLog.recommendation == "WARN"
    ).count()

    allowed = db.query(EvaluationLog).filter(
        EvaluationLog.tenant_id == tenant_id,
        EvaluationLog.recommendation == "ALLOW"
    ).count()

    last_7_days = datetime.utcnow() - timedelta(days=7)

    trend_data = db.query(
        func.date(EvaluationLog.created_at),
        func.avg(EvaluationLog.trust_score)
    ).filter(
        EvaluationLog.tenant_id == tenant_id,
        EvaluationLog.created_at >= last_7_days
    ).group_by(func.date(EvaluationLog.created_at)).all()

    return {
        "total_evaluations": total,
        "average_trust_score": round(avg_trust, 2),
        "blocked_count": blocked,
        "warned_count": warned,
        "allowed_count": allowed,
        "trend": [
            {"date": str(row[0]), "avg_trust": round(row[1], 2)}
            for row in trend_data
        ]
    }


# ===================================================
# 📄 LIST EVALUATIONS
# ===================================================
@router.get("/evaluations")
def list_evaluations(
    auth: AuthContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
):
    tenant_id = auth.tenant_id
    offset = (page - 1) * page_size

    total = db.query(EvaluationLog).filter(
        EvaluationLog.tenant_id == tenant_id
    ).count()

    results = db.query(EvaluationLog).filter(
        EvaluationLog.tenant_id == tenant_id
    ).order_by(EvaluationLog.created_at.desc()) \
     .offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": results
    }


# ===================================================
# 💰 BILLING REVENUE
# ===================================================
@router.get("/billing/revenue")
def billing_revenue(
    auth: AuthContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    tenant_id = auth.tenant_id

    total_revenue = db.query(
        func.sum(UsageMeter.estimated_cost)
    ).filter(
        UsageMeter.tenant_id == tenant_id
    ).scalar() or 0

    return {
        "tenant_id": tenant_id,
        "total_revenue_generated": float(total_revenue)
    }


# ===================================================
# 👑 ADMIN ANALYTICS
# ===================================================
@router.get("/admin/analytics")
def admin_analytics(db: Session = Depends(get_db)):
    return {
        "total_tenants": db.query(Tenant).count(),
        "total_evaluations": db.query(EvaluationLog).count(),
        "total_revenue": float(
            db.query(func.sum(UsageMeter.estimated_cost)).scalar() or 0
        )
    }