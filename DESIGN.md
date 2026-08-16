# Design System: IncidentMind Precision

**Project:** IncidentMind IT Operations App (Stitch MCP)  
**Style Archetype:** Corporate Modernism & Technical Precision  
**Target Platform:** Enterprise Desktop & Web Application

---

## 1. Brand & Aesthetic Principles

- **Corporate Modernism:** High information density, extreme legibility, and quiet authority designed for high-pressure IT incident response.
- **Precision Grid:** Strict alignment to an 8px base grid with low-contrast borders defining workspace boundaries.
- **Low Motion:** Fast, functional micro-interactions (150ms duration) ensuring zero cognitive latency.

---

## 2. Color Palette

### Primary & Secondary Palette
| Token | Hex / Value | Usage |
|---|---|---|
| **Primary** | `#00236F` / `#1E3A8A` | Deep Blue for navigation, primary buttons, and key focus boundaries |
| **Primary Container** | `#1E3A8A` | Container fills, active navigation items |
| **On Primary** | `#FFFFFF` | Text on primary backgrounds |
| **Secondary** | `#0058BE` / `#2170E4` | Interactive accents, secondary actions |
| **Secondary Container** | `#2170E4` | Soft highlight containers |

### Surfaces & Backgrounds
| Token | Hex / Value | Usage |
|---|---|---|
| **Background / Canvas** | `#F8FAFC` / `#F8F9FF` | Main application viewport canvas |
| **Surface (Level 1)** | `#FFFFFF` | Cards, table containers, sidebar panels |
| **Surface Container Low** | `#EFF4FF` | Subtle callout containers |
| **Surface Container** | `#E5EEFF` | Nested UI component containers |
| **Surface Container High** | `#DCE9FF` | Elevated card surfaces |
| **Inverse Surface** | `#213145` | Dark mode overlays and high-contrast tooltips |

### Text & Foreground
| Token | Hex / Value | Usage |
|---|---|---|
| **On Surface (Primary Text)** | `#0B1C30` | Main body text, section headers, card titles |
| **On Surface Variant (Secondary)** | `#444651` | Subtitles, meta-data labels, helper text |
| **Outline** | `#757682` | Input borders, separator lines |
| **Outline Variant** | `#C5C5D3` / `#E2E8F0` | Card outer borders, table dividers |

### Functional Status Colors
| Status | Color Token | Visual Standard |
|---|---|---|
| **Success** | Emerald Green (`#10B981` / `#059669`) | Resolved tickets, healthy nodes, 10% opacity pill background |
| **Failure** | Critical Red (`#BA1A1A` / `#EF4444`) | System outages, failed execution attempts, critical alerts |
| **Partial** | Warm Amber (`#F59E0B` / `#D97706`) | Performance degradation, warning states |
| **Rejected** | Muted Gray (`#64748B`) | Cancelled fixes, invalid attempts |
| **Unknown** | Dashed Gray (`#94A3B8`) | Pending telemetry, unverified outcomes |

---

## 3. Typography

### Font Families
- **Primary Body & Display:** `Inter`, sans-serif
- **Technical Identifiers & Code:** `JetBrains Mono`, monospace (used for IP addresses, Log IDs, Node names, and trace hashes)

### Type Scale

| Level | Font Family | Size | Weight | Line Height | Letter Spacing |
|---|---|---|---|---|---|
| **Display** | Inter | 30px | 700 (Bold) | 38px | -0.02em |
| **H1** | Inter | 24px | 600 (Semi-Bold) | 32px | -0.01em |
| **H2** | Inter | 20px | 600 (Semi-Bold) | 28px | Normal |
| **H3** | Inter | 16px | 600 (Semi-Bold) | 24px | Normal |
| **Body Large** | Inter | 16px | 400 (Regular) | 24px | Normal |
| **Body Medium** | Inter | 14px | 400 (Regular) | 20px | Normal |
| **Body Small** | Inter | 12px | 400 (Regular) | 18px | Normal |
| **Label Medium** | JetBrains Mono | 12px | 500 (Medium) | 16px | +0.02em |
| **Button** | Inter | 14px | 500 (Medium) | 20px | Normal |

---

## 4. Spacing, Shapes & Layout Rules

- **Base Unit:** 8px grid system (`xs: 4px`, `sm: 8px`, `md: 16px`, `lg: 24px`, `xl: 32px`).
- **Sidebar Width:** Fixed 260px width.
- **Top Bar Height:** Fixed 64px height with a subtle `1px solid #E2E8F0` bottom border.
- **Corner Radius:**
  - Cards, Modals, Inputs, Buttons: `8px` (`rounded-lg`)
  - Badges, Tags, Pills: `4px` (`rounded-sm`)
  - Full Circle / Avatars: `9999px` (`rounded-full`)
- **Elevation & Depth:**
  - Primary depth is achieved via **Tonal Layering** and `1px` borders (`#E2E8F0`).
  - Soft diffused shadows (`0px 4px 6px rgba(0,0,0,0.05)`) are restricted to floating elements (Modals & Popovers).
