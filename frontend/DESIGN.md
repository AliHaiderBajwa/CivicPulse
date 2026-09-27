# CivicPulse frontend design system

Municipal operations console: trustworthy, calm, dense where it counts.
One font, one accent, slate neutrals. Light theme only (explicit debt).

## Tokens (`src/index.css` `:root`)

| Token | Value | Use |
|---|---|---|
| `--slate-950` | `#0B1220` | Header, ink text |
| `--slate-700` | `#334155` | Secondary text |
| `--slate-500` | `#64748B` | Muted text, table head |
| `--slate-200` | `#E2E8F0` | Borders |
| `--slate-100` | `#F1F5F9` | Muted surfaces |
| `--paper` | `#F6F8FB` | Page background |
| `--card` | `#FFFFFF` | Cards, tables |
| `--accent` | `#0369A1` | Primary actions, links, focus (5.9:1 on white) |
| `--accent-ink` | `#075985` | Hover / pressed |
| `--accent-soft` | `#E0F2FE` | Info fills, active nav pill |
| `--ok` / `--ok-bg` | `#047857` / `#D1FAE5` | Resolved, HIT, success |
| `--warn` / `--warn-bg` | `#B45309` / `#FEF3C7` | In-progress, attention |
| `--bad` / `--bad-bg` | `#B42318` / `#FEF3C2`-adjacent `#FEE4E2` | High priority, MISS, errors |
| `--neutral-bg` | `#E8ECF1` | Rejected, low, unknown chips |
| `--radius-sm/md/lg` | `6px` / `10px` / `14px` | Inputs / cards / hero panels |
| `--shadow-sm/md` | slate-tinted `rgb(15 23 42 / …)` | Single light source (top) |
| `--font` | `'Atkinson Hyperlegible', system-ui, …` | 400 body, 700 display |

Status → chip mapping (color + label, never color alone):
`open` sky · `in_progress` amber · `resolved` green · `rejected` slate.
Priority: `high` red · `normal` sky · `low` slate. Provider: mono slate chip.

## Typography

Display (h1/h2): 700, `letter-spacing -0.01em`, `line-height 1.2`,
`text-wrap: balance`. Body 16px/1.5. Labels 600 0.95rem. Counts and
timestamps: `font-variant-numeric: tabular-nums`. Micro labels (eyebrows,
table heads): 0.78rem, uppercase, `letter-spacing 0.06em`, slate-500.

## Motion (meaning only)

`--ease: cubic-bezier(.2,.7,.3,1)`; hovers 160ms, entrances 220ms;
GPU-only (`transform`, `opacity`). Button press `scale(.98)`. Result card
enters with fade-rise once. Loading keeps its text (screen-reader contract)
plus a CSS pulse dot. `prefers-reduced-motion: reduce` disables all of it.

## Responsive

Container `72rem`, fluid gutters. `<640px`: single column, full-width
inputs, table scrolls horizontally in `.table-wrap`, header stacks.
`640–1024px`: two-column filter grid, stats grid ×2. `>1024px`: stats grid
×4 dashboard breathing room. Touch targets ≥44px (`min-height: 2.75rem`
on buttons/inputs/selects). No horizontal page scroll at 375px.

## Accessibility contract (DO NOT BREAK)

Worst case a test or a screen reader depends on it: labels
`Complaint text`, `Location`, `Contact (optional)`, `Category`; roles
`alert`/`status`/named `button`s/`heading`s (exact copy listed in tests);
testIds `cache-badge`, `stats-total`, `count-category-*`,
`count-priority-*`, `result-category|priority|summary|provider`.
Focus ring always visible: `outline: 3px solid rgba(3,105,161,.5)` +
offset. Skip link first in tab order. Errors stay adjacent to fields with
`role="alert"`.

## Accepted debt

- Light theme only (no dark mode; flagged for later).
- Google-Fonts `<link>` with system fallback: offline/sandboxed renderers
  fall back silently, layout unchanged.
- No new npm dependencies: React + CSS only, bundle unchanged in kind.
