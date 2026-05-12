# Frontend Lib

Shared client utilities for the frontend.

## Files

- `api.ts`: typed fetch wrappers for backend calls.
- `hooks/useChat.ts`: chat session state and streaming response handling.
- `hooks/useMapData.ts`: area data loading, GeoJSON conversion, and filters.
- `utils.ts`: class name and small utility helpers.

## Conventions

Keep backend URLs centralized through `NEXT_PUBLIC_API_URL`. Hooks should own browser-only state such as `localStorage`, map filters, and chat session IDs. Avoid duplicating endpoint paths in page components.
