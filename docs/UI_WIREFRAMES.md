# Kirdbyys UI Wireframes & Design System

## Design Philosophy

- **Dark-first**: professional photo editing aesthetic
- **Light mode**: optional for bright environments
- **Minimal chrome**: content (photos) takes priority
- **High information density**: scores, badges, and metadata are glanceable
- **Responsive**: works from 1280×720 up to 4K displays

## Color System

### Dark Mode
- Background: `#0B1120`
- Surface: `#0F172A`
- Surface 2: `#1E293B`
- Border: `#1E293B`
- Text: `#F8FAFC`
- Muted: `#94A3B8`
- Primary: `#F97316` (orange)
- Primary hover: `#FB923C`
- Success: `#22C55E`
- Warning: `#EAB308`
- Danger: `#EF4444`

### Light Mode
- Background: `#F8FAFC`
- Surface: `#FFFFFF`
- Surface 2: `#F1F5F9`
- Border: `#E2E8F0`
- Text: `#0F172A`
- Muted: `#64748B`
- Primary: `#F97316`
- Success: `#22C55E`
- Warning: `#EAB308`
- Danger: `#EF4444`

## Layout

```
+--------------------------------------------------+
|  [Logo] Kirdbyys      [Theme] [Status: CPU Ready]|
+----------+---------------------------------------+
|          |                                       |
|  NAV     |           MAIN CONTENT AREA           |
|          |                                       |
|  · Dash  |                                       |
|  · Projs |                                       |
|  · Import|                                       |
|  · Rank  |                                       |
|  · Dup   |                                       |
|  · Export|                                       |
|          |                                       |
|  [Job    |                                       |
|   Card]  |                                       |
|          |                                       |
+----------+---------------------------------------+
```

## Views

### 1. Dashboard
- Hero card with CTA: Create Project / Quick Import
- Stats cards: Projects, Images Analyzed, Selected, Duplicates
- Recent projects list (cards)

### 2. Projects
- Grid of project cards
- Name, sport, source folder, status badge
- Click to open

### 3. Import
- Large drag-and-drop zone
- Supported formats note
- Target project dropdown
- Browse folder button

### 4. Rankings
- Toolbar: sort dropdown, top-N selector, selected-only toggle
- Weights panel: 4 sliders (Technical, Action, Story, Composition) + Re-rank button
- Gallery of photo cards with rank badge, score badge, filename, moments tags
- Click card → detail modal

### 5. Duplicates
- List of duplicate/burst groups
- Each group shows representative + alternatives
- Representative highlighted with primary border

### 6. Export
- Mode dropdown (copy/move/CSV/Excel/XMP/PDF)
- Top-N input
- Destination folder input (for copy/move)
- Result panel with path and count

## Components

### Photo Card
```
+----------------------------+
| [Rank #]      [Score 89.2] |
|                            |
|        [THUMBNAIL]         |
|                            |
| filename.jpg               |
| T 82 · A 91 · S 88 · C 74  |
| [GOAL] [CELEBRATION]       |
+----------------------------+
```

### Detail Modal
```
+--------------------------------------+
|  ×                                  |
|  +----------------+  +------------+|
|  |                |  | Filename   ||
|  |   PREVIEW      |  | Score Rings||
|  |                |  | Explanation||
|  |                |  | Moments    ||
|  |                |  | Technical  ||
|  |                |  | Action     ||
|  |                |  | Composition||
|  |                |  | [Select]   ||
|  +----------------+  +------------+|
+--------------------------------------+
```

### Score Ring
- Circular progress indicator (SVG)
- Shows value 0–100
- Label below

### Job Card (Sidebar)
- Title: current job type
- Progress bar
- Meta: status, processed/total, message

## Interactions

- Hover photo card: lift + border highlight
- Click photo card: open detail modal
- Drag images/folder onto import zone: highlight zone
- Change weight slider: instant label update; re-rank requires button click
- Toggle theme: instant global swap, logo switches between SVG variants

## Responsive Behavior

- Sidebar collapses to icons on narrow screens
- Gallery columns reduce from 5 to 2 as width decreases
- Modal becomes vertical stack on mobile

## Accessibility

- All interactive elements have focus states
- Buttons have aria-labels
- Color contrast meets WCAG AA
- Keyboard navigation for modal close and actions
