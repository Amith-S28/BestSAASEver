"""Tenant-scoped token-bucket rate limiter and quota tracker."""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List
from medrag.domain.exceptions import QuotaExceededException


@dataclass
class TenantQuotaConfig:
    requests_per_minute: int
    concurrent_streams_limit: int
    monthly_queries_limit: int


# Default tier configurations
TIER_CONFIGS: Dict[str, TenantQuotaConfig] = {
    "community": TenantQuotaConfig(
        requests_per_minute=10,
        concurrent_streams_limit=2,
        monthly_queries_limit=250,
    ),
    "standard": TenantQuotaConfig(
        requests_per_minute=60,
        concurrent_streams_limit=10,
        monthly_queries_limit=5000,
    ),
    "enterprise": TenantQuotaConfig(
        requests_per_minute=300,
        concurrent_streams_limit=50,
        monthly_queries_limit=100000,
    ),
}


class TenantRateLimiter:
    """In-memory sliding window rate limiter and monthly quota manager."""

    def __init__(self) -> None:
        # tenant_id -> list of request timestamps in the current window
        self._request_timestamps: Dict[str, List[float]] = defaultdict(list)
        # tenant_id -> active concurrent streams count
        self._active_streams: Dict[str, int] = defaultdict(int)
        # tenant_id -> monthly queries count
        self._monthly_queries: Dict[str, int] = defaultdict(int)
        # tenant_id -> tier
        self._tenant_tiers: Dict[str, str] = defaultdict(lambda: "standard")

    def set_tenant_tier(self, tenant_id: str, tier: str) -> None:
        """Assign subscription tier to tenant."""
        if tier in TIER_CONFIGS:
            self._tenant_tiers[tenant_id] = tier

    def check_and_record_request(self, tenant_id: str) -> None:
        """Check rate limit and monthly quota; record request if permitted."""
        tier = self._tenant_tiers[tenant_id]
        cfg = TIER_CONFIGS[tier]
        now = time.time()

        # 1. Monthly quota check
        if self._monthly_queries[tenant_id] >= cfg.monthly_queries_limit:
            raise QuotaExceededException(
                tenant_id=tenant_id,
                quota_type="queries",
                limit=cfg.monthly_queries_limit,
            )

        # 2. Sliding window (60s) rate limit check
        cutoff = now - 60.0
        timestamps = [ts for ts in self._request_timestamps[tenant_id] if ts > cutoff]
        self._request_timestamps[tenant_id] = timestamps

        if len(timestamps) >= cfg.requests_per_minute:
            raise QuotaExceededException(
                tenant_id=tenant_id,
                quota_type="requests_per_minute",
                limit=cfg.requests_per_minute,
            )

        # Record usage
        self._request_timestamps[tenant_id].append(now)
        self._monthly_queries[tenant_id] += 1

    def acquire_stream(self, tenant_id: str) -> None:
        """Acquire concurrent stream slot."""
        tier = self._tenant_tiers[tenant_id]
        cfg = TIER_CONFIGS[tier]
        if self._active_streams[tenant_id] >= cfg.concurrent_streams_limit:
            raise QuotaExceededException(
                tenant_id=tenant_id,
                quota_type="concurrent_streams",
                limit=cfg.concurrent_streams_limit,
            )
        self._active_streams[tenant_id] += 1

    def release_stream(self, tenant_id: str) -> None:
        """Release concurrent stream slot."""
        if self._active_streams[tenant_id] > 0:
            self._active_streams[tenant_id] -= 1

    def get_tenant_usage(self, tenant_id: str) -> Dict[str, int]:
        """Get current usage stats for tenant."""
        tier = self._tenant_tiers[tenant_id]
        cfg = TIER_CONFIGS[tier]
        return {
            "queries_used": self._monthly_queries[tenant_id],
            "monthly_limit": cfg.monthly_queries_limit,
            "active_streams": self._active_streams[tenant_id],
            "max_concurrent_streams": cfg.concurrent_streams_limit,
        }
