# GitHub Automation

GitHub Actions workflows for CI and deployment.

## Workflows

- `deploy-backend.yml`: installs Python dependencies, imports the FastAPI app, and deploys backend changes to Railway.
- `deploy-frontend.yml`: installs frontend dependencies, runs `npm run build`, and deploys to Vercel.
- `pr-check.yml`: lightweight backend Ruff and frontend lint checks for pull requests.

## Required Secrets

Configure secrets in GitHub Repository Settings -> Secrets and variables -> Actions. See root `SECRETS_GUIDE.md` for the full list.

Common secrets:

- `RAILWAY_TOKEN`
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_MAPBOX_TOKEN`
