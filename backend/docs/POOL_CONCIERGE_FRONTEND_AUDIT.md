# Pool Concierge — Frontend Design Audit (2026-04-15)

Verdict: **RED** — not portfolio-ready as-is. Top 5 fixes get to YELLOW; original hero visual gets to GREEN.

## Top 5 must-fix (highest impact)

1. **Hero is generic** — `pool-concierge-landing/components/Hero.tsx` is the cliché it warned against (centered headline + gradient blob + italic serif + pill input). Replace with editorial split: headline left, **live before/after preview right** that proves the promise above the fold.
2. **Viewer HUD doesn't match brand** — `pool-concierge-viewer/src/App.tsx:97-132` renders dark-navy debug HUD with "renderer: pascal" exposed. Adopt landing's water-tinted glass + Fraunces/Inter fonts + water-500 accents.
3. **Semantic HTML wrong top-to-bottom** — `app/page.tsx` puts `<Footer>` inside `<main>`; `Hero.tsx` puts `<nav>` inside its `<section>` instead of a top-level `<header>`; no section has `aria-labelledby`. Restructure to `<header><nav/></header> <main>...</main> <footer/>`.
4. **Image + font perf** — `DemoPreview.tsx:22-30,37-45` uses raw `<img>` with no width/height (causes CLS); `globals.css:1` loads Google Fonts via `@import` (render-blocking). Convert to `next/image` + `next/font/google`.
5. **Viewer camera frames the lot, not the pool** — `pool-concierge-viewer/src/scene/from-listing.ts:83-97` aims at lot centroid. Weight target ~0.65 toward `poolCenterWorld` so frame 1 actually shows the pool.

## Landing — anti-template / opinionated design
- HIGH `Hero.tsx:6-34` — cliché hero (see #1).
- HIGH `HowItWorks.tsx:41-68` — uniform shadcn 3-card grid; switch to alternating split or bento with step 2 (the render) dominant.
- HIGH `DemoPreview.tsx:20-47` — money moment styled identically to stock photos. Add a slider handle (drag-to-reveal) or hover-animated caustic overlay.
- MEDIUM `FAQ.tsx:28-55` — `<details>` lacks open-state visual personality. Add left-accent bar + water-100 tint on open panel.

## Landing — semantic / a11y
- CRITICAL `app/page.tsx:10-17` — `<Footer>` inside `<main>`; no top-level `<header>`. Restructure.
- HIGH every `<section>` — missing `aria-labelledby`. Add `id` to each `<h2>` + `aria-labelledby` to its section.
- HIGH `WaitlistForm.tsx:82-101,108-111,50-67` — error msg + success state not announced. Add `role="alert"`/`aria-live="polite"`, `aria-invalid`, `aria-describedby`.
- HIGH `WaitlistForm.tsx:74` — focus not moved to success message. `ref.focus()` on transition.
- HIGH `FAQ.tsx:42` — `<summary>` `list-none` inconsistent across browsers. Add `summary::-webkit-details-marker { display:none }` to globals.css.
- CRITICAL contrast — `Hero.tsx:29` + `CTAFooter.tsx:13` — `text-water-700` italic over translucent water gradient may dip below 4.5:1. Verify; if failing shift to `water-800`.
- MEDIUM `globals.css:108-114` — `prefers-reduced-motion` doesn't disable Tailwind animations from `tailwind.config.ts:28-40`. Wrap config animation keyframes with `@media (prefers-reduced-motion: no-preference)`.

## Landing — frontend correctness
- HIGH `globals.css:1` — Google Fonts via `@import` is render-blocking. Move to `next/font/google` in `app/layout.tsx`.
- HIGH `DemoPreview.tsx:22-30,37-45` — `<img>` without dimensions → CLS. Use `next/image` with explicit `width`/`height`.
- HIGH `Footer.tsx:35` — Personal "Built by Madhav Chauhan" undermines product brand. Move to `/about` or aria-label credit.
- MEDIUM `Footer.tsx:18` — Personal Gmail in product footer. Use `hello@poolconcierge.com` and route server-side.
- MEDIUM `tailwind.config.ts:28-40` — `animate-shimmer`/`animate-float` defined but unused (hand-rolled CSS classes used instead). Pick one; delete the other.
- MEDIUM `WaitlistForm.tsx:28,97` — Pre-filled `"75024"` looks pre-validated. Either drop the field ("Plano 75024 pilot") or move to `placeholder=""`.

## Landing — design system
- MEDIUM `globals.css` vs `tailwind.config.ts` — Tokens split between Tailwind palette + hardcoded CSS. Consolidate `--water-glow`, easings, durations into `:root`.
- MEDIUM no `--ease-out-expo` / duration tokens. Magic `transition-all duration-300` everywhere.

## 3D viewer
- CRITICAL `App.tsx:97-132` — Dark-navy debug HUD doesn't match landing brand. Adopt landing's `.glass-card` style + Fraunces/Inter fonts.
- HIGH `index.html:16` + `App.tsx:64` — `#e8f0fa` body vs `#dfeaf5` canvas color mismatch reads accidental.
- HIGH `App.tsx:105-131` — "renderer: pascal/fallback — {err.message}" is dev debug exposed to end user. Replace with product affordance ("Interactive 3D" vs "Static preview").
- CRITICAL `App.tsx:107-132` — Fixed-position `<div>` overlay no semantic role. Title "Pool Concierge Viewer" should be `<h1>` in `<header>`.
- HIGH `App.tsx:134-151` — `LoadingHud` no `aria-live`. Wrap in `<div role="status" aria-live="polite">`.
- HIGH `index.html:27` — `body { overflow: hidden }` + no keyboard scroll. OrbitControls keyboard not enabled (`App.tsx:84-91`).
- HIGH Canvas no fallback text. Add `aria-label="3D rendering of {address} backyard with proposed pool"`.
- HIGH `from-listing.ts:83-97` — Camera frames lot centroid not pool (see #5).
- HIGH `App.tsx:35-47` — WebGPU silent fallback leaks raw error text via `note` prop. Separate user message from dev error.
- HIGH `App.tsx:3` — `@react-three/drei` (OrbitControls/Sky/Environment) imported eagerly. `<Environment preset="city">` triggers HDR fetch even on Pascal happy path. Dynamic import inside fallback branch only.
- MEDIUM `pool-mesh.tsx:35-64` + `house-fallback.tsx:30,74,84` — `useMemo` Three geometries leak GPU memory on unmount. Add `.dispose()` cleanup or `<primitive>` attach.
- MEDIUM `from-listing.ts:50,68` — No polygon validation (closed/non-empty). `planToWorld`/`bbox` will throw. Add input validation per `common/coding-style.md`.
- MEDIUM `pool-mesh.tsx:149` — `buildKidney` is a "dented circle" approximation. Document or use real SVG path for true kidney shape.

## Brand consistency (cross-cutting)
- CRITICAL Viewer + landing read as two different products. Same fonts (self-host Fraunces/Inter in viewer), same glass card style, same water-500 accent color.
