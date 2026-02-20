"""
Model registry for ATLAS.

All SQLAlchemy models must be imported here
so that:

1. Alembic autogenerate detects them
2. Base.metadata registers tables
3. App startup loads schema correctly
"""

from .evaluation_log import EvaluationLog
from .trust_config import TrustConfig
from .tenant import Tenant
from .api_key import TenantAPIKey
from .usage_meter import UsageMeter
from .pricing_plan import PricingPlan
from .embedding_cache import EmbeddingCache

__all__ = [
    "EvaluationLog",
    "TrustConfig",
    "Tenant",
    "TenantAPIKey",
    "UsageMeter",
    "PricingPlan",
    "EmbeddingCache",   # ✅ important for Alembic detection
]