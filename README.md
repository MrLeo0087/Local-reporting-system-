# Civic Problem Reporting System

A lab project (BSc. CSIT, Tribhuvan University) for reporting local
infrastructure problems. Citizens submit a report with a photo and
location; government staff verify, work on, and resolve them.

```
frontend/   Plain HTML/CSS/JS — the public feed, login/register, and
            the citizen/staff/admin dashboards. No build step.
backend/    FastAPI + PostgreSQL API. See backend/README.md to run it
            and backend/ARCHITECTURE.md for how the code is organized.
```

## Running it locally

**1. Backend** (see [backend/README.md](backend/README.md) for full detail):

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in a real DATABASE_URL + JWT_SECRET_KEY
python -m app.database        # creates the tables
python create_first_admin.py  # your first login
uvicorn app.main:app --reload --port 8000
```

**2. Frontend** — just serve the folder as static files:

```bash
cd frontend
python3 -m http.server 5500
```

Open `http://localhost:5500/index.html`. `frontend/js/api.js` auto-detects
whether it's running on localhost (→ talks to `http://localhost:8000`) or
deployed (→ talks to the Render backend URL set in that file) — no manual
switching needed.

## Deploying to Render

This deploys as **two** separate Render services:

1. **Backend — Web Service**

   - Root directory: `backend`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Add a Render PostgreSQL database (or keep Neon/Supabase) and set
     `DATABASE_URL`, `JWT_SECRET_KEY`, and the other vars from `.env.example`
     in the Render dashboard.
   - Once deployed, note its URL (e.g. `https://your-api.onrender.com`).
2. **Frontend — Static Site**

   - Root directory: `frontend`
   - Open `frontend/js/api.js` and set `RENDER_API_BASE_URL` at the top to
     the backend URL from step 1, then commit and deploy.
3. Back on the backend service, set `CORS_ORIGINS` to include your
   frontend's Render URL, so the deployed frontend is allowed to call it.

Full endpoint reference and the fake-report lockout rule are documented in
[backend/README.md](backend/README.md).
