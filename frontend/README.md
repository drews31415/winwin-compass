# Frontend

Next.js App Router frontend for 상생나침반.

## Structure

```text
app/             Routes and page-level screens
components/      Shared UI and domain components
lib/             API client, hooks, utility helpers
tests/           Playwright deployment smoke tests
public/          Static assets
```

## Commands

```bash
npm install
npm run dev
npm run build
npm run lint
```

`npm run dev` starts the local app, `npm run build` validates the production bundle, and `npm run lint` runs Next linting.

## Environment

Set these in `.env.local` for local development:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MAPBOX_TOKEN=pk...
```

If Mapbox token is absent or invalid, map components fall back to Leaflet/OpenStreetMap.

## Deployment

```bash
vercel --prod --yes
```

Production URL: https://winwin-compass.vercel.app

## Main Pages

- `/chat`: AI 상담
- `/map`: 상권 지도
- `/report`: 상권 리포트
- `/policy`: 지원사업 매칭
- `/marketing`: 마케팅 문구 자동 생성
