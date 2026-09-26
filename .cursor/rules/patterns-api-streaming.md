# Cursor Rule: Server-Sent Events (SSE) Streaming Conventions

## Rule Invariant
1. SSE streams must emit structured event types (`synthesis_chunk`, `citation_verified`, `claim_redacted`, `synthesis_complete`).
2. Synthesis chunks must include monotonic `chunk_index` to support client-side ordering and reconnection deduplication.
3. Stream errors must be transmitted as an `event: stream_error` frame before closing the socket.

### ✅ DO
```python
yield {
    "event": "synthesis_chunk",
    "data": json.dumps({"chunk_index": idx, "text": token, "is_final": False})
}
```
