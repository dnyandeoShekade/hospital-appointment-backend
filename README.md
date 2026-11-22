# Hospital Appointment Backend

FastAPI REST API for the Hospital Appointment System. The backend authenticates users, applies role and ownership checks, calculates provider availability, and stores application data in PostgreSQL.

## Features

- Customer registration and login with signed bearer tokens.
- User roles for customers, providers, and administrators.
- Approved provider profiles and active services.
- Provider working hours and blocked periods.
- Appointment slot generation in each provider's time zone.
- Appointment booking, listing, cancellation, and rescheduling.
- Administrator-only provider account, profile, service, and weekly schedule creation.
- PostgreSQL schema migrations managed by Alembic.

## Stack

- Python 3.11+
- FastAPI and Pydantic
- SQLAlchemy
- PostgreSQL with psycopg
- Alembic

## Run locally

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set these values in `.env`:

```dotenv
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
JWT_SECRET_KEY=replace-with-a-long-random-secret
FRONTEND_ORIGIN=http://localhost:3000
```

Use the URL from your PostgreSQL provider and URL-encode special characters in the username or password. Generate a random signing secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Apply migrations and start the API:

```powershell
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API health: `http://localhost:8000/api/v1/health`
Swagger docs: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`

## Main routes

All versioned routes use the `/api/v1` prefix.

| Area | Routes | Access |
| --- | --- | --- |
| Authentication | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | Registration/login are public; `/me` requires a token |
| Providers | `GET /providers`, `GET /providers/{provider_id}` | Public |
| Services | `GET /providers/{provider_id}/services` | Public |
| Availability | `GET /providers/{provider_id}/availability?date=YYYY-MM-DD&service_id=...` | Public |
| Appointments | `POST /appointments`, `GET /appointments/me`, `GET /appointments/{id}`, `PATCH /appointments/{id}/cancel`, `PATCH /appointments/{id}/reschedule` | Bearer token; only customers can book |
| Admin provider setup | `POST /admin/providers` | Administrator token |
| Availability management | `POST /providers/{provider_id}/working-hours`, `POST /providers/{provider_id}/blocked-times` | Provider owner or administrator |

New registrations receive the customer role. There is no public administrator-promotion endpoint; provision the first administrator through a trusted, private setup process.

## Availability and booking rules

Slots are generated in 15-minute increments for the provider's working periods. The availability response excludes past times, blocked periods, and appointments that overlap an active booking. Booking also rechecks working hours and conflicts before saving the appointment.

## Database

The initial schema is in `alembic/versions/3c2139c95004_initial.py`. After configuring `DATABASE_URL`, run `alembic upgrade head` to create/update tables.

## Tests

Run the backend test suite from this directory:

```powershell
pytest
```

## Security

- `.env` is gitignored. Never commit database connection URLs, JWT signing keys, real passwords, access tokens, or patient data.
- Use a unique, strong `JWT_SECRET_KEY`; set `ENVIRONMENT=production` and the exact frontend `FRONTEND_ORIGIN` for a deployed setup.
- Provider and appointment actions enforce role and ownership checks in the API.
