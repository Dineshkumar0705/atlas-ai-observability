from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from app.models.evaluation_log import EvaluationLog


class AnalyticsService:

    @staticmethod
    def get_summary(
        db: Session,
        app_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):

        query = db.query(EvaluationLog)

        if app_name:
            query = query.filter(EvaluationLog.app_name == app_name)

        if start_date:
            query = query.filter(EvaluationLog.created_at >= start_date)

        if end_date:
            query = query.filter(EvaluationLog.created_at <= end_date)

        total_requests = query.count()

        if total_requests == 0:
            return {
                "total_requests": 0,
                "avg_trust_score": None,
                "block_rate": None,
                "high_risk_rate": None,
            }

        avg_trust_score = query.with_entities(
            func.avg(EvaluationLog.trust_score)
        ).scalar()

        block_count = query.filter(
            EvaluationLog.recommendation == "BLOCK"
        ).count()

        high_risk_count = query.filter(
            EvaluationLog.business_risk == "HIGH"
        ).count()

        return {
            "total_requests": total_requests,
            "avg_trust_score": round(avg_trust_score, 2),
            "block_rate": round(block_count / total_requests, 2),
            "high_risk_rate": round(high_risk_count / total_requests, 2),
        }