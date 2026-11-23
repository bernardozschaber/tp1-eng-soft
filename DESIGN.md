---
name: BernoulliPay
description: A light, flat operations console for RPA payroll, cut in neutral grey and signed in verde Bernoulli.
colors:
  ink: "#171717"
  ink-secondary: "#5c5c5c"
  ink-subdued: "#737373"
  ink-inverse: "#ffffff"
  surface: "#f7f7f7"
  surface-hover: "#f0f0f0"
  container: "#ffffff"
  container-inset: "#f7f7f7"
  inverse: "#242424"
  inverse-hover: "#363636"
  focus-ring: "#363636"
  brand-tint: "#e6f5f4"
  brand-tint-deep: "#c9e9e6"
  brand: "#009e8e"
  brand-hover: "#038276"
  brand-ink: "#047569"
  link: "#047569"
  success: "#047569"
  destructive: "#c91313"
  border-secondary: "rgba(11, 11, 11, 0.1)"
  border-tertiary: "rgba(11, 11, 11, 0.08)"
  tint-red: "#fff1f0"
  tint-blue: "#eff8ff"
  tint-yellow: "#fffaeb"
  tint-gray: "#f0f0f0"
  badge-red: "#c91313"
  badge-blue: "#175cd3"
  badge-yellow: "#b54708"
  categorical-1: "#009e8e"
  categorical-2: "#255ebc"
  categorical-3: "#934f00"
  categorical-4: "#5f8df3"
  categorical-5: "#ca7500"
  categorical-6: "#8a4a71"
  categorical-7: "#2783b2"
  categorical-8: "#b1614b"
typography:
  hero:
    fontFamily: "IBM Plex Sans, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 500
    lineHeight: 1.15
    letterSpacing: "-0.01em"
    fontFeature: "tabular-nums"
  display:
    fontFamily: "IBM Plex Sans, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 500
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "IBM Plex Sans, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "normal"
  metric:
    fontFamily: "IBM Plex Sans, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "normal"
    fontFeature: "tabular-nums"
  title:
    fontFamily: "IBM Plex Sans, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "normal"
  body:
    fontFamily: "IBM Plex Sans, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "IBM Plex Sans, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  column-header:
    fontFamily: "IBM Plex Sans, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "0.04em"
  numeric:
    fontFamily: "IBM Plex Mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tabular-nums"
rounded:
  md: "8px"
  lg: "10px"
  xl: "12px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  gutter: "20px"
components:
  button-primary:
    backgroundColor: "{colors.inverse}"
    textColor: "{colors.ink-inverse}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "8px 12px"
  button-primary-hover:
    backgroundColor: "{colors.inverse-hover}"
  button-secondary:
    backgroundColor: "{colors.container}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "8px 12px"
  button-secondary-hover:
    backgroundColor: "{colors.container-inset}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "8px 12px"
  button-ghost-hover:
    backgroundColor: "{colors.surface-hover}"
    textColor: "{colors.ink}"
  button-danger:
    backgroundColor: "{colors.container}"
    textColor: "{colors.destructive}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "8px 12px"
  button-danger-hover:
    backgroundColor: "{colors.tint-red}"
  button-sm:
    typography: "{typography.numeric}"
    rounded: "{rounded.md}"
    padding: "4px 10px"
  icon-button:
    backgroundColor: "transparent"
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.md}"
    height: "32px"
    width: "32px"
  card:
    backgroundColor: "{colors.container}"
    textColor: "{colors.ink}"
    rounded: "{rounded.xl}"
    padding: "16px"
  metric:
    backgroundColor: "{colors.container}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "12px 16px"
  field:
    backgroundColor: "{colors.container}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  select:
    backgroundColor: "{colors.container}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 28px 8px 12px"
  badge:
    backgroundColor: "{colors.tint-gray}"
    textColor: "{colors.ink-secondary}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  badge-brand:
    backgroundColor: "{colors.brand-tint}"
    textColor: "{colors.brand-ink}"
  badge-error:
    backgroundColor: "{colors.tint-red}"
    textColor: "{colors.badge-red}"
  badge-info:
    backgroundColor: "{colors.tint-blue}"
    textColor: "{colors.badge-blue}"
  badge-warning:
    backgroundColor: "{colors.tint-yellow}"
    textColor: "{colors.badge-yellow}"
  alert-success:
    backgroundColor: "{colors.brand-tint}"
    textColor: "{colors.brand-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "10px 14px"
  table-header:
    backgroundColor: "{colors.container-inset}"
    textColor: "{colors.ink-secondary}"
    typography: "{typography.column-header}"
    padding: "10px 12px"
  nav-item:
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.md}"
    height: "32px"
    width: "32px"
  nav-item-active:
    backgroundColor: "{colors.container}"
    textColor: "{colors.ink}"
  dropzone:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.xl}"
    padding: "40px 16px"
---

# Design System: BernoulliPay

## Overview

**Creative North Star: "The Ledger Signed in Verde"**

BernoulliPay is a near-achromatic operations console that carries exactly one colour of its own.
The neutral scale, spacing rhythm and shadow structure came from a port of the Maybe design
system and remain the working chassis — the token file still says so in its first line, and
components still carry donor names in comments (*"Stat block (net worth style)"*, *"Weight bar
(asset allocation style)"*). The colour identity is no longer borrowed. Every chromatic token
in the build is now derived from **verde Bernoulli (#009E8E)**, Colégio Bernoulli's own brand
colour, or chosen to sit beside it. The decorative leftovers of the donor palette — violet,
cyan, pink, orange, fuchsia, indigo, standalone blue — are deleted from the token file, not
merely unused.

The personality is administrative rather than expressive, and the brand is applied with
deliberate restraint: it appears in six places and nowhere else. The logomark, the active
navigation indicator, the trend chart's stroke and gradient, positive badges and alerts,
legend and status dots, and links. Everything else is grey. Density is high and
unapologetically desktop-first — a 240px nav rail (200px from 1024px down, icon-only at
64px below 480px) and a single full-height white card holding the work. Depth is almost entirely absent: a one-pixel
alpha-black hairline plus a barely-there shadow is the whole elevation vocabulary, so
hierarchy comes from tonal steps (page grey → card white → inset grey) and from typographic
weight, not from lifting things off the page.

One contrast fact governs the whole palette and is written into the token file itself:
**#009E8E is 3.34:1 on white.** It is a fill, stroke and mark colour and is never text on a
light surface. Text that must read as brand uses `--color-brand-700` (#047569, 5.59:1 on white
and 4.99:1 on the brand-50 tint). That single number is why the primary button did not turn
teal at the rebrand and why links, success text and positive badge ink all land on the 700 step
rather than the 500.

**Key Characteristics:**
- Two themes, one identity: light is the default `:root`; `[data-theme="dark"]` re-points the
  same semantic names rather than introducing a second vocabulary. Verde Bernoulli is lifted
  (`#00b8a5`) to hold its own on a dark ground; nothing else about the system's logic changes.
- Neutral greys carry the whole interface; verde Bernoulli is the only identity colour.
- The brand is a fill/stroke/mark; brand *text* is always the darker 700 step.
- Flat by default — hairline borders and 1px/6%-black shadows, never lifted panels.
- Money and counts are monospaced and tabular-aligned; prose is not.
- Desktop-first density: nav rail plus one content column, the rail narrowing in place —
  never a drawer — down to a phone width.
- Every icon is inline Lucide SVG rendered by a template tag; there is no icon font and no
  Unicode glyph stands in for one.

## Identity

### The institutional anchor

BernoulliPay is an internal tool of Colégio Bernoulli, and the brief was that it must read
as one. The school's own mark is a filled teal disc carrying a white infinity symbol beside
the word "Bernoulli", with "Colégio" set below it, also in white. Two things in that mark are
load-bearing and were treated as given:

- **The colour.** "Verde Bernoulli", `#009E8E`, is the institution's brand colour. It is not a
  palette choice this product gets to make.
- **The infinity.** The lemniscate is the school's defining motif — a Bernoulli signature in
  the mathematical sense as much as the institutional one.

Everything chromatic in this system is derived from that colour or chosen to sit beside it.

### The constraint that shaped the whole system

`#009E8E` measures **3.34:1 against white**. It clears the 3:1 floor for non-text graphics and
fails the 4.5:1 floor for text. That single number decided more than the logo:

- the mark, the chart stroke, the active nav indicator and the status dots may all be verde;
- links, positive trend figures and badge ink may not, and resolve to `#047569` instead;
- the primary button stayed dark neutral rather than turning verde, because white on `#009E8E`
  would fail button-text contrast.

The rule is written into `tokens.css` itself so it survives the next edit: **verde is a fill,
a stroke and a mark, never text on a light surface.**

### The constraint nobody would guess from the result

The brief carried an explicit **anti-reference: it must not look like PicPay.**

That is not a stylistic preference, it is a collision risk. PicPay is one of Brazil's
best-known payment apps, it is green, and it shares the initials. A green Brazilian payment
product built around a P was one careless decision away from reading as a knock-off of it.
Every round of generation carried that exclusion, and it is the reason the mark leans on the
lemniscate — the school's own motif — rather than on a stylised letter, which is the space
PicPay already occupies.

### Ideation — two rounds, two tools

The identity was not generated once. It went through two distinct rounds, under two different
product names and two different tools, and the second only makes sense because of the first.

**Round 1 — v0.app, while the product was still "ProvaPay".**
The brief described Colégio Bernoulli's own mark as the anchor and asked for ten concepts
combining two "P"s, the infinity motif, a minimalist treatment and verde Bernoulli, with the
PicPay exclusion stated. v0 generated the ten and then built a **side-by-side comparison
gallery** so they could be judged against each other rather than in sequence — the directions
explored were:

| # | Direction |
|---|---|
| 1 | Mirrored Ps resolving into an infinity |
| 2 | A continuous stroke or ribbon |
| 3 | A circular seal, in the spirit of the school crest |
| 4 | An interlaced monogram |
| 5 | A reclining infinity |
| 6 | A duotone treatment |
| 7 | An app icon working in negative space |
| 8 | A single line |
| 9 | A knotted centre |
| 10 | A Möbius ribbon |

No concept from this round shipped. The round's value was the *direction* it settled —
letterforms meeting back to back to form the lemniscate — which is what carried into round two.

**Round 2 — ChatGPT image generation, after the rename to "BernoulliPay".**
The rename changed the problem: the monogram was no longer P+P but **B+P**, and the reference
to the school became explicit in the name itself. The brief was restated for the new name —
minimalist, the initials B and P, verde Bernoulli `#009E8E` referencing the Colégio, the
school's infinity as inspiration, and again the PicPay exclusion — with the geometry named
directly: *letters mirrored into an infinity*, *with their backs forming the infinity symbol*.

Ten samples were generated. Selection landed on **the seventh**, followed by a short and
specific refinement brief: **polished, solid colour rather than shaded, the form closed so it
reads as one whole shape, higher resolution, delivered as PNG.**

A final pass then asked for the mark **without** the words "BernoulliPay". That single request
is why the system has two lockups instead of one, and therefore why the icon rail and the login
card can differ at all — see **The two lockups**, below.

The two outputs of that round are what ship: `logos/bernoulli-pay-logo-mais-texto.png` and
`logos/bernoulli-pay-logo-apenas.png`.

### What the mark resolves to

A **"bp" monogram** whose b and p bowls interlock into a lemniscate: the infinity that signs
the school, drawn by the product's own initials. The school's motif is quoted, not copied.

Two deliberate departures from the institutional mark:

- **It is not a disc.** The school's seal is a filled circle. BernoulliPay is a tool inside the
  institution, not the institution, and its mark says so by not being the seal. The favicon
  reaches square by padding, never by cropping the mark into a circle.
- **It is letters, not a symbol.** Measured against its own reflections, the mark is *not*
  symmetric — 21.7% of pixels diverge under a horizontal mirror, 19.0% vertical, 21.5% at 180°.
  It reads symmetric at a glance and measurably is not, because the b's ascender and the p's
  descender break it. That asymmetry is what keeps it reading as a monogram rather than as a
  generic infinity glyph.

The wordmark sets "Bernoulli" at a heavier weight than "Pay", so the institution leads and the
function follows — the same hierarchy the product name states.

### The two lockups

Which one appears is a decision, not a convenience:

- `static/img/logomark.png` — the mark alone, **1.544:1**, displayed 28×18 next to the
  wordtext "BernoulliPay" at the top of the nav rail. The wordtext drops away only at the
  narrowest, icon-only rail (below 480px) — everywhere wider, the mark keeps its words.
- `static/img/wordmark.png` — the mark above the words "BernoulliPay", **0.946:1**, displayed
  140×148 on the login card. The login screen is the one surface with room for the name and a
  reason to say it, so it is the one surface that carries the full lockup.
- `static/img/favicon.png` — the mark padded onto a square transparent canvas.

### Production notes

Both ship from the team's renders (`logos/bernoulli-pay-logo-apenas.png`,
`logos/bernoulli-pay-logo-mais-texto.png`), trimmed to their alpha bounds and resized to
delivery size. The ink is then normalised to exactly `#009E8E`.

**The order matters.** Normalising the colour *before* resizing lets the resampling blend the
flat ink and leaves it a step off the token — measured at `#009d8d` on the first attempt.
Normalising *after* the resize keeps a single exact ink value, which also compresses better:
the three assets total 49 KB.

Never redraw the mark, never substitute a drawn approximation, and never force either lockup
into a square.

### Not recorded here

The candidate renders are not in the repository — only the two selected outputs of round 2.
Specifically missing:

- the ten round-1 concepts from v0.app and the comparison gallery page it built;
- the ten round-2 samples from ChatGPT, including the one numbered 7 that was chosen.

Round 1's ten directions are named in the table above because the team recorded them in prose;
round 2's ten were never described individually, so only the selected one can be shown. If the
ideation needs to be presented or reproduced — for the AI-usage report, for instance — those
images should be added alongside the shipped assets.

## Colors

A neutral grey console with a single saturated identity colour, plus a small status set and a
validated categorical palette for data.

### Primary
- **Verde Bernoulli** (`brand`): the institution's colour and the product's only identity hue.
  It is the ink of the supplied logomark, paints the 3px active navigation indicator, strokes the trend
  chart at 2px and fades its area gradient from 12% to 0, and fills the first categorical slot.
  It is never set as text on a light surface.
- **Verde Ink** (`brand-ink`): the readable step of the same green. Links, the positive trend
  figure, the *OK* / *ok* / *padrão* badges and the success alert all use this, not the 500.
- **Console Ink** (`ink`): the near-black used for body copy, page titles and numbers that
  matter. It is the darkest thing on screen.
- **Inverse Slate** (`inverse`): the only filled button surface in the system. Primary actions
  — *Novo*, *Importar Excel*, *Confirmar lançamentos* — are dark-on-white rectangles. Its hover
  (`inverse-hover`) doubles as the focus-ring colour.

### Secondary
- **Ledger Red** (`destructive`): errors, the *ver* consistency badge, the destructive button's
  text, the field error border, and the duplicate-row dot in the import preview. Red never
  fills a button background; it only colours text on white or sits on its own 50 tint.
- **Warning Amber** (`badge-yellow`) and **Count Blue** (`badge-blue`): the two remaining
  status inks, used only as badge and alert text over their matching 50 tints. Blue survives
  the rebrand as a *counting* colour, not as a link colour — links are verde.

### Tertiary
- **Categorical Set** (`categorical-1` … `categorical-8`): the per-unit palette for the
  allocation weight bar, its legend dots and the inline tick meters. Derived by farthest-point
  search in OKLCH inside a deliberately muted chroma band (0.10–0.16), then validated with the
  data-viz palette validator against surface `#ffffff` in light mode. All five checks pass on
  the adjacent pairlist — the correct rule for a stacked weight bar — and the first four slots,
  which are the four real school units, also clear the stricter all-pairs gate. Slot 1 is verde
  Bernoulli, so the largest unit reads as the house colour. The set it replaced failed three
  checks, including a normal-vision ΔE of 14.4 between its violet and blue, and a zero-chroma
  grey that could not be told from disabled chrome.

### Neutral
- **Page Grey** (`surface`): the field the whole app sits on, visible only as the margin around
  the main card and behind the nav rail.
- **Card White** (`container`): every card, metric tile, field, select and the main column card.
- **Inset Grey** (`container-inset`): table header rows, table footers, sheet headers, dropzone
  hover. The one-step-back tone that says "this is chrome, not content".
- **Secondary Ink** (`ink-secondary`): labels, captions, muted table cells, inactive nav labels,
  breadcrumb trail. The single most-used text colour after Console Ink.
- **Subdued Ink** (`ink-subdued`): the quietest step, used for the dropzone's format hint and
  the select chevron. Reserved for text that may be skipped entirely.
- **Hairline** (`border-secondary`, `border-tertiary`): alpha-black rules at 10% and 8%. Every
  division in the system is one of these two; there are no solid grey borders.

### Named Rules

**The Fill-Not-Text Rule.** Verde Bernoulli at the 500 step is 3.34:1 on white. It may fill a
shape, stroke a line, or mark a surface. It may never be a text colour on a light background.
Anything that must read as brand *and* as words uses the 700 step. This is the governing
constraint of the palette and it is written into `tokens.css` so it cannot be lost.

**The Six Placements Rule.** The brand colour appears in six places: the logomark, the active
nav indicator, the chart stroke and gradient, positive badges and alerts, status and legend
dots, and links. Adding a seventh placement is a palette decision, not a styling choice.
Everything not on that list is grey or a status colour.

**The One Dark Button Rule.** `inverse` is the only filled control colour in the product, and
it survived the rebrand on contrast grounds: white on #009E8E is 3.34:1 and fails button text
contrast, so the primary action stays dark neutral. A screen shows at most one dark button;
everything else is bordered, ghosted, or a plain link.

**The Tint-and-Ink Pair Rule.** Every coloured badge or alert is a 50-step tint background with
its 700-step ink on top (brand 50/700, red 50/700, blue 50/700, yellow 50/700). Never invert
the pair, and never put white text on a saturated fill.

**The Fixed-Slot Data Rule.** Categorical colours are assigned in index order and never cycled.
A ninth series does not wrap around to slot 1; it means the chart needs rethinking. The
validation that earned these eight values only holds for the order they are declared in.

### Dark theme

Applied by an explicit `[data-theme="dark"]` on `<html>`, set before first paint by an inline
script in `base.html` so there is no flash and no second copy of the block under
`prefers-color-scheme`. The toggle lives in the nav footer (moon/sun icon) and the choice
persists in `localStorage`.

The theme re-points the same semantic names rather than inventing a second vocabulary — a
component never names a theme, only a semantic token. Ground inverts (surface `#121212`,
container `#1b1b1b`, inset `#151515`, keeping the same three-step separation as light) and the
chromatic scale flips role, not meaning: each colour's 50-tint becomes a deep desaturated
ground and its 700-ink becomes a light hue, individually re-verified at ≥4.5:1 against the tint
it sits on. Verde Bernoulli is lifted to `#00b8a5` (500) with `#4dd6c5` (700, 8.4:1 on the
brand-50 ground) so it still reads as the identity colour rather than washing out on a dark
surface; hairlines flip from black alpha to white alpha, since a black hairline is invisible on
a dark ground; and shadows deepen, because a 6%-black shadow does not read on `#121212`.

**The One Semantic Layer Rule.** Dark mode is a re-pointed token layer, not a parallel design
system. A new component references the same semantic custom properties the light theme uses
(`--bg-container`, `--text-primary`, …) and gets both themes for free; it never branches on
`[data-theme]` directly or hard-codes a dark-mode-only value.

## Typography

**Display Font:** IBM Plex Sans (variable `wght` 100–700, self-hosted `.woff2`, preloaded,
with system-ui fallback)
**Body Font:** IBM Plex Sans — the same face at every size; there is no second text family.
**Numeric Font:** IBM Plex Mono (self-hosted, **400 only**), applied via `.mono` with tabular figures.

**Licence:** both are SIL Open Font License 1.1 (`static/fonts/IBMPlex-LICENSE.txt`), self-hosted
with no CDN dependency. Each family ships split by `unicode-range` into `latin` and `latin-ext`;
pt-BR resolves entirely inside `latin`, so `latin-ext` is fetched only when a name demands it.

**Character:** A grotesque with engineering DNA, differentiated by weight (400/500 only — nothing
bolder is used) and by size. The pairing is the point: Plex Sans and Plex Mono are drawn as one
family, so a currency column and the label above it sit on the same skeleton. The mono face is
not a stylistic accent; it exists so money aligns on the decimal.

**Why it replaced Geist.** Geist was the last inherited piece of the Maybe port and a face that
has become a default across the category. The swap was measured before it was made: Plex Sans is
3–5% *narrower* than Geist at the same size, so tables gained room rather than overflowing, and
Plex Mono's advance width is **identical** to Geist Mono's, so money columns did not move by a
single pixel. x-height differs by 2.6% (0.516em vs 0.530em) — below the threshold that would
justify re-cutting the ramp, so the scale above is unchanged. Both line boxes are 1.300em, so
the leading values still hold.

**Units:** the ramp is **rem, not px**. Every step was a px literal, which silently ignored a
reader's browser font-size preference; `0.875rem` body is a deliberate density floor for an
all-day desktop workflow, not an accident of scale.

### Hierarchy

Every step is a token in `tokens.css`; no component may set a literal size.

| Role | Token | Size | Use |
|---|---|---|---|
| Hero | `--text-hero` | 2.25rem / 36px | The payable total, and nothing else |
| Display | `--text-display` | 1.875rem / 30px | Page titles; drops to Headline below 640px |
| Headline | `--text-headline` | 1.375rem / 22px | Login card title; page title on narrow screens |
| Metric | `--text-metric` | 1.25rem / 20px | Metric tile values |
| Title | `--text-title` | 1rem / 16px | Card headings, and the lede under a page title |
| Body | `--text-body` | 0.875rem / 14px | The default: cells, inputs, buttons, breadcrumbs |
| Data | `--text-data` | 0.8125rem / 13px | Inline mono, optically matched to Body |
| Label | `--text-label` | 0.75rem / 12px | Field and metric labels, badges, captions |
| Micro | `--text-micro` | 0.6875rem / 11px | Nav rail labels; uppercase column headers |

**Leading:** `--leading-tight` 1.15 for Hero and Display (1.5 left headings floating),
`--leading-snug` 1.3 for Titles, `--leading-body` 1.5 for everything else.

**Measure:** `--measure` (68ch) caps running text via `.prose`. Tables and data panels are
deliberately exempt — they want the full card; running text does not.

**Column Header** keeps +0.04em tracking and uppercase, on Micro, and is table `<th>` only.

### Named Rules
**The Two-Weight Rule.** Plex Sans ships a 100–700 `wght` axis; this system uses 400 and 500. Emphasis is a step
up to 500 or a step darker in ink, never 600+.

**The Tabular Money Rule.** Any rendered currency, percentage or count gets `tabular-nums` —
via `.mono` where the figure is secondary metadata, via `.tabular` where it must stay in the
body face. Numeric table columns are right-aligned and `white-space: nowrap`.

**The Uppercase-Is-For-Columns Rule.** Uppercase with letter-spacing appears in exactly one
place: table column headers. It is not an eyebrow style, not a section kicker, and must not be
borrowed for one.

## Layout

A two-column fixed shell at full height, defined once in `base.html` and never overridden: a
nav rail carrying the logomark, the section links and the account footer, and a flexible main
column. The main column holds a single white card (12px radius) that fills the viewport height
and scrolls internally — the page itself never scrolls. Content inside the card sits on a
`--gutter` custom property (20px desktop, 14px below 1024px) so the topbar and body share one
horizontal rhythm, with 48px of bottom breathing room.

Spacing is a 4px-based rhythm used at 4 / 8 / 12 / 16 / 24: 24px between stacked sections
(`.stack`, card bottom margin, page-header margin), 16px of card padding, 12px of table cell
padding, 8px between adjacent controls. Grids are auto-fitting rather than fixed-column —
metric tiles at `minmax(180px, 1fr)` (`minmax(150px, 1fr)` below 640px, where two 180px tiles
plus their grid gap no longer fit a phone-width card), form fields at `minmax(220px, 1fr)` — so
wide monitors fill out instead of leaving a dead gutter.

**Responsive behaviour.** Three breakpoints, each earning its keep. Below 1024px the nav rail
narrows from 240px to 200px, the gutter tightens, and touch targets grow rather than shrink —
icon buttons go 32px → 40px and small buttons regain padding, because both sat under the 24px
minimum once padding collapsed. Below 640px the page title shrinks and metric tiles drop their
minimum width, per above. Below 480px the rail drops its text — logo wordtext, item labels,
account name — down to a 64px icon-only strip, because a labelled 200px rail plus a data table
does not fit a phone screen with anything left to read; every icon-only link keeps its label as
an `aria-label` so nothing loses its accessible name. There is no drawer, no overlay and no
per-viewport layout preference in `localStorage` — the rail is always present, just narrower.

**Motion.** Near-zero: a 150ms background fade on buttons and the dropzone, a 200ms chevron
rotation, a 180ms icon cross-fade on the theme toggle. Under `prefers-reduced-motion` the
chevron rotation is removed while colour and opacity transitions are kept, so state feedback
survives.

### Named Rules
**The Card-Is-The-Page Rule.** The scroll container is the main card, not the document. New
screens render inside `app__content`; they do not introduce their own full-height wrappers or
page-level scroll.

**The Gutter Variable Rule.** Horizontal padding comes from `var(--gutter)`, never a literal.
Anything hard-coding 20px falls out of alignment with the topbar at the tablet breakpoint.

## Elevation & Depth

Essentially flat. Depth is tonal, not spatial: page grey behind, white card in front, inset
grey for chrome rows inside the card. What shadow exists is a hairline substitute — the
signature `--shadow-border-xs` combines a 1px/6%-black drop with a `0 0 0 1px` alpha-black
ring, so a card reads as *edged* rather than *raised*. No element in the system is lifted more
than 1px at rest, and nothing lifts on hover; hover changes background tone only.

### Shadow Vocabulary
- **Edge** (`box-shadow: 0 1px 2px 0 rgba(11,11,11,0.06), 0 0 0 1px rgba(11,11,11,0.05)`): the
  main card only — the single shell that sits directly on page grey. Content cards and metric
  tiles nest inside that shell, so they take a hairline border instead of repeating its shadow;
  see the Fill-Not-Text-style rule under Shapes.
- **Edge, larger** (`box-shadow: 0 1px 6px 0 rgba(11,11,11,0.06), 0 0 0 1px rgba(11,11,11,0.05)`):
  the login card only — the one surface that floats alone on grey.
- **Control** (`box-shadow: 0 1px 2px 0 rgba(11,11,11,0.06)`): secondary buttons, form fields
  and the active nav item's tile, giving them just enough presence to read as interactive.
- **Overlay** (`box-shadow: 0 4px 8px -2px rgba(11,11,11,0.06)`, stacked with a deeper ambient
  shadow): the merge-confirmation modal and the import sheet-detail card — the two genuinely
  floating elements in the product, both dialogs over a scrim, neither a drawer.

### Named Rules
**The Edge-Not-Lift Rule.** Shadows draw edges, not altitude. A surface may gain a hairline ring;
it may never gain a visible drop that implies it hovers above the page.

**The Focus-Is-An-Outline Rule.** Focus is `2px solid var(--focus-ring)` at `2px` offset on
`:focus-visible`, applied globally to links, buttons, inputs, selects, textareas, summaries and
anything tabbable. It is never a shadow, never a colour shift, never removed. Composite controls
carry the ring on the wrapper (`.field:focus-within`) and explicitly suppress it on the inner
control so only one ring ever draws. The focus ring stayed neutral slate through the rebrand;
it is not a brand surface.

## Shapes

Softly rounded rectangles throughout, at three used steps: 8px for small controls and
interactive chrome (icon buttons, nav item tiles, fields, selects, small buttons),
10px for buttons, metric tiles and alerts, 12px for cards, the main column card, table frames,
sheets and the dropzone. Badges and weight-bar segments are full pills (999px); avatars and
legend dots are circles.

Borders are alpha-black hairlines, never solid grey, and appear on exactly three things: form
controls, table row dividers, and frames around grouped content. Table headers round their
outer corners (10px on `th:first-child` and `th:last-child`) so a header row reads as a
floating inset bar rather than a ruled band. The upload dropzone is the single dashed edge in
the system (1.5px dashed).

The logomark is not system geometry and is specified under **Identity**, above.

## Components

### Buttons
- **Shape:** softly rounded (10px; 8px in the small variant).
- **Primary:** dark inverse slate with white text, 8px/12px padding, 14px weight 500, 16px
  inline icon before the label. Not teal — see The One Dark Button Rule.
- **Hover / Focus:** 150ms background fade to `inverse-hover`; focus adds the global 2px outline.
- **Secondary:** white with a hairline border and the control shadow — the default for anything
  non-committal (*Importar*, *Cancelar*).
- **Ghost:** transparent, secondary ink, tinting to `surface-hover` and darkening to full ink
  on hover. Used for in-table and in-card navigation ("Ver lançamentos ›").
- **Danger:** white with a hairline border and red text, hovering to the red 50 tint. It is
  never a red fill.
- **Icon button:** 32px square, transparent, secondary ink, 8px radius, tinting on hover;
  grows to 40px below 1024px. Always carries an `aria-label`.

### Chips
- **Style:** pill badges (999px), 2px/8px padding, 12px weight 500, tint background with its
  matching 700-step ink. Five variants: gray (neutral facts such as paying company), blue
  (counts), brand (positive state — *OK*, *ok*, *padrão*), red (needs review), yellow
  (warnings, incomplete registration).
- **State:** badges are read-only status markers, not filters or toggles. Filtering is done by
  `.select` controls in the filter bar, never by chips.

### Cards / Containers
- **Corner Style:** 12px (10px for the smaller metric tile).
- **Background:** card white on page grey.
- **Shadow Strategy:** the Edge treatment — see Elevation & Depth.
- **Border:** none; the hairline ring inside the shadow is the border.
- **Internal Padding:** 16px, with 24px between stacked cards and a 12px header row above the body.

### Inputs / Fields
- **Style:** the field is a bordered white box (8px radius, hairline border, control shadow,
  8px/12px padding) that contains *both* a 12px secondary-ink label and a chrome-less input —
  the input itself has no border, outline, padding or background of its own. The field has no
  transition; it is a static container whose only animated property would have been a shadow it
  never changes.
- **Focus:** the wrapper takes the 2px focus outline at 2px offset via `:focus-within`; the
  inner control's own outline is suppressed.
- **Error:** the wrapper border turns red-500 and a 12px destructive-ink message sits below.
- **Select:** distinct from field — a bordered weight-500 control with an inline SVG chevron
  drawn in subdued ink, 28px of right padding to clear it, and native appearance removed.
- **Checkbox:** native, sized to 18px, tinted with `accent-color` at the dark neutral (not the
  brand — an 18px control needs the contrast).

### Navigation
- **Rail (240px, 200px below 1024px, 64px icon-only below 480px):** the logomark and wordtext,
  then a vertical list of items, each an 18px icon and an inline label sharing one row (icon
  above label only disappears — the label does, not the row — at the narrowest, icon-only
  width). Inactive is secondary ink on transparent; hover tints the tile; active gets a white
  tile with the control shadow, full ink, and a 3px **verde Bernoulli** bar flush with the
  rail's own edge — the single strongest brand placement in the chrome, and the only place the
  500 step touches the shell. Every link keeps an `aria-label` matching its visible text, so the
  icon-only width loses no accessible name. The rail's footer pins the account row (avatar,
  name, role) above settings, theme toggle and logout icon buttons.
- **Topbar:** a `›`-separated breadcrumb in secondary ink with the current page in full ink.
- **Mobile:** the rail never leaves the flow — there is no drawer or overlay. It narrows in
  place at 1024px and 480px, per Layout.

### Data Table
The product's densest and most characteristic surface. Column headers are 11px uppercase
letter-spaced secondary ink on inset grey with rounded outer corners; body rows are separated
by 8%-black hairlines and tint on hover; the last row drops its rule. Numeric columns are
right-aligned, tabular and non-wrapping; withholding columns render as muted negative figures.
The footer row repeats totals in weight 500 on inset grey above a 10%-black rule. Action cells
right-align a 6px-gapped row of icon buttons. Empty state is a centred 40px-padded secondary-ink
line inside the same frame.

### Trend Chart
A dependency-free SVG line chart drawn by `chart.js` at an 800×220 viewBox with
`preserveAspectRatio: none`, stretched to the card width at a fixed 220px height. A 2px
non-scaling verde Bernoulli stroke over an area fill of the same green fading 12% → 0%. It
reads its stroke from `--color-brand-500` at runtime rather than hard-coding a hex, so a
palette change cannot strand it — and the script carries the contrast note in a comment, since
this is exactly the legitimate use of the 500 step: a stroke, never a word. Axis endpoints
render as a 12px secondary-ink row beneath. It carries `role="img"` and a sentence-long
`aria-label` describing the series.

### Allocation Weight Bar
A 4px-tall flex row of pill segments, one per school unit, flexed by share and coloured from
the categorical set in fixed slot order, followed by a legend of dots with unit name and bold
percentage. A ten-tick variant (`.ticks`, 2px × 10px bars) renders the same proportion inline
inside table rows, filling from the same slot colour via a `--tick-color` custom property.

### Import Sheet Block
The import preview's signature container: a 12px-radius hairline frame with an inset-grey header
holding an include checkbox, the sheet name, a blue count badge and warning badges, and a
collapse chevron that rotates 90° when closed. Excluded sheets drop to 50% opacity rather than
disappearing — the operator must be able to see what they chose to skip.

## Do's and Don'ts

### Do:
- **Do** compose new screens from `page-header` → optional `metrics` grid → `card` sections,
  inside `app__content`.
- **Do** use `--color-brand-500` for fills, strokes and marks, and `--color-brand-700` for any
  brand-coloured text, including links and positive badge ink.
- **Do** reach for semantic tokens (`--text-secondary`, `--bg-container-inset`,
  `--border-tertiary`) rather than the raw `--color-gray-*` or `--color-brand-*` primitives
  where a semantic name exists.
- **Do** assign categorical colours by fixed slot index, in declaration order.
- **Do** put every currency, percentage and count in tabular figures, right-aligned in tables.
- **Do** give every icon-only control an `aria-label` and every table column a `scope="col"`
  header, using `.sr-only` where a column reads as blank.
- **Do** render icons with `{% icon "name" %}` — inline Lucide SVG at 12/14/16/18px,
  stroke-only — including directional arrows, which use `arrow-up` / `arrow-down` with
  `css_class="trend-icon"` for optical alignment.
- **Do** keep the global focus outline intact; if a composite control needs one ring, put it on
  the wrapper and suppress the inner one.
- **Do** grow touch targets at the 1024px breakpoint rather than letting padding collapse.
- **Do** define a new colour for both themes together, in the same edit: the light value under
  `:root` and its re-verified (≥4.5:1) dark equivalent under `[data-theme="dark"]`.

### Don't:
- **Don't** set `--color-brand-500` as a text colour on any light surface. It is 3.34:1.
- **Don't** fill the primary button with verde. White on #009E8E fails button text contrast;
  the dark neutral button is the deliberate outcome of the rebrand, not an oversight.
- **Don't** redraw, re-letter or re-proportion the logomark, and don't force the horizontal
  lockup into a square container. It is supplied artwork; the only permitted transforms are
  uniform scaling and the transparent padding used for the favicon.
- **Don't** branch a component on `[data-theme]` directly or hard-code a dark-mode-only value;
  reference the same semantic token both themes already re-point (see Dark theme, under Colors).
- **Don't** fill a button with brand, red, yellow or blue. Status colour is text-on-tint only.
- **Don't** reintroduce decorative hues. Violet, cyan, pink, orange, fuchsia and indigo were
  deleted from the token layer as dead port residue; they are not a reserve palette.
- **Don't** cycle the categorical palette past slot 8, or reorder it. The validation holds for
  the declared order only.
- **Don't** add font weights above 500 or a third font family. Emphasis is weight 500 or darker ink.
- **Don't** use uppercase letter-spaced type anywhere but table column headers — in particular,
  not as a kicker or eyebrow above a heading.
- **Don't** lift surfaces on hover or add a shadow heavier than the Overlay step; hover changes
  background tone.
- **Don't** replace the focus outline with a box-shadow or a border-colour change; that treatment
  was already removed once by audit for failing contrast.
- **Don't** substitute a Unicode character for an icon. Arrows, chevrons and carets come from
  the Lucide set through the `icon` tag; `↑`/`↓` were removed from the dashboard for this reason.
- **Don't** hard-code a hex in a template, a script or a component. Colour comes from the token
  layer, including in JavaScript (`getComputedStyle` on `:root`).