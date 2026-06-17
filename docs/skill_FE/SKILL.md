---
name: burgerprints-fe-taste-skill
description: Project-specific frontend implementation skill for BurgerPrintsAgent UI. Use the existing design brief in docs/skill_FE/design.md, then apply Taste Skill anti-slop frontend rules for high-quality, accessible UI implementation.
---

# BurgerPrintsAgent Frontend Skill

Use this skill when implementing or redesigning the frontend/chat UI for this project.

## Required inputs

Before writing frontend code, read:

1. `docs/skill_FE/design.md` - project design tokens, typography, colors, component rules, accessibility checklist.
2. `docs/skill_FE/taste-skill/skills/taste-skill/SKILL.md` - Taste Skill anti-slop frontend implementation rules.

Optional references:

- `docs/skill_FE/taste-skill/skills/image-to-code-skill/SKILL.md` for image-to-code workflows.
- `docs/skill_FE/taste-skill/skills/redesign-skill/SKILL.md` for improving an existing UI.
- `docs/skill_FE/taste-skill/skills/soft-skill/SKILL.md` if the UI should feel calmer and more premium.

## Design read for this project

Read this as: a seller-facing BurgerPrints/POD assistant UI for Vietnamese and international sellers, with a practical SaaS/productivity language, leaning toward accessible React UI, strong BurgerPrints orange CTA, clean cards, and decision-ready commerce data.

## Non-negotiable project tokens

Use `design.md` as the source of truth:

- Primary font: `SVN-Gilroy`, `Gilroy`, then system fallback.
- Brand orange: `#f26522` for primary CTA and active emphasis.
- Primary text: `#0f172a`.
- Secondary text: `#94a3b8`.
- Card surface: `#ffffff`.
- Section/muted surface: `#f8fafc`.
- Radius and spacing must come from the token scale in `design.md`.

Do not introduce a second orange, random AI-purple gradients, generic glassmorphism, or untracked pixel values unless the design brief is updated.

## UI priorities

The frontend should make these flows easy:

1. Seller asks a natural-language BurgerPrints question.
2. Agent asks for destination market when needed.
3. User sees suggested questions by market/month.
4. User sees SKU recommendation table with cost, shipping, delivery, carrier, SLA, profit/margin when available.
5. User can start a sandbox order draft only after a recommendation.
6. Final create-order action remains explicit and safe.

## Suggested question UI rules

Suggested questions should appear as compact chips/buttons near the chat input or onboarding state.

They should support:

- Market-aware prompts: US, CA, UK, AU, VN, EU.
- Month/season-aware prompts.
- Product prompts: T-shirt, hoodie, sweatshirt, mug, tank top.
- Clear click behavior: clicking a suggestion sends it to `/agent/chat` as the message.

Example chips:

```text
Mùa này ở US nên bán áo gì?
Gợi ý niche POD cho US tháng này
Sắp tới ở US có event nào nên làm design?
Tìm SKU T-shirt phù hợp bán ở US mùa hè
```

## Component rules

### Primary button

- Use BurgerPrints orange from `design.md`.
- Include hover, focus-visible, active, disabled, and loading states.
- Never remove focus outline unless a custom visible focus state replaces it.

### Chat input

- Must be keyboard accessible.
- Enter sends message; Shift+Enter creates newline if multiline is supported.
- Loading state must prevent duplicate sends.

### Recommendation table/card

- Keep SKU, product, supplier, base cost, shipping, total cost, delivery, carrier, SLA visible.
- Use horizontal scroll on small screens instead of shrinking text too much.
- Long product names must truncate with ellipsis.

### Order draft summary

- Never display raw PII after capture if backend returns masked summary.
- Make final confirmation visibly separate from ordinary “ok/yes” responses.

## Implementation checklist

Before reporting frontend work complete:

- Verify the UI uses `design.md` tokens.
- Verify responsive behavior at mobile and desktop widths.
- Verify keyboard focus order.
- Verify suggested question click sends the expected chat message.
- Verify missing-country clarification is visible and does not show create-order CTA.
- Verify recommendation response can lead to sandbox order draft.
- Run the available frontend test/build command if the frontend project defines one.
