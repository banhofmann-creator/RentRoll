# Frontend Design System (GARBE Industrial)

Based on the GARBE Industrial Design Manual. All UI components follow these guidelines. Referenced from [PLAN.md](PLAN.md).

---

## 1. Color Palette

| Name | Hex | Usage |
|---|---|---|
| **GARBE-Blau** | `#003255` | Primary brand color. Nav bar, headings, primary buttons, dark backgrounds |
| GARBE-Blau 80% | `#224f71` | Hover states on primary elements |
| GARBE-Blau 60% | `#537392` | Secondary text, borders |
| GARBE-Blau 40% | `#879cb5` | Disabled states, muted elements |
| GARBE-Blau 20% | `#c0cada` | Light backgrounds, table header fills |
| **GARBE-Grün** | `#64B42D` | Accent color. Success states, CTAs, progress indicators, active navigation |
| GARBE-Grün 80% | `#99bf65` | Hover on green elements |
| GARBE-Grün 60% | `#b5cf8c` | Secondary green accents |
| GARBE-Grün 40% | `#d0e0b5` | Light green backgrounds |
| **GARBE-Ocker** | `#a48113` | Secondary accent. Warnings, inherited/orphan row highlights |
| **GARBE-Rot** | `#FF7276` | Error states, destructive actions |
| **GARBE-Türkis** | `#005555` | Tertiary accent. Info badges, chart alternative |
| GARBE-Türkis 80% | `#337777` | Hover on teal elements |
| GARBE-Türkis 60% | `#669999` | Muted teal |
| **Neutral Light** | `#ececec` | Borders, dividers |
| **Neutral Off-White** | `#f9f9f9` | Page background |

## 2. Typography

- **Font family:** Open Sans (Google Fonts), self-hosted via `next/font/google`
- **Headlines (h1, h2):** Open Sans Semibold, uppercase, letter-spacing `0.045em`, line-height 130%
- **Subheadings (h3, h4):** Open Sans Semibold, uppercase, letter-spacing `0.045em`, smaller size
- **Body text:** Open Sans Regular, normal case, letter-spacing `0.02em`, line-height 140%
- **Green dot accent:** Headlines may optionally end with a GARBE-Grün dot (`·`) for brand emphasis on hero/landing sections

## 3. Component Patterns

**Navigation bar:**
- Background: GARBE-Blau (`#003255`)
- Text: white, Open Sans Semibold
- Active link: GARBE-Grün underline or highlight
- Logo/brand mark: white text on GARBE-Blau

**Buttons:**
- Primary: GARBE-Grün background, white text, rounded. Hover: `#99bf65`
- Secondary: GARBE-Blau background, white text, rounded. Hover: `#224f71`
- Outline: transparent with GARBE-Blau border and text. Hover: GARBE-Blau fill
- Destructive: GARBE-Rot background, white text

**Tables:**
- Header: GARBE-Blau 20% (`#c0cada`) background, GARBE-Blau text, uppercase labels
- Rows: alternating white / `#f9f9f9`, hover `#ececec`
- Inherited/orphan highlight: GARBE-Ocker `#a48113` at 15% opacity background

**Status badges:**
- Complete/success: GARBE-Grün on light green
- Processing/info: GARBE-Türkis on light teal
- Error: GARBE-Rot on light red
- Warning: GARBE-Ocker on light amber

**Cards and panels:**
- White background, `#ececec` border, subtle shadow
- Section headings in GARBE-Blau, uppercase

**Drop zones:**
- Dashed border in GARBE-Blau 60%, transitions to GARBE-Grün on drag-over

## 4. Layout Principles

- Clean and structured — generous whitespace ("room to breathe")
- Max content width: `max-w-7xl` (1280px) centered
- Page background: `#f9f9f9`
- Headlines span full width at top of content area
- Charts and data visualizations use the primary color palette with 20% step gradations for series
