# Issue #25: Landing Page — Full Implementation

## Summary

Implement the complete public landing page with five sections: Hero (headline, subheadline, dual CTA buttons), Features (4 feature showcase cards with alternating layout), Demo (screenshot/video placeholder with auto-play), TechStack (logo/badge grid), HowItWorks (4-step horizontal flow), and Footer (GitHub, author, license links). All sections must be responsive across desktop, tablet, and mobile breakpoints. No authentication required. Uses shadcn/ui Card and Button components with Lucide icons.

## Context

- **Phase**: 6 — Frontend
- **Priority**: P0
- **Labels**: `phase-6-frontend`, `frontend`, `tdd`
- **Dependencies**: None (landing page is public, no auth needed)
- **Branch**: `feat/25-landing-page`
- **Estimated scope**: M

## Specs to Read

- `specs/frontend/components.md` — Component tree, shadcn/ui setup, file conventions
- `specs/frontend/state.md` — No server state needed for landing page
- `docs/blueprint/02-product/user-interface-specification.md` — Section 2.0 Landing Page layout
- `docs/blueprint/02-product/acceptance-criteria-specification.md` — AC 0.1 through AC 0.10

## Current State (Scaffold)

All landing page components are empty stubs returning placeholder text:

**File: `frontend/src/pages/LandingPage.tsx`**
```typescript
export function LandingPage() {
  return <div className="min-h-screen flex items-center justify-center"><h1 className="text-2xl font-bold">DocMind-VLM</h1></div>;
}
```

**File: `frontend/src/components/landing/Hero.tsx`**
```typescript
export function Hero() {
  return <div>Hero</div>;
}
```

**File: `frontend/src/components/landing/Features.tsx`**
```typescript
export function Features() {
  return <div>Features</div>;
}
```

**File: `frontend/src/components/landing/Demo.tsx`**
```typescript
export function Demo() {
  return <div>Demo</div>;
}
```

**File: `frontend/src/components/landing/Footer.tsx`**
```typescript
export function Footer() {
  return <div>Footer</div>;
}
```

**Missing files that need to be created:**
- `frontend/src/components/landing/TechStack.tsx`
- `frontend/src/components/landing/HowItWorks.tsx`
- `frontend/src/components/landing/Navbar.tsx`

## Requirements

### Functional

1. **Navbar**: Fixed top bar with logo text ("DocMind-VLM"), "Try it Free" CTA button, GitHub icon link, theme toggle placeholder.
2. **Hero**: Full-viewport-height section with:
   - Headline: "Chat with any document. See exactly what the AI sees."
   - Subheadline: brief value proposition paragraph
   - Two CTA buttons: "Try it Free — Google" and "Try it Free — GitHub" (link to `/dashboard` or trigger auth)
   - Animated demo preview placeholder (div with aspect ratio, can be image/video later)
3. **Features**: 4 feature cards in alternating text-left/image-right layout:
   - Extract: "Upload any doc. Get structured data instantly."
   - Understand: "See where the AI is confident — and where it's not."
   - Compare: "Raw VLM vs enhanced. See the difference."
   - Chat: "Ask questions. Get answers with source citations."
4. **HowItWorks**: Horizontal 4-step flow: Upload -> Extract -> Verify -> Chat, with icons and one-line descriptions.
5. **TechStack**: Badge grid showing: Qwen3-VL, LangGraph, FastAPI, React, Supabase.
6. **Footer**: GitHub repo link, MIT License notice, author website (nunenuh.me), year 2026.
7. No authentication or API calls on this page.

### Non-Functional

- Lighthouse performance score > 90 (AC 0.1)
- Page loads in < 1.5 seconds
- Fully responsive: desktop (> 1024px), tablet (768-1024px), mobile (< 768px)
- Smooth scroll between sections
- Dark mode primary, light mode toggle available
- Accessible: proper heading hierarchy, alt text on images, keyboard-navigable

## Implementation Plan

### Component Tree

```
LandingPage.tsx
├── Navbar.tsx              (fixed top)
├── Hero.tsx                (full viewport height)
├── Features.tsx            (4 alternating sections)
├── HowItWorks.tsx          (horizontal step flow)
├── Demo.tsx                (screenshot/video placeholder)
├── TechStack.tsx           (badge grid)
└── Footer.tsx              (links + copyright)
```

### Key Components

**`frontend/src/components/landing/Navbar.tsx`** (new file):
```typescript
interface NavbarProps {
  // No props needed — self-contained
}

export function Navbar() {
  return (
    <nav className="fixed top-0 w-full z-50 border-b bg-background/80 backdrop-blur-sm">
      <div className="container mx-auto flex items-center justify-between h-14 px-4">
        <span className="text-lg font-bold">DocMind-VLM</span>
        <div className="flex items-center gap-3">
          <a href="https://github.com/nunenuh/docmind-vlm" target="_blank" rel="noopener noreferrer">
            {/* GitHub icon from Lucide */}
          </a>
          <Button asChild>
            <a href="/dashboard">Try it Free</a>
          </Button>
        </div>
      </div>
    </nav>
  );
}
```

**`frontend/src/components/landing/Hero.tsx`**:
```typescript
interface HeroProps {
  // No props — self-contained section
}

export function Hero() {
  return (
    <section className="min-h-screen flex flex-col items-center justify-center text-center px-4 pt-14">
      <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
        Chat with any document.
        <br />
        <span className="text-primary">See exactly what the AI sees.</span>
      </h1>
      <p className="mt-6 text-lg text-muted-foreground max-w-2xl">
        Upload PDFs and images. Extract structured data with confidence scores.
        Ask questions and get answers with source citations.
      </p>
      <div className="mt-8 flex flex-col sm:flex-row gap-4">
        <Button size="lg">Try it Free — Google</Button>
        <Button size="lg" variant="outline">Try it Free — GitHub</Button>
      </div>
      <div className="mt-12 w-full max-w-4xl aspect-video rounded-lg border bg-muted/50">
        {/* Demo preview placeholder — replace with screenshot/video */}
      </div>
    </section>
  );
}
```

**`frontend/src/components/landing/Features.tsx`**:
```typescript
interface Feature {
  title: string;
  description: string;
  icon: React.ReactNode;
  visual: React.ReactNode; // placeholder for screenshot
}

const FEATURES: Feature[] = [
  { title: "Extract", description: "Upload any doc. Get structured data instantly.", icon: <FileSearch />, visual: <div /> },
  { title: "Understand", description: "See where the AI is confident — and where it's not.", icon: <Eye />, visual: <div /> },
  { title: "Compare", description: "Raw VLM vs enhanced. See the difference.", icon: <GitCompare />, visual: <div /> },
  { title: "Chat", description: "Ask questions. Get answers with source citations.", icon: <MessageSquare />, visual: <div /> },
];

// Render alternating layout: odd index = text-left/image-right, even = image-left/text-right
```

**`frontend/src/components/landing/HowItWorks.tsx`** (new file):
```typescript
const STEPS = [
  { icon: <Upload />, title: "Upload", description: "Drop any PDF or image" },
  { icon: <Cpu />, title: "Extract", description: "AI extracts structured data" },
  { icon: <CheckCircle />, title: "Verify", description: "See confidence scores" },
  { icon: <MessageSquare />, title: "Chat", description: "Ask questions about your doc" },
];

export function HowItWorks() {
  return (
    <section className="py-24 px-4">
      <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
      <div className="flex flex-col md:flex-row items-center justify-center gap-8 max-w-4xl mx-auto">
        {STEPS.map((step, idx) => (
          <React.Fragment key={step.title}>
            <div className="flex flex-col items-center text-center gap-2">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">{step.icon}</div>
              <h3 className="font-semibold">{step.title}</h3>
              <p className="text-sm text-muted-foreground">{step.description}</p>
            </div>
            {idx < STEPS.length - 1 && <ArrowRight className="hidden md:block h-5 w-5 text-muted-foreground" />}
          </React.Fragment>
        ))}
      </div>
    </section>
  );
}
```

**`frontend/src/components/landing/TechStack.tsx`** (new file):
```typescript
const TECH = [
  { name: "Qwen3-VL", description: "Vision Language Model" },
  { name: "LangGraph", description: "Pipeline Orchestration" },
  { name: "FastAPI", description: "Backend Framework" },
  { name: "React", description: "Frontend Framework" },
  { name: "Supabase", description: "Auth + Database" },
];

export function TechStack() {
  return (
    <section className="py-16 px-4 bg-muted/30">
      <h2 className="text-2xl font-bold text-center mb-8">Built With</h2>
      <div className="flex flex-wrap justify-center gap-4 max-w-3xl mx-auto">
        {TECH.map((t) => (
          <Badge key={t.name} variant="secondary" className="px-4 py-2 text-sm">
            {t.name}
          </Badge>
        ))}
      </div>
    </section>
  );
}
```

**`frontend/src/pages/LandingPage.tsx`** (updated):
```typescript
import { Navbar } from "@/components/landing/Navbar";
import { Hero } from "@/components/landing/Hero";
import { Features } from "@/components/landing/Features";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Demo } from "@/components/landing/Demo";
import { TechStack } from "@/components/landing/TechStack";
import { Footer } from "@/components/landing/Footer";

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <Hero />
      <Features />
      <HowItWorks />
      <Demo />
      <TechStack />
      <Footer />
    </div>
  );
}
```

### shadcn/ui Components Needed

Run before implementing:
```bash
cd frontend
npx shadcn@latest add button badge card
```

### Layout Approach

- Use Tailwind CSS for all styling, no custom CSS files
- Container max-width with `container mx-auto` for consistent centering
- Sections separated by `py-24` padding
- Features use CSS grid: `grid md:grid-cols-2 gap-12` with alternating `order` classes
- Responsive: stack vertically on mobile, side-by-side on desktop
- Smooth scroll: add `scroll-smooth` to html element

## Acceptance Criteria

- [ ] Landing page loads without authentication (no redirect to login) — AC 0.10
- [ ] Hero section visible without scrolling with headline and CTA buttons — AC 0.2
- [ ] Demo preview placeholder visible within first scroll — AC 0.3
- [ ] Four feature sections present: Extract, Understand, Compare, Chat — AC 0.4
- [ ] "How It Works" section shows 4-step flow — AC 0.5
- [ ] Tech stack badges visible: Qwen3-VL, LangGraph, FastAPI, React, Supabase — AC 0.6
- [ ] At least two CTA buttons present (hero + bottom) — AC 0.7
- [ ] Footer has GitHub repo link and author website link — AC 0.8
- [ ] Page is responsive: mobile, tablet, desktop — AC 0.9
- [ ] Lighthouse performance score > 90 — AC 0.1
- [ ] Each component file is under 200 lines
- [ ] All components have proper TypeScript props interfaces

## Files Changed

- `frontend/src/pages/LandingPage.tsx` — compose all sections
- `frontend/src/components/landing/Navbar.tsx` — new file
- `frontend/src/components/landing/Hero.tsx` — implement from stub
- `frontend/src/components/landing/Features.tsx` — implement from stub
- `frontend/src/components/landing/HowItWorks.tsx` — new file
- `frontend/src/components/landing/Demo.tsx` — implement from stub
- `frontend/src/components/landing/TechStack.tsx` — new file
- `frontend/src/components/landing/Footer.tsx` — implement from stub

## Verification

```bash
cd frontend
npm run dev                 # Visual inspection at http://localhost:5173/
npm run typecheck           # No TypeScript errors
npm run lint                # No lint errors
npx lighthouse http://localhost:5173/ --output=json  # Performance > 90
# Manually resize browser for responsive checks at 320px, 768px, 1024px, 1440px
```
