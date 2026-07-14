---
name: Precision Archival
colors:
  surface: '#fff8f6'
  surface-dim: '#efd4d0'
  surface-bright: '#fff8f6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fff0ee'
  surface-container: '#ffe9e6'
  surface-container-high: '#fee2dd'
  surface-container-highest: '#f8dcd8'
  on-surface: '#261816'
  on-surface-variant: '#5a403c'
  inverse-surface: '#3d2c2a'
  inverse-on-surface: '#ffedea'
  outline: '#8e706b'
  outline-variant: '#e3beb8'
  surface-tint: '#b52619'
  primary: '#610000'
  on-primary: '#ffffff'
  primary-container: '#8b0000'
  on-primary-container: '#ff907f'
  inverse-primary: '#ffb4a8'
  secondary: '#5e5e5e'
  on-secondary: '#ffffff'
  secondary-container: '#e2e2e2'
  on-secondary-container: '#646464'
  tertiary: '#2b2c2c'
  on-tertiary: '#ffffff'
  tertiary-container: '#424242'
  on-tertiary-container: '#afaeae'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad4'
  primary-fixed-dim: '#ffb4a8'
  on-primary-fixed: '#410000'
  on-primary-fixed-variant: '#920703'
  secondary-fixed: '#e2e2e2'
  secondary-fixed-dim: '#c6c6c6'
  on-secondary-fixed: '#1b1b1b'
  on-secondary-fixed-variant: '#474747'
  tertiary-fixed: '#e3e2e2'
  tertiary-fixed-dim: '#c7c6c6'
  on-tertiary-fixed: '#1b1c1c'
  on-tertiary-fixed-variant: '#464747'
  background: '#fff8f6'
  on-background: '#261816'
  surface-variant: '#f8dcd8'
typography:
  headline-xl:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  panel-width-side: 280px
  panel-width-tools: 320px
  gutter: 1px
---

## Brand & Style

This design system is built for administrative precision and professional productivity. It targets power users in document management, legal, and architectural sectors who require high information density and structural clarity. The brand personality is authoritative, reliable, and meticulously organized.

The visual style follows a **Corporate / Modern** aesthetic with a lean toward **Minimalism**. It prioritizes a clear functional hierarchy over decorative elements. By utilizing a high-contrast palette of dark red and black against a sterile white background, the interface establishes a "clinical" efficiency that minimizes cognitive load during complex "maquetación" (layout) tasks. Visual depth is created through crisp borders and subtle tonal shifts rather than complex shadows.

## Colors

The palette is strictly functional. **Dark Red (#8B0000)** is used exclusively for primary actions, critical alerts, and high-level branding, ensuring these elements command immediate attention. **Black (#000000)** provides maximum contrast for text and structural navigation elements.

**Gray (#808080)** and its lighter variations serve as the "utility" colors for borders, inactive states, and secondary metadata. The background remains a pure **White (#FFFFFF)** to mimic the physical canvas of document pages, while a muted light gray is used for container backgrounds to distinguish sidebars and panels from the main workspace.

## Typography

The typography system is engineered for legibility across dense data sets. **Hanken Grotesk** is used for headlines to provide a sharp, contemporary edge. **Inter** handles the bulk of the body content due to its exceptional readability and neutral tone.

For technical metadata and "Object Fields" (as seen in the sketch), **JetBrains Mono** is introduced to provide a clear distinction between user-generated content and system-level data or variables. Navigation and section headers utilize uppercase labels with slight tracking to enforce a rigid, organized structure.

## Layout & Spacing

This design system utilizes a **Fixed-Panel Fluid Grid**. The layout is divided into four distinct vertical zones as suggested by the sketch:
1.  **Global Navigation:** A slim left-hand rail for top-level module switching.
2.  **Asset/Page Manager:** A secondary panel for managing document structure and thumbnails.
3.  **The Canvas/Preview:** A fluid central area that expands to fill available space, dedicated to the "Document Preview."
4.  **Property Inspector:** A fixed right-hand panel for "Object Fields" and configuration.

Spacing follows a strict 4px base unit. To maximize the working area, gutters between major panels are reduced to 1px (lines) rather than wide whitespace, creating a "tiled" workspace typical of professional design tools.

## Elevation & Depth

Hierarchy is established through **Tonal Layering** and **Line Work** rather than shadows. 
- **Level 0 (Background):** The application shell and main canvas area.
- **Level 1 (Panels):** Sidebars use a very light gray background with 1px borders to separate them from the canvas.
- **Level 2 (Active Elements):** Active pages or selected blocks are highlighted with a 2px Dark Red border.
- **Overlays:** Modals or dropdown menus use a sharp, 1px black border with a subtle 4px blur shadow to indicate they are temporary and positioned above the workspace.

This approach ensures the UI feels "flat" and paper-like, consistent with a tool focused on document creation.

## Shapes

To maintain a professional and technical appearance, the design system uses "Soft" geometry. A radius of **4px (0.25rem)** is applied to buttons and input fields to prevent the interface from feeling overly aggressive, while larger components like page thumbnails or container cards use the same minimal rounding to preserve grid alignment. High-level branding elements or floating action buttons may use a pill shape for distinct visual contrast.

## Components

### Buttons
- **Primary:** Dark Red background, White text, 4px radius.
- **Secondary:** White background, 1px Black border, Black text.
- **Ghost:** No background, Black or Gray text, used for low-priority sidebar actions.

### Page Thumbnails (Maqueta Documento)
- Rectangular containers with a 1px gray border.
- Active state: 2px Dark Red border with a small red "tag" or index number.
- Drag handle icon visible on hover.

### Object Fields / Tree View
- Hierarchical list items with 16px indentations for nested "Fields."
- Folders use a solid Black icon; individual fields use a gray monospaced icon.
- Hover state: Light gray background fill (#F5F5F5).

### Input Fields
- Flush-bottom or fully outlined 1px gray borders.
- Labels are persistent, small, and uppercase (label-caps).
- Focus state: Border color changes to Dark Red.

### Page Canvas
- The "Page 1", "Page 2" blocks in the preview should have a subtle 1px gray border and a white fill to differentiate from the light gray workspace background.