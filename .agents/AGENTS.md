# eTala Workspace Design Rules & Guidelines

## Responsive System & Breakpoint Standard

When building or updating UI components for eTala, adopt the following 3 core behavioral breakpoints across 5 target device ranges:

```text
320px ───────── 480px    : MOBILE
481px ───────── 767px    : SMALL / LANDSCAPE
768px ───────── 1024px   : TABLET
1025px ──────── 1280px   : LAPTOP
1281px ──────── 1920px+  : DESKTOP
```

> **Testing Matrix vs Breakpoints**: Device dimensions (`667`, `767`, `834`, `1024`, `1280`, `1366`, `1440`, `1920`) are test sizes inside these 5 target ranges. Do NOT write separate CSS breakpoints for every width.

---

## Page Header Layout Rules (`.etala-page-header`)

### 1. Desktop, Laptop & Tablet (`≥ 768px`)
- **Layout**: Row layout (`flex-direction: row`, `justify-content: space-between`, `align-items: center`).
- **Alignment**: Page Title & Subtitle on the LEFT; Contextual Action buttons on the RIGHT.
- **Buttons**: Always inline.

```text
┌────────────────────────────────────────────────────────────┐
│ Page Title                              [Action] [Action]  │
│ Description                                                 │
└────────────────────────────────────────────────────────────┘
```

### 2. Small Tablet & Mobile (`< 768px`)
- **Layout**: Column layout (`flex-direction: column`).
- **Alignment**: Page Title & Subtitle top; Action buttons placed below.
- **Buttons**: Inline by default (`flex-wrap: wrap`, `gap: 8px`). Keep buttons side-by-side whenever they fit; only allow vertical wrapping if screen space is too tight (<360px). Avoid forcing vertical stacked button blocks on landscape or small tablets.

```text
┌────────────────────────────────────────────┐
│ Page Title                                 │
│ Description                               │
│                                            │
│ [Action] [Action]                          │
└────────────────────────────────────────────┘
```
