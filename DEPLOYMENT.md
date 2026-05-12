# 상생나침반 Deployment

배포 완료: 2026-05-13

## URLs

- Frontend: https://winwin-compass.vercel.app
- Backend: https://winwin-compass-production.up.railway.app
- API Docs: https://winwin-compass-production.up.railway.app/docs
- Health Check: https://winwin-compass-production.up.railway.app/health
- GitHub: https://github.com/drews31415/winwin-compass

## Services

- Vercel project: `winwin-compass`
- Railway project: `winwin-compass`
- Railway service: `winwin-compass`

## Production Environment

- `NEXT_PUBLIC_API_URL=https://winwin-compass-production.up.railway.app`
- `CORS_ORIGINS=http://localhost:3000,https://winwin-compass.vercel.app,https://golmok-compass.vercel.app`

## Smoke Test Commands

```bash
curl https://winwin-compass-production.up.railway.app/health
curl https://winwin-compass-production.up.railway.app/api/v1/report/3110016
curl "https://winwin-compass-production.up.railway.app/api/v1/ml/forecast/3110016?periods=4"
curl https://winwin-compass.vercel.app
```
