# Tech Spec: Rate Limiting, Abuse Prevention & Quota Control

_MedRAG v2.0 Quota & Protection Engineering_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Token-Bucket Rate Limiter (Redis-Backed)

To protect local inference servers (vLLM / LM Studio) from GPU exhaustion, requests are metered using an atomic Redis token-bucket algorithm:

### Algorithm Formulation
- **Capacity ($C$)**: Maximum burst size allowed per plan tier.
- **Refill Rate ($r$)**: Tokens added per second.
- **Lua Script Execution**: Evaluated atomically in Redis to prevent race conditions during concurrent client bursts.

```lua
-- Atomic Token Bucket Lua Script
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

-- Retrieve current tokens and last timestamp
local data = redis.call('HMGET', key, 'tokens', 'last_updated')
local tokens = tonumber(data[1]) or capacity
local last_updated = tonumber(data[2]) or now

-- Compute refilled tokens
local delta = math.max(0, now - last_updated)
tokens = math.min(capacity, tokens + delta * refill_rate)

if tokens >= requested then
    tokens = tokens - requested
    redis.call('HMSET', key, 'tokens', tokens, 'last_updated', now)
    return 1 -- Allowed
else
    return 0 -- Rejected
end
```

---

## 2. Quota Enforcement & Overage Handling

1. **Monthly Query Counting**: Atomic `INCR` on key `quota:{tenant_id}:{YYYY_MM}`.
2. **Quota Breaches**: If current count exceeds plan ceiling:
   - Returns HTTP `429 Too Many Requests`.
   - Response contains `Retry-After` header and `error_code: "QUOTA_EXCEEDED"`.
   - Never falls back to cached pseudo-data.
