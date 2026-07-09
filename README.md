# TrekManager — Trekking Management Application

A role-based web application for organising trekking activities. Admins manage treks
and people, trek staff run their assigned treks, and trekkers browse, book, and track
their adventures.

Built with **Flask + SQLite + Bootstrap 5** (Jinja2 templates). The database is created
programmatically on first run — no manual DB setup required.

---

## Tech stack

| Layer      | Technology                                   |
|------------|----------------------------------------------|
| Backend    | Flask, Flask-Login, Flask-SQLAlchemy         |
| Database   | SQLite (auto-created via SQLAlchemy models)  |
| Frontend   | Jinja2, HTML5, Bootstrap 5, Bootstrap Icons  |
| API        | Flask Blueprint REST API at `/api/v1`        |

No JavaScript is used for any core requirement. Charts are rendered with pure
CSS/Bootstrap progress bars.

---

## Setup & run

```bash
# 1. (optional) create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install flask flask-login flask-sqlalchemy
#   — or, if using uv:  uv sync

# 3. run
python app.py
```

Then open **http://127.0.0.1:5000/**.

On first launch the app creates `instance/tma.db` and seeds the admin account
automatically.

### Default admin login
| Username | Password   |
|----------|------------|
| `admin`  | `admin123` |

Admin is pre-seeded and cannot be registered. Staff and trekkers self-register.

---

## Roles & features

### Admin
- Dashboard with totals (treks / users / staff / bookings) and CSS statistics charts
  (popular treks, bookings by status, treks by status)
- Create, edit, delete treks; assign staff; control trek status
- Approve or blacklist staff and users
- View all bookings; search treks / users / staff by name or ID

### Trek Staff
- Self-register (requires admin approval before dashboard access)
- View assigned treks and per-trek participant counts
- Update available slots and trek status (Open / Closed / **Started** / Completed)
- View the participant list for each assigned trek

### User (Trekker)
- Self-register and log in
- Browse open treks; filter by difficulty and location; search
- Book treks (overbooking and non-open treks are blocked; no duplicate bookings)
- Cancel bookings (slot is returned) and view booking history
- Edit profile

### Trek lifecycle
When a trek is marked **Completed** (by staff or admin), all its active bookings are
automatically moved to **Completed**, building each trekker's trip history.

---

## REST API

Session-authenticated JSON API under `/api/v1`:

| Method | Endpoint                  | Role                    |
|--------|---------------------------|-------------------------|
| GET    | `/treks`, `/treks/<id>`   | public                  |
| POST   | `/treks`                  | admin                   |
| PUT    | `/treks/<id>`             | admin / assigned staff  |
| DELETE | `/treks/<id>`             | admin                   |
| GET    | `/users`, `/users/<id>`   | admin (or self)         |
| GET    | `/bookings`               | role-scoped             |
| POST   | `/bookings`               | trekker                 |
| PUT    | `/bookings/<id>`          | owner / admin / staff   |

---

## Project structure

```
app.py             # routes, app config, auth, admin/staff/user views
models.py          # SQLAlchemy models + admin seeding
api.py             # /api/v1 REST blueprint
templates/         # Jinja2 templates (base + per-page)
static/theme.css   # Bootstrap customisation layer
instance/tma.db    # SQLite DB (auto-created, git-ignored)
```
