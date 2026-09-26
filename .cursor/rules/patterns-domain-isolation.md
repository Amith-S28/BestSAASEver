# Cursor Rule: Pure Domain Entity Immutability & Methods

## Rule Invariant
1. Domain models must be defined as `@dataclass(frozen=True)` to prevent unintended mutations.
2. Invariants must be validated during instantiation in `__post_init__`.
3. Entity methods must be pure functions with zero side-effects.

### ✅ DO
```python
@dataclass(frozen=True)
class LabObservation:
    code_loinc: str
    display_name: str
    numeric_value: float
    unit: str
    flag: ObservationFlag

    def is_critical(self) -> bool:
        return self.flag in (ObservationFlag.CRITICAL_HIGH, ObservationFlag.CRITICAL_LOW)
```
