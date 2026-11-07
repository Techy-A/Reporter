# Reporter design rules

The house rules for every Reporter screen. Sources: the `frontend-design` skill, the doctrine in
[plugin87/ux-ui-agent-skills](https://github.com/plugin87/ux-ui-agent-skills) (MIT), and the
"20 ways to unslop AI designs" checklist. Read this before designing or building any screen, and use
it as the review checklist afterwards.

## Brief

- **Subject:** an HR desk for Indian organisations. HR and recruiters use the admin portal all day
  on desktop; employees open the employee portal occasionally, mostly on a phone.
- **Mood:** "on the record". Calm, exact, citable. Never playful, never hype.
- **Signature:** the policy citation slip (paper surface, hairline border, serif § number, version).
  It is the thing an answer is trusted for, so it is the one place the design spends boldness.
  In the admin portal, the week slot rail plays the same role for scheduling.

## Tokens (in `frontend/shared/src/tokens.css`)

| Role | Value | Rule |
|---|---|---|
| Ink | `#1e2a5a` | Headings, primary surfaces, the "attended" action |
| Saffron | `#e8a33d` | **Actions only** (primary buttons, focus ring, active tab). One accent. |
| Paper / surface | `#f6f7fb` / `#fff` | Off-white page, white cards. Never `#000` on `#fff`. |
| Status | ok / warn / bad / info | Always with a word or icon, never colour alone |
| Radius | `--r-xs 6` · `--r-sm 8` · `--r 12` · `--r-lg 16` · pill | Only these. Nested: inner radius ≈ outer minus padding, floor `--r-xs`. |
| Type | Young Serif (display), Figtree (UI), JetBrains Mono (codes) | Page title ≥ 2.5× body. Mono **only** for codes, IDs, versions, sign-in codes. |
| Numbers | `.num` (tabular figures) | Times, dates, counts, KPIs, money |
| Motion | `--dur-fast 120ms`, `--dur 200ms`, `--ease` | Only for feedback (new message, sent, saved). Reduced motion turns it off. |

## Never ship

1. **Emoji**, anywhere: UI, copy, CSS content, commits. Use the `Icon` component (inline SVG, `currentColor`).
2. **A coloured border on one side** of a card, slot, callout or alert. Use a full hairline border or a surface change; status by icon plus text.
3. **Em or en dashes in UI copy**, including as "empty" placeholders. Say what's missing ("Not booked", "Not rated yet") or use "to" for ranges.
4. **Filler badges and redundant labels.** If a heading already says it, the chip goes.
5. **Equal-weight rows of cards.** One thing leads each screen; the rest is quieter.
6. **A shadow on every box.** Most things are flat; elevation means it actually floats (drawer, sticky dock).
7. **Fake or placeholder content** in shipped screens. Use realistic Indian names, real policy wording.
8. **Marketing words**: elevate, seamless, unlock, effortless, supercharge.

## Always

- **Mobile first.** Base styles are the phone layout; wider screens add with `min-width`.
- **Every interactive element has its states:** default, hover, focus-visible, active, disabled, loading (if async), error (if input), selected (if selectable).
- **Loading states** for every request: the button says what's happening ("Sending…"), lists show a quiet placeholder.
- **Copy:** verbs first on buttons ("Send to HR", "Make live"); errors say what to do next; sentence case; the same action keeps the same name through the flow.
- **Destructive actions** look destructive everywhere (trigger and confirm).
- **Check it rendered**: 390 px and 1280 px, light and dark, then click every control.

## Deliberate exception

Native `<select>` stays for now. The kit bans it for looks, but a custom listbox must pass full keyboard
and screen-reader checks to be safe, and the native control is the better phone experience for HR's
occasional dropdowns. Revisit if we add a component library with a tested listbox.

## The 20-point unslop checklist (for reviews)

1 Delete filler badges · 2 Drop redundant labels · 3 Unitalicise random words · 4 Mono only where needed ·
5 Use a design system · 6 Show the actual product · 7 Enlarge the main feature · 8 Group with spacing ·
9 Make headlines specific · 10 Emphasise the CTA · 11 One accent colour · 12 Keep icons consistent ·
13 Remove embellishments · 14 Inner radius = outer − padding · 15 Improve text contrast ·
16 Wrap headlines properly (`text-wrap: balance`) · 17 Align by eye, not pixels · 18 Tabular numbers ·
19 Add loading states · 20 Animate useful feedback.
