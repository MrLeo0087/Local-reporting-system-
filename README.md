# Local Civic Problem Reporting System — Backend

FastAPI + PostgreSQL backend for an E-Governance lab project (BSc. CSIT,
Tribhuvan University). Citizens report local infrastructure problems with a
photo and location; government staff review, verify, and resolve them.

New to this codebase (or coming back after a while)? Read
[ARCHITECTURE.md](ARCHITECTURE.md) first — it walks through how a
request flows through the code and where each business rule lives.

## 1. Requirements

- Python 3.11+
- A PostgreSQL database (a free one on [Neon](https://neon.tech) or
  [Supabase](https://supabase.com) works fine — no local install needed)

## 2. Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

```
DATABASE_URL=postgresql://username:password@host:port/database_name
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=120
UPLOAD_DIR=uploads
MAX_UPLOAD_MB=5
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000
PORT=8000
```

Make sure the `uploads/` folder exists at the project root (it's already in
this repo with a `.gitkeep` file, so you're set).

## 3. Create the database tables

```bash
python -m app.database
```

This creates every table (`citizens`, `staff`, `reports`, `status_logs`) from
the SQLAlchemy models. Run it once, and again any time you point at a fresh
database.

## 4. Create your first Admin account

Admins create Staff accounts through the API — but nothing creates the
first Admin. Run the seed script once:

```bash
python create_first_admin.py
```

It will prompt for a name, email, and password and insert an admin row
directly.

## 5. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the interactive Swagger UI — test
every endpoint there before touching the frontend.

## 6. API overview

| Method | Path | Who | Purpose |
|---|---|---|---|
| POST | `/citizens/register` | anyone | Create a citizen account |
| POST | `/citizens/login` | anyone | Get a citizen JWT |
| GET | `/citizens/me` | citizen | Current citizen's profile |
| POST | `/reports` | citizen | Submit a report (multipart form + photo) |
| GET | `/reports` | anyone | Public feed (filter with `?category=` `&status_filter=`) |
| GET | `/reports/mine` | citizen | Citizen's own reports |
| GET | `/reports/{id}` | anyone | Single report + status history |
| POST | `/staff/login` | staff/admin | Get a staff JWT |
| GET | `/staff/reports` | staff/admin | Reports in your category+ward (admin sees all) |
| PATCH | `/staff/reports/{id}/verify` | staff/admin | Mark verified |
| PATCH | `/staff/reports/{id}/reject` | staff/admin | Reject with a reason |
| PATCH | `/staff/reports/{id}/progress` | staff/admin | Mark in progress + ETA |
| PATCH | `/staff/reports/{id}/complete` | staff/admin | Mark completed |
| POST | `/admin/staff` | admin | Create a staff account |
| GET | `/admin/staff` | admin | List staff accounts |
| PATCH | `/admin/citizens/{id}/disable` | admin | Permanently disable a citizen |

Every protected route expects `Authorization: Bearer <token>`.

## 7. Fake-report lockout

If a citizen gets 3 reports rejected with reason `false_report` within a
7-day window, they're locked out of submitting new reports for 7 days. This
is enforced automatically in `PATCH /staff/reports/{id}/reject` and checked
on every `POST /reports`. The counter and lock timestamp are never exposed
in citizen-facing or public responses — only staff/admin endpoints see them
indirectly (an admin can also permanently disable a repeat offender via
`PATCH /admin/citizens/{id}/disable`).

## 8. Serving the frontend

For local development, either open the HTML files in `../frontend` directly
in your browser, or serve them as static files. Make sure `js/api.js` points
at your backend URL (`http://localhost:8000` while developing).

## 9. Deploying to Render.com

1. Push this repo to GitHub.
2. Create a new **Web Service** on Render, connect the repo, set the start
   command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Add a Render PostgreSQL database (or keep using Neon/Supabase) and set
   `DATABASE_URL` accordingly.
4. Set the other environment variables from `.env` in Render's dashboard.
   Never commit your real `.env` file — it's already in `.gitignore`.
5. Render gives you HTTPS automatically.
