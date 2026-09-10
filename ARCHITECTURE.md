# How this backend works

A quick walkthrough for future-you. The code itself is already fairly
small and flat — this doc is a map, not a replacement for reading it.

## The folders, in one line each

```
app/
  main.py          # creates the FastAPI app, wires everything together
  config.py        # one Settings object, loaded from .env
  database.py      # SQLAlchemy engine/session setup + get_db()
  models/          # tables (SQLAlchemy) — what's stored in Postgres
  schemas/         # shapes (Pydantic) — what goes in/out of the API as JSON
  auth/            # password hashing, JWT tokens, "who is calling this?"
  routers/         # the actual endpoints, grouped by who uses them
  utils/           # small standalone helpers (photo saving, lockout rule)
```

**Models vs. schemas** is the one distinction worth being sure about:
a *model* (`models/report.py`) is a database table. A *schema*
(`schemas/report.py`) is what the API accepts or returns as JSON. They
often have near-identical fields, but keeping them separate means the
API never accidentally leaks a DB-only column (see `CitizenOut`, which
deliberately drops `fake_report_count`).

## A request, end to end

Example: a staff member clicks "Verify" on a report.

1. Browser sends `PATCH /staff/reports/{id}/verify` with
   `Authorization: Bearer <token>` — [routers/staff.py](app/routers/staff.py).
2. FastAPI resolves the route's `Depends(get_current_staff)` first
   ([auth/dependencies.py](app/auth/dependencies.py)): it decodes the
   JWT, loads the `Staff` row from the DB, and 401s if anything's off.
   This is the "who is calling this?" check.
3. `_get_report_for_staff()` loads the report and checks the staff
   member is allowed to touch it (admins can touch anything; regular
   staff only their own category+ward).
4. The route function updates `report.status`, adds a `StatusLog` row
   (an audit trail entry), and commits both in one transaction.
5. The response is built through `ReportStaffOut` (a schema) — this is
   where staff-only fields like the citizen's phone number get
   attached, which the public-facing `ReportOut` never includes.

Every other endpoint follows the same shape: `Depends` for auth →
load/validate → mutate → commit → return through a schema.

## The three kinds of "user"

- **Citizen** — registers/logs in via `/citizens/*`, submits reports,
  sees their own reports. Token role: `"citizen"`.
- **Staff** — created by an admin (no self-registration), logs in via
  `/staff/login`, only sees/acts on reports in their assigned
  `category` + `ward_no`. Token role: `"staff"`.
- **Admin** — a `Staff` row with `role="admin"`. Sees and acts on
  everything, and is the only one who can create staff accounts
  (`/admin/staff`) or disable a citizen.

Citizen tokens and staff tokens are separate JWTs (different
`get_current_*` dependencies), so a citizen token can never be used to
call a staff route, even by accident.

## Report status flow

```
submitted → verified → in_progress → completed
    └────────────────→ rejected
```

Every transition writes a `StatusLog` row (who, when, optional
comment) — that's what powers the "Status History" timeline on the
report detail page. Status names live in
[models/report.py](app/models/report.py) (`REPORT_STATUSES`) — that's
the one place to look if a status ever needs to change.

## The one non-obvious business rule

[utils/fake_report_lock.py](app/utils/fake_report_lock.py): if a
citizen gets 3 reports rejected as `false_report` within 7 days, they
lose the ability to submit new reports for 7 days. It's checked on
every `POST /reports` and updated whenever a staff member rejects a
report with that reason. The comments in that file explain the "why"
in more depth.

## Running it locally

See [README.md](README.md) for full setup. Short version:

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in a real DATABASE_URL + JWT_SECRET_KEY
python -m app.database  # creates tables
python create_first_admin.py  # your first login
uvicorn app.main:app --reload --port 8000
```

Then visit `http://localhost:8000/docs` — Swagger UI, generated
automatically from the schemas above, lets you try every endpoint
without touching the frontend at all. That's the fastest way to
understand what an endpoint expects/returns before you go read its code.
