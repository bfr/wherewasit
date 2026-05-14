# Deploy to Render

## Prerequisites
- Code pushed to a GitHub repository
- Render account

## Option A: Blueprint deploy (recommended)
1. In Render, click `New +` -> `Blueprint`.
2. Connect your GitHub repo.
3. Render will detect `render.yaml`.
4. In service env vars, set `MSNO_PASSWORD` to your private password.
5. Deploy.

## Option B: Manual Web Service
1. In Render, click `New +` -> `Web Service`.
2. Connect your GitHub repo and branch.
3. Set:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Add environment variables:
   - `MSNO_PASSWORD` = your password
   - `MSNO_SECRET_KEY` = long random string
5. Deploy.

## Notes
- Password gate works via persistent session cookie (one-time unlock per browser/PWA profile).
- If assets look stale after deploy, hard refresh once.
- For app updates, push to the connected branch; Render auto-deploys.
