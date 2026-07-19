# Frontend Dev — Reference

## State Management Patterns

| Pattern | When to Use | Library |
|---------|-------------|---------|
| Context + useReducer | Medium apps, few re-renders | Built-in React |
| Zustand | Small-to-medium, simple API | zustand |
| TanStack Query | Server-state heavy apps | @tanstack/react-query |
| Redux Toolkit | Large apps, complex actions | @reduxjs/toolkit |
| Jotai | Atomic, fine-grained re-renders | jotai |

- Keep server state (API data) in TanStack Query, not in client stores.
- Use Zustand for UI-only state (modals, toasts, sidebar open/close).
- Compute derived data with `useMemo` or selectors, not by duplicating into stores.

## Testing Checklist

- [ ] Render tests for every component (React Testing Library)
- [ ] Use user-centric queries (`getByRole`, `getByLabelText`) over test IDs
- [ ] Cover edge states: loading, empty, error boundary, 404
- [ ] Integration tests for 3-5 primary user journeys
- [ ] `waitFor` / `findBy` for async — never `setTimeout`
- [ ] Snapshot tests only for stable, rarely-changing output

## Accessibility Checklist

- [ ] All interactive elements have accessible names
- [ ] Color contrast >= 4.5:1 text / 3:1 large text
- [ ] Focus indicators visible on all interactive elements
- [ ] Form errors announced via `aria-live` regions
- [ ] Semantic landmarks (`<nav>`, `<main>`, `<aside>`)
- [ ] Full keyboard navigation (Tab order covers every control)
- [ ] Screen reader test: NVDA (Windows) or VoiceOver (macOS)

## Component Library Integration

- **MUI**: Use `sx` sparingly — prefer theme overrides via `createTheme`.
- **shadcn/ui**: Copy into tree and customize directly (no version lock-in).
- **Ant Design**: Set `ConfigProvider` with `token` for consistent theming.
- **Chakra UI**: Use `componentStyle` config as single source of truth.
- Always wrap third-party libs in your own abstraction for future swap-ability.
