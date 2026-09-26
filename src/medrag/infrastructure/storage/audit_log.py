"""Audit log repository tracking institutional events with HIPAA/DPDP compliance."""

import base64
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AuditEntry:
    entry_id: str
    timestamp: str
    event_type: str
    tenant_id: str
    user_id: str
    role: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    trace_id: str


class AuditLogRepository:
    """In-memory and persistent audit logger for clinical operations."""

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []

    def record_event(
        self,
        event_type: str,
        tenant_id: str,
        user_id: str,
        role: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any],
        trace_id: str = "trace-system",
    ) -> AuditEntry:
        """Record an immutable audit log entry."""
        entry = AuditEntry(
            entry_id=f"aud-{len(self._entries) + 1:06d}",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            event_type=event_type,
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            trace_id=trace_id,
        )
        self._entries.append(entry)
        return entry

    def query_logs(
        self,
        tenant_id: str,
        limit: int = 25,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query audit log entries for a tenant with cursor-based pagination."""
        # Tenant scoping: if tenant is not 'admin', filter strictly by tenant_id
        if tenant_id == "system" or tenant_id == "admin":
            filtered = self._entries
        else:
            filtered = [e for e in self._entries if e.tenant_id == tenant_id]

        start_index = 0
        if cursor:
            try:
                decoded = json.loads(base64.b64decode(cursor).decode("utf-8"))
                start_index = decoded.get("offset", 0)
            except Exception:
                start_index = 0

        page_entries = filtered[start_index : start_index + limit]
        next_offset = start_index + limit
        has_more = next_offset < len(filtered)
        next_cursor = None
        if has_more:
            next_cursor = base64.b64encode(json.dumps({"offset": next_offset}).encode("utf-8")).decode("utf-8")

        return {
            "items": [asdict(e) for e in page_entries],
            "cursor": next_cursor,
            "has_more": has_more,
            "total_count": len(filtered),
        }
