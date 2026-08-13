# eTala Workspace Design Rules & Guidelines

## eTala Responsive Design Standard

Apply a consistent, mobile-first responsive design system throughout eTala.

### Breakpoints & Ranges

Use these responsive ranges consistently across the entire eTala UI:

```text
320px  ───────── 480px    : Mobile
481px  ───────── 767px    : Small / Landscape
768px  ───────── 1024px   : Tablet
1025px ──────── 1280px   : Laptop
1281px ──────── 1920px   : Desktop
1921px+                 : Wide Desktop
```

> **Testing Matrix vs Breakpoints**: Do not create layouts for individual phone or monitor models (e.g. "iPhone 13", "iPad", "1366px laptop"). Those widths (`320`, `360`, `375`, `390`, `430`, `480`, `768`, `834`, `1024`, `1280`, `1366`, `1440`, `1920`) are testing points inside these target ranges. The CSS must respond smoothly to available width.

---

### Core Layout & Styling Rules

1. **Viewport Meta Tag**:
   - Ensure the shared Django base template (`permits/templates/permits/base.html`) has:
     `<meta name="viewport" content="width=device-width, initial-scale=1.0">`

2. **Mobile-First CSS Architecture**:
   - Write base CSS for the smallest mobile layout first (`/* Base = Mobile */`).
   - Use progressive enhancement via `min-width` media queries:
     - `@media (min-width: 481px) { ... }`
     - `@media (min-width: 768px) { ... }`
     - `@media (min-width: 1025px) { ... }`
     - `@media (min-width: 1281px) { ... }`

3. **Layout Systems (Flexbox vs Grid vs Absolute)**:
   - **Flexbox**: Use for headers, action bars, navigation, and horizontal controls.
   - **CSS Grid**: Use for card grids, dashboard layouts, and map + list split layouts.
   - **Absolute Positioning**: Avoid using `position: absolute` for major page structures. Use absolute positioning ONLY for small overlay badges or floating tooltips when genuinely required.

4. **Sizing Units (px vs % vs rem vs vh/vw)**:
   - `%`: Flexible container widths.
   - `rem`: Typography and spacing padding/margins.
   - `vw/vh`: Special viewport-based sizing only when genuinely useful.
   - `px`: Precise UI details (border thickness, icon dimensions, minimum heights, border radius, touch targets).

5. **Touch Targets**:
   - Interactive controls (buttons, inputs, dropdowns, icon controls, menu items) must have a comfortable touch target of around **44px – 48px**.
   - Small decorative icons do NOT need to be enlarged to 48px unless interactive.

6. **Inputs & Form Controls (Prevent iOS Safari Zoom)**:
   - All `input`, `select`, and `textarea` elements must have a minimum `font-size: 16px` on mobile to prevent unwanted browser zoom behavior on iOS Safari.

7. **Overflow & Long Text Handling**:
   - Prevent horizontal page overflow (`overflow-x: hidden` / container constraints).
   - Long text (filenames, project titles, permit descriptions, staff names, barangay names) must NEVER break layouts or force horizontal scrolling. Handle via `text-overflow: ellipsis`, `overflow-wrap: break-word`, or `word-break: break-word`.

8. **Reflow over Shrinking & Functionality Preservation**:
   - Do NOT simply shrink desktop layouts on mobile. Reflow the interface according to available space.
   - Do NOT hide important functionality on mobile using `display: none`. Reposition, stack, collapse, or adapt controls instead.

---

### Component Behavior Guidelines

- **Page Headers (`.etala-page-header`)**:
  - `≥ 768px`: Row layout (`flex-direction: row`, `justify-content: space-between`). Title/subtitle left, actions inline right.
  - `< 768px`: Column layout (`flex-direction: column`). Title top, actions below with inline flex wrap (`gap: 8px`).

- **Cards & Grids**:
  - Desktop/Tablet: Multi-column CSS Grid (`grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))`).
  - Mobile: Single-column layout. Keep cards compact without excessive empty padding.

- **Tables**:
  - Desktop: Standard clean tabular layout.
  - Mobile: Reflow complex tables into compact card structures or readable mobile-friendly card rows rather than forcing tiny unreadable columns.

- **Modals**:
  - Must fit comfortably within the viewport with `max-height: 90vh`.
  - Must remain centered and scroll internally (`overflow-y: auto`) when content is long.
  - Keep action buttons (`Cancel`, `Save`, `Upload`) accessible and visible on mobile.
  - Lock background scrolling when modal is active (`body.modal-open { overflow: hidden; }`).

- **Maps**:
  - Desktop/Tablet: Side-by-side split layout (e.g. `grid-template-columns: minmax(0, 0.45fr) minmax(0, 0.55fr)`).
  - Sticky map behavior must remain within page bounds without overlapping footers or headers.
  - On mobile (`< 768px`), stack map and list vertically so the map does not consume all screen height.
