# Tech Spec: Accessible Healthcare Design System & Tokens

_MedRAG v2.0 Visual & Interaction Design Standard_  
_Derived from UI/UX Pro Max & WCAG 2.1 AA Standards_

---

## 1. Healthcare Color Palette Tokens

```css
:root {
  /* Brand Foundations */
  --med-primary-900: #0a2540;
  --med-primary-700: #1a4f8b;
  --med-primary-500: #2563eb;
  --med-primary-100: #e0e7ff;

  /* Clinical Severity & Verification Status */
  --med-status-verified: #059669;       /* Green: Entailed evidence */
  --med-status-verified-bg: #ecfdf5;
  --med-status-uncertain: #d97706;      /* Amber: Clinical correlation advised */
  --med-status-uncertain-bg: #fffbeb;
  --med-status-contradicted: #dc2626;   /* Red: Safety redaction tombstone */
  --med-status-contradicted-bg: #fef2f2;
  --med-status-cmo-verified: #2563eb;   /* Blue: CMO manual override sign-off */
  --med-status-cmo-verified-bg: #eff6ff;

  /* Surfaces & Typography */
  --med-bg-canvas: #f8fafc;
  --med-bg-surface: #ffffff;
  --med-text-primary: #0f172a;
  --med-text-secondary: #475569;
  --med-border-subtle: #e2e8f0;
}
```

---

## 2. Accessibility & Typography Standards

- **Typography**: Inter / Outfit via Google Fonts. High legibility tabular figures (`font-variant-numeric: tabular-nums`) for laboratory values.
- **Contrast**: All body text and badges achieve minimum 4.5:1 contrast against background (WCAG AA).
- **No Color-Alone Cues**: Every verification badge pairs color with an explicit semantic icon and text label (e.g. checkmark + "VERIFIED").
