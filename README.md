# StudyMatch

A study-partner platform for CIT-U students. This repository contains **Phase 1: Accounts** — registration, login, role-based dashboards and profile management.

**Stack:** Django 5 (server-rendered templates) · PostgreSQL hosted on **Supabase** · Python 3.10+

---

## Features

- Student registration with validation (CIT-U email domain, unique email and student ID, password rules)
- Login / logout, with account lockout after repeated failed attempts
- Two roles, each with its own dashboard: **Student** and **Admin**
- View and edit your own profile (program, year level, contact number, bio, photo)
- Admins can suspend and restore student accounts
- Protected pages: logged-out users go to login; opening another role's dashboard returns a 403 page

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5 (`>=5.0,<6.0`) |
| Database | Supabase (PostgreSQL), or local PostgreSQL |
| Frontend | Django templates + `static/css/style.css` |
| DB driver | `psycopg2-binary` |
| Config | `python-dotenv`, `dj-database-url` |
| Images | `Pillow` |

SQLite is **not** used.

---

## Getting started

### 1. Prerequisites

- Python 3.10 or newer
- A [Supabase](https://supabase.com) account and project (free tier is fine)

### 2. Install

```bash
python -m venv venv
venv\Scripts\activate            
pip install -r requirements.txt
```

### 3. Connect to Supabase

1. In the [Supabase dashboard](https://supabase.com/dashboard), create a project and remember the **database password** you set.
2. Click **Connect** at the top of the project (or go to **Project Settings → Database**) and copy the **URI** connection string.
3. Copy the env template and fill it in:

   ```bash
   cp .env.example .env            # Windows: copy .env.example .env
   ```

4. In `.env`, set `DATABASE_URL` to your Supabase URI and keep `?sslmode=require` at the end:

   ```env
   SECRET_KEY=generate-a-long-random-string
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1

   DATABASE_URL=postgresql://postgres.<project-ref>:<YOUR-PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require

   ALLOWED_EMAIL_DOMAIN=cit.edu
   ```

   When `DATABASE_URL` is set, it is used and the `DB_*` variables are ignored. If your password contains special characters (`@`, `/`, `:`, `#`…), URL-encode them (e.g. `@` → `%40`).

> **Never commit `.env`.** It is already in `.gitignore`. Keep your database password and `SECRET_KEY` private.

#### Which Supabase connection string?

| Option | Port | Use when |
|---|---|---|
| Session pooler | `5432` | Default choice; works with Django as configured here |
| Direct connection | `5432` (`db.<ref>.supabase.co`) | Your network supports IPv6 |
| Transaction pooler | `6543` | Serverless/short-lived deployments. Django needs `DISABLE_SERVER_SIDE_CURSORS = True` in the database settings for this mode |

If you get a "could not translate host name" or timeout error on the direct connection, switch to the pooler string.

### 4. Create the tables

The initial migration is included, so just apply it:

```bash
python manage.py migrate
```

This creates the app tables plus Django's own tables (sessions, admin log, auth permissions) in your Supabase database. You can see them under **Table Editor** in the dashboard.

If you change `accounts/models.py`, generate a new migration first with `python manage.py makemigrations accounts`.

### 5. Create an administrator

Admins are never created through public registration:

```bash
python manage.py createsuperuser
```

### 6. Run the server

```bash
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Register a student account (using an email that ends in `@cit.edu`), or log in as the admin.

### Using local PostgreSQL instead

Leave `DATABASE_URL` unset (or commented out), create an empty database (`CREATE DATABASE studymatch;`), and set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` in `.env`.

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | insecure dev key | Django secret key. **Set your own.** |
| `DEBUG` | `True` | Debug mode; set to `False` in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hostnames |
| `DATABASE_URL` | — | Supabase (or any Postgres) connection string. Takes priority over `DB_*` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | `studymatch` / `postgres` / — / `localhost` / `5432` | Local PostgreSQL settings |
| `ALLOWED_EMAIL_DOMAIN` | `cit.edu` | Only emails on this domain can register. Empty = allow any (for testing) |

---


### Supabase notes

- Django connects as a normal Postgres client and manages its own tables, so you don't need Supabase Auth or the Supabase client libraries for this project. Users live in `accounts_user`, not in Supabase's `auth.users`.
- Tables created by Django are in the `public` schema. Supabase may flag them as having **Row Level Security disabled**. Since access goes through Django (and not the Supabase REST API), you can keep your database password private and, optionally, enable RLS on these tables in the dashboard to block anonymous API access.
- Profile photos are saved to the local `media/` folder, **not** to Supabase Storage. On hosts with an ephemeral filesystem, uploaded photos will be lost on redeploy.

---


## Routes

| URL | Access | Description |
|---|---|---|
| `/` | Anyone | Redirects to login or your dashboard |
| `/register/` | Anyone | Create a student account |
| `/login/` | Anyone | Log in |
| `/logout/` | Logged in (POST) | Log out |
| `/dashboard/` | Logged in | Redirects to the dashboard for your role |
| `/dashboard/student/` | Students | Student dashboard |
| `/dashboard/admin/` | Admins | User stats and suspend/restore controls |
| `/profile/`, `/profile/edit/` | Logged in | View and edit your own profile |
| `/django-admin/` | Staff | Built-in Django admin |

---

## Project structure

```
studymatch/        Project settings and root URLs
accounts/          Models (User, Profile), forms, views, urls, decorators,
                   validators, signals, admin, migrations, tests
templates/         base.html and accounts/*.html
static/css/        style.css
manage.py
requirements.txt
.env.example       Template for your local .env
```

## Running the tests

```bash
python manage.py test accounts
```

Django creates a temporary test database, so the database user needs permission to create databases. The Supabase `postgres` user may not allow this, so **run tests against a local PostgreSQL** (use the `DB_*` variables and leave `DATABASE_URL` unset).


## Roadmap

The "Find partners / Groups / Sessions" cards on the student dashboard are placeholders for the next phases.

## Author

Canoy, Arnold — Group 6