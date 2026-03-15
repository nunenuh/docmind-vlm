# User Interface Specification: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Product Definition

---

## 1. Design System & Language

- **Theme:** Modern, professional, dark mode primary with light mode option
- **Primary Color:** Indigo (#4F46E5) — action buttons, active states, links
- **Secondary Color:** Slate (#64748B) — backgrounds, secondary text
- **Success/Confidence High:** Emerald (#10B981)
- **Warning/Confidence Medium:** Amber (#F59E0B)
- **Error/Confidence Low:** Rose (#F43F5E)
- **Typography:** Inter (UI) / JetBrains Mono (code/JSON output)
- **Component Library:** shadcn/ui (Tailwind-based, composable, accessible)
- **Icons:** Lucide React

## 2. Page Structure

### 2.0 Landing Page (Public — No Auth)

```
+--------------------------------------------------+
|  Nav: Logo        [Try it Free]  [GitHub] [Theme] |
+--------------------------------------------------+
|                                                    |
|  HERO SECTION                                      |
|  "Chat with any document.                          |
|   See exactly what the AI sees."                   |
|                                                    |
|  [Try it Free — Google]  [Try it Free — GitHub]    |
|                                                    |
|  [ Animated demo preview / auto-play video ]       |
|  (showing: upload → extract → overlay → chat)      |
|                                                    |
+--------------------------------------------------+
|                                                    |
|  FEATURE SHOWCASE (4 sections, alternating layout) |
|                                                    |
|  1. EXTRACT        |  [visual: messy scan →        |
|  "Upload any doc.  |   structured JSON output      |
|   Get structured   |   with confidence badges]     |
|   data instantly." |                               |
|                                                    |
|  [visual: heatmap  |  2. UNDERSTAND                |
|   on document]     |  "See where the AI is         |
|                    |   confident — and where        |
|                    |   it's not."                   |
|                                                    |
|  3. COMPARE        |  [visual: side-by-side         |
|  "Raw VLM vs       |   with diff highlights]        |
|   enhanced. See    |                               |
|   the difference." |                               |
|                                                    |
|  [visual: chat     |  4. CHAT                       |
|   with citations]  |  "Ask questions. Get answers   |
|                    |   with source citations."      |
|                                                    |
+--------------------------------------------------+
|                                                    |
|  HOW IT WORKS (horizontal 4-step flow)             |
|  [Upload] → [Extract] → [Verify] → [Chat]         |
|  with icons and one-line descriptions              |
|                                                    |
+--------------------------------------------------+
|                                                    |
|  BUILT WITH (tech badges)                          |
|  Qwen3-VL | LangGraph | FastAPI | React | Supabase|
|                                                    |
+--------------------------------------------------+
|                                                    |
|  WHY DIFFERENT (moat statement)                    |
|  "7 years of production OCR meets modern VLMs.     |
|   We know when the AI is wrong."                   |
|                                                    |
|  [Try it Free — Google]  [Try it Free — GitHub]    |
|                                                    |
+--------------------------------------------------+
|  Footer: GitHub | MIT License | nunenuh.me | 2026  |
+--------------------------------------------------+
```

**Design notes:**
- Feature sections use alternating text-left/image-right and image-left/text-right layout for visual rhythm
- Hero demo preview: ideally an animated GIF or short looping video showing the real product
- All visuals use actual product screenshots, not stock illustrations
- Dark mode by default for technical credibility; light mode toggle available
- Smooth scroll animations on feature sections (intersection observer, subtle fade-in)

### 2.1 Login Page
- Centered card with DocMind-VLM logo and tagline
- Two buttons: "Continue with Google" / "Continue with GitHub"
- Clean, minimal — no distractions
- Note: Login may be triggered directly from landing page CTA buttons (redirect to Supabase OAuth flow, then back to dashboard)

### 2.2 Dashboard (Document List)
- Top bar: logo, user avatar/menu, theme toggle
- Main area: grid of document cards showing:
  - Thumbnail (first page preview)
  - Filename, upload date, document type (if detected)
  - Processing status badge: uploading / processing / ready / error
- Upload area: prominent drag-and-drop zone at top or empty state
- Pre-loaded demo documents marked with a "Demo" badge

### 2.3 Document Workspace (Main View)
Split-panel layout — the core of the application:

```
+--------------------------------------------------+
|  Top Bar: document name | mode toggle | export    |
+------------------------+-------------------------+
|                        |                         |
|   Document Viewer      |   Results Panel         |
|   (left panel)         |   (right panel)         |
|                        |                         |
|   - Rendered document  |   Tab 1: Extraction     |
|   - Confidence overlay |     - Fields list       |
|     (togglable)        |     - JSON view         |
|   - Zoom/pan controls  |                         |
|   - Page navigation    |   Tab 2: Chat           |
|                        |     - Message thread     |
|                        |     - Input box          |
|                        |                         |
|                        |   Tab 3: Audit           |
|                        |     - Pipeline steps     |
|                        |     - Per-field detail   |
|                        |                         |
|                        |   Tab 4: Compare         |
|                        |     - Side-by-side diff  |
|                        |                         |
+------------------------+-------------------------+
|  Status bar: processing progress / pipeline step  |
+--------------------------------------------------+
```

### 2.4 Document Viewer (Left Panel)
- Rendered document image with zoom and pan (mouse wheel + drag)
- Page navigation for multi-page documents
- Toggle buttons: "Confidence Overlay" (heatmap on/off), "Show Regions" (bounding boxes on/off)
- Clicking a region highlights the corresponding field in the Results Panel
- Hovering a low-confidence region shows tooltip with reason

### 2.5 Results Panel — Extraction Tab (Right Panel)
- Two view modes: "Fields" (structured list) and "JSON" (raw output)
- Fields view: table with columns: Field Name, Value, Confidence (badge), Source (clickable link)
- Clicking "Source" scrolls the Document Viewer to the field's bounding box and highlights it
- Template mode: required fields missing shown with yellow warning row
- Export buttons: "Download JSON" / "Download CSV"

### 2.6 Results Panel — Chat Tab
- Message thread (scrollable, newest at bottom)
- Each assistant message includes citation blocks:
  - Clickable reference: "[Page 1, Region 3]" → scrolls Document Viewer to cited area
  - Inline text span quote in a subtle callout
- Input box at bottom with send button
- "Copy Summary" button at top of chat

### 2.7 Results Panel — Audit Tab
- Pipeline timeline: vertical list of processing steps with timing
  - "Image quality analysis — 0.3s"
  - "Deskew correction (4.2 degrees) — 0.1s"
  - "VLM extraction (Qwen3-VL) — 2.1s"
  - "Post-processing — 0.2s"
- Per-field audit: click any field to see its full provenance chain

### 2.8 Results Panel — Compare Tab
- Side-by-side layout: "Raw VLM" (left) vs "DocMind-VLM" (right)
- Color-coded diff: blue (corrected), green (added by enhanced pipeline), gray (unchanged)
- Summary stats at top: "X fields corrected, Y fields added, Z fields unchanged"

## 3. UI Flow

```
Login → Dashboard → Upload Document → Processing (progress bar)
  → Document Workspace opens automatically
    → Extraction tab shown by default
    → User switches to Chat / Audit / Compare tabs as needed
    → Export from any tab
```

## 4. Responsive Behavior

- **Desktop (> 1024px):** Full split-panel layout as described above
- **Tablet (768–1024px):** Stacked layout — Document Viewer on top, Results Panel below (tabbed)
- **Mobile (< 768px):** Not primary target, but functional — single column, toggle between viewer and results

---
#ui-spec #visual-design #interface #docmind-vlm
