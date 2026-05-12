# Frontend Tests

Playwright smoke tests for deployed frontend pages.

## Current Test

- `deploy-smoke.spec.ts`: opens the production pages and fails on browser console errors or page errors.

## Run

```bash
cd frontend
npx playwright test tests/deploy-smoke.spec.ts
```

The test targets https://winwin-compass.vercel.app. Update `baseUrl` only when the public frontend URL changes.
