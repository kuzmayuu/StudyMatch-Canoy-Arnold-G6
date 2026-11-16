# StudyMatch: Account Feature (Phase 1)

Full-stack Django project (Django templates for the frontend) using PostgreSQL or Supabase (PostgreSQL). SQLite is not used.

## 1. Setup

1. **Python 3.10+** and PostgreSQL (or a Supabase project).
2. Create and activate a virtual environment, then install packages:

   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your values.
   - **Local PostgreSQL:** create an empty database first (`CREATE DATABASE studymatch;`), then set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
   - **Supabase:** copy the connection string from *Project Settings > Database*, and set it as `DATABASE_URL` (keep `?sslmode=require`).
   - `ALLOWED_EMAIL_DOMAIN=cit.edu` limits registration to CIT-U emails (BR-01). Change it if your school email domain differs, or leave it empty while testing.
4. Create the tables. The `accounts` migration is generated from the models:

   ```bash
   python manage.py makemigrations accounts
   python manage.py migrate
   ```
5. Create an **administrator** (admins are created here, never through public registration):

   ```bash
   python manage.py createsuperuser
   ```
6. Run the server and open http://127.0.0.1:8000/

   ```bash
   python manage.py runserver
   ```

Run the automated tests with `python manage.py test accounts` (Django creates a temporary test database, so your PostgreSQL user needs permission to create databases; on Supabase, run tests against a local PostgreSQL instead).

## 2. How each requirement is met

| Requirement | Where |
|---|---|
| Registration form with validation (required fields, valid email, unique email and student ID, matching passwords), success and error messages | `accounts/forms.py` (`RegistrationForm`), `views.register_view`, `templates/accounts/register.html` |
| Passwords hashed with Django's built-in authentication | Custom user model with `set_password()` (PBKDF2); never stored as plain text |
| Login with clear error on invalid credentials, logout ends the session | `LoginForm`, `login_view`, `logout_view` (POST only) |
| Protected pages | `@login_required` and `@role_required` in `accounts/decorators.py`; logged-out users are sent to the login page |
| Two roles with separate dashboards | `User.role` = `STUDENT` or `ADMIN`. After login each user goes to `/dashboard/student/` or `/dashboard/admin/` |
| Cannot open another role's dashboard by URL | `role_required` returns a 403 "Access denied" page |
| View and edit own profile | `/profile/` and `/profile/edit/`; there is no user id in the URL, so users only ever see their own |

## 3. Business rules from the SDD implemented in this phase

BR-01 (CIT-U email domain), BR-02 (unique student ID and email), BR-03 (password with letter and number, hashed), BR-04 (account locks for 15 minutes after 5 failed logins), BR-05 (suspended accounts cannot log in), BR-06 (users edit only their own profile), BR-32 (only an administrator can suspend or restore accounts; shown on the admin dashboard).

## 4. Project structure

```
studymatch/        project settings and root URLs
accounts/          models (User, Profile), forms, views, urls, decorators, validators, admin, tests
templates/         base.html and accounts/*.html (Django templates)
static/css/        style.css
```

## 5. Notes

- The `users` and `profiles` tables follow the data dictionary in the SDD (the password hash is stored in Django's `password` column).
- Uploaded profile photos are saved to `media/` (served by Django only while `DEBUG=True`).
- The "Find partners / Groups / Sessions" cards on the student dashboard are placeholders for the next phases.
