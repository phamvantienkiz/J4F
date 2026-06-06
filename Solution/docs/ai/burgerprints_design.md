# Speedy Print

## Mission

Create implementation-ready, token-driven UI guidance for Speedy Print that is optimized for consistency, accessibility, and fast delivery across e-commerce storefront.

## Brand

- Product/brand: Speedy Print
- URL: https://burgerprints.com/en/
- Audience: online shoppers and consumers
- Product surface: e-commerce storefront

## Style Foundations

- Visual style: clean, functional, implementation-oriented
- Main font style: `font.family.primary=Inter`, `font.family.stack=Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`, `font.size.base=16px`, `font.weight.base=500`, `font.lineHeight.base=25.6px`
- Typography scale: `font.size.xs=12px`, `font.size.sm=13.6px`, `font.size.md=14px`, `font.size.lg=14.5px`, `font.size.xl=15px`, `font.size.2xl=15.52px`, `font.size.3xl=16px`, `font.size.4xl=17px`
- Color palette: `color.text.primary=#0f172a`, `color.text.secondary=#94a3b8`, `color.surface.muted=#ffffff`, `color.text.inverse=#475569`, `color.surface.base=#000000`, `color.surface.raised=#f26522`, `color.surface.strong=#f8fafc`
- Spacing scale: `space.1=1.86px`, `space.2=8px`, `space.3=9px`, `space.4=10px`, `space.5=12px`, `space.6=14px`, `space.7=14.4px`, `space.8=15px`
- Radius/shadow/motion tokens: `radius.xs=4px`, `radius.sm=8px`, `radius.md=10px`, `radius.lg=12px`, `radius.xl=14px`, `radius.2xl=20px`, `radius.step7=28px`, `radius.step8=999px` | `shadow.1=rgba(15, 23, 42, 0.1) 0px 10px 30px -5px, rgba(15, 23, 42, 0.08) 0px 20px 40px -10px`, `shadow.2=rgba(242, 101, 34, 0.28) 0px 4px 14px 0px`, `shadow.3=rgba(0, 0, 0, 0.08) 0px 4px 12px 0px`, `shadow.4=rgba(242, 101, 34, 0.35) 0px 20px 60px -15px` | `motion.duration.instant=200ms`, `motion.duration.fast=300ms`

## Accessibility

- Target: WCAG 2.2 AA
- Keyboard-first interactions required.
- Focus-visible rules required.
- Contrast constraints required.

## Writing Tone

Concise, confident, implementation-focused.

## Rules: Do

- Use semantic tokens, not raw hex values, in component guidance.
- Every component must define states for default, hover, focus-visible, active, disabled, loading, and error.
- Component behavior should specify responsive and edge-case handling.
- Interactive components must document keyboard, pointer, and touch behavior.
- Accessibility acceptance criteria must be testable in implementation.

## Rules: Don't

- Do not allow low-contrast text or hidden focus indicators.
- Do not introduce one-off spacing or typography exceptions.
- Do not use ambiguous labels or non-descriptive actions.
- Do not ship component guidance without explicit state rules.

## Guideline Authoring Workflow

1. Restate design intent in one sentence.
2. Define foundations and semantic tokens.
3. Define component anatomy, variants, interactions, and state behavior.
4. Add accessibility acceptance criteria with pass/fail checks.
5. Add anti-patterns, migration notes, and edge-case handling.
6. End with a QA checklist.

## Required Output Structure

- Context and goals.
- Design tokens and foundations.
- Component-level rules (anatomy, variants, states, responsive behavior).
- Accessibility requirements and testable acceptance criteria.
- Content and tone standards with examples.
- Anti-patterns and prohibited implementations.
- QA checklist.

## Component Rule Expectations

- Include keyboard, pointer, and touch behavior.
- Include spacing and typography token requirements.
- Include long-content, overflow, and empty-state handling.
- Include known page component density: links (57), cards (29), lists (18), inputs (16), buttons (11), navigation (3).

## Quality Gates

- Every non-negotiable rule must use "must".
- Every recommendation should use "should".
- Every accessibility rule must be testable in implementation.
- Teams should prefer system consistency over local visual exceptions.
