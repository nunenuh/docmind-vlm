# User Experience Specification: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Product Definition

---

## 1. Interaction Principles

### Speed & Responsiveness
- **Upload:** Instant feedback — progress bar appears immediately on drop/select
- **Processing:** Step-by-step progress updates (not a single spinner) — user sees each pipeline stage complete in real time
- **Chat:** Response streaming — text appears word-by-word, not after a long wait
- **Navigation:** Tab switching, zoom, pan — all < 100ms (client-side, no server roundtrip)

### Transparency as UX
- **Show the pipeline:** The processing progress is not just a loading bar — it names each step ("Analyzing image quality", "Correcting 4.2-degree skew", "Extracting with Qwen3-VL"). This IS the product's moat made visible.
- **Show confidence:** Never present extraction results as absolute truth. Every field has a confidence badge. This builds trust through honesty.
- **Show provenance:** One click from any extracted field to its source in the document. No "trust me" moments.

### Progressive Disclosure
- **Default view:** Clean extraction results with confidence badges — simple, scannable
- **One click deeper:** Audit trail per field — for users who want to verify
- **Compare tab:** Pipeline comparison — for technical evaluators (hiring managers) who want to see the engineering depth
- Don't overwhelm on first interaction; let users drill down when they want

### Direct Manipulation
- **Click field → highlight source:** Extracted field and document region are visually linked
- **Click citation → scroll to source:** Chat citations navigate the document viewer
- **Toggle overlay:** One button to show/hide confidence heatmap — user controls the information density

## 2. Feedback & Status Communication

| Action | Feedback |
|---|---|
| File dropped on upload zone | Zone highlights, filename appears, progress bar starts |
| Upload complete | Checkmark animation, processing begins automatically |
| Processing step completes | Step shows green check, next step activates, progress bar advances |
| Processing error | Red alert with specific step that failed and a human-readable error message |
| Field clicked | Source region highlights in document viewer with a smooth scroll/zoom |
| Chat message sent | Message appears in thread, typing indicator shows, response streams in |
| Export clicked | Brief download animation, file saves to browser downloads |

## 3. Accessibility (a11y)

- **Color independence:** Confidence indicators use both color AND text/icons (green checkmark, yellow warning, red exclamation) — never color alone
- **Keyboard navigation:** All interactive elements reachable via Tab key; Enter/Space to activate
- **Screen reader support:** ARIA labels on all buttons, meaningful alt text on document viewer, live regions for processing updates
- **Contrast:** All text meets WCAG AA contrast ratios (4.5:1 minimum)
- **Focus indicators:** Visible focus ring on all interactive elements

## 4. Error Recovery

### Upload Errors
- **File too large:** "This file is 25MB — the maximum is 20MB. Try compressing the PDF or reducing image resolution."
- **Wrong format:** "This file type (.docx) isn't supported yet. Please convert to PDF first."
- **Network failure:** "Upload interrupted. Click to retry." (file is kept in browser memory)

### Processing Errors
- **DashScope API failure:** "Document extraction service is temporarily unavailable. Your document is saved — click 'Retry' to try again."
- **Timeout:** "Processing took longer than expected. This may happen with very complex documents. Click 'Retry' or try a simpler scan."
- **Partial extraction:** If some fields extracted before error, show what was recovered: "Partial results available — X of Y fields extracted before an error occurred."

### Chat Errors
- **API failure:** "Couldn't generate a response. Click to retry your last question."
- **Ungrounded answer:** If the LangGraph agent cannot find evidence in the document, respond: "I couldn't find information about that in this document. Try rephrasing your question or check if the relevant section is visible in the scan."

## 5. First-Time User Experience

### Demo Documents
- On first login, dashboard shows 3 pre-loaded demo documents with "Demo" badges:
  1. **Scanned multilingual certificate** — English + Bahasa Indonesia, slightly skewed
  2. **Invoice with complex table** — nested line items, tax calculations
  3. **Low-quality receipt photo** — tilted, partially cut off, mixed language
- Each demo document has pre-computed raw VLM baseline for comparison view
- Tooltip on first visit: "Try one of these demo documents to see DocMind-VLM in action"

### Guided First Interaction
- After first extraction completes, subtle callouts highlight key features:
  - "Click any field to see where it came from in the document"
  - "Toggle the confidence overlay to see which areas need attention"
  - "Switch to the Chat tab to ask questions about this document"
- These callouts appear once per user, then never again

## 6. Performance Perception

- **Skeleton loading:** Show layout skeleton while data loads (not blank white)
- **Optimistic updates:** Chat message appears in thread immediately on send (before response)
- **Progressive rendering:** Extraction results appear as they're ready (streaming from backend), not all at once
- **Smooth animations:** Transitions between tabs, panel resizing, overlay toggle — 200ms ease-in-out

---
#ux-spec #usability #interaction-design #docmind-vlm
