# Frontend Components

Reusable React components for 상생나침반.

## Folders

- `layout/`: sidebar and mobile tab bar.
- `chat/`: chat window, input, and suggested questions.
- `map/`: Mapbox/Leaflet map, sidebar filters, and area popup.
- `report/`: forecast chart, risk detail, risk gauge, and stat cards.
- `policy/`: policy card display.
- `ui/`: small shared UI primitives and feedback components.

## Guidelines

Use `PascalCase` for component filenames. Keep components focused on rendering and local interaction; fetch shared data through hooks or helpers in `lib/`. Prefer existing design tokens and Tailwind classes over new CSS.
