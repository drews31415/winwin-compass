# Frontend App Routes

This directory contains Next.js App Router pages.

## Routes

- `/`: home, search entry, quick-start cards, and statistics.
- `/chat`: AI 상담 screen with streaming chat UI.
- `/map`: map screen with Mapbox/Leaflet fallback and area filters.
- `/report`: report search and popular area list.
- `/report/[area_cd]`: detailed commercial-area report.
- `/policy`: policy matching and search form.
- `/marketing`: text-based marketing content generator for SNS, reviews, flyers, menu copy, and events.
- `/settings`: placeholder settings screen.
- `/ux-test`: SUS usability survey and local admin view.

## Conventions

Keep route-level state in page or route client components. Move reusable UI into `frontend/components/` and API access into `frontend/lib/`. Use Korean user-facing copy and maintain the 상생나침반 brand name consistently.
