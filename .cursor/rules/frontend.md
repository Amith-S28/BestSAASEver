# Cursor Rule: Frontend Guidelines & Accessible Healthcare UI

## Rule Invariant
1. Next.js 15 App Router standard: Server Components by default; add `'use client'` only when interactive state, hooks, or event listeners are required.
2. Styling: Strict adherence to UI/UX Pro Max tokens and WCAG 2.1 AA contrast requirements.
3. Every verification badge must display both a semantic icon and clear textual status (never rely on color alone).

### ✅ DO
```tsx
// Accessible status badge with icon + text
export function VerificationBadge({ status }: { status: VerificationStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <span className={`badge badge-${status.toLowerCase()}`} role="status">
      <config.Icon className="w-4 h-4 mr-1" aria-hidden="true" />
      <span>{config.label}</span>
    </span>
  );
}
```
