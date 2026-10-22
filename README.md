# College Management Portal

A Django web application for managing a college: student records, departments,
faculty accounts and a self-service workflow for students who spot a mistake in
their own record.

The project started as a public "Student Portal" (no login, free-text branch
names). It is now a role based portal with three roles - **Admin**, **Faculty**
and **Student** - and it keeps the existing student rows and photos.

---

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project layout](#project-layout)
- [Roles and permissions](#roles-and-permissions)
- [Data model](#data-model)
- [Setup](#setup)
- [Management commands](#management-commands)
- [Configuration](#configuration)
- [Running the tests](#running-the-tests)
- [Deployment](#deployment)
- [Known limitations](#known-limitations)

---

## Features

**Admin**

- Dashboard with counters (students, departments, faculty, pending corrections)
- Full CRUD on student records, including a photo upload
- Full CRUD on departments, with an audit trail of every change
- Create and deactivate faculty accounts, assign them to departments
- Create student login accounts and link/unlink them with a student record
- Review, approve or reject student correction requests, optionally applying
  the change to the official record
- Django admin site (superusers only) at `/django-admin/`

**Faculty**

- Dashboard with the departments they are assigned to
- Read-only access to the whole student directory (search, filter, paginate)
- Edit a limited set of fields (`description`, `office_location`,
  `contact_email`) on the departments they are assigned to

**Student**

- See their own profile, department and section
- Ask for a correction to their name, department or section
- Follow the status of their correction requests

**Shared**

- Searchable and filterable student directory with pagination (12 per page)
- Role aware navigation, mobile friendly layout, accessible forms
- Progressively enhanced JavaScript (the portal works without it)

---

## Tech stack

| Layer      | Choice                                   |
|------------|------------------------------------------|
| Backend    | Python 3.13, Django 5.0                  |
| Database   | SQLite (`db.sqlite3`)                    |
| Templates  | Django templates (no template engine add-on) |
| Frontend   | Hand written CSS and vanilla JavaScript  |
| Images     | Pillow (validation of uploaded photos)   |

Only two third party packages are needed: `Django` and `pillow`.

---

## Project layout

```
College Portal/
├── manage.py
├── requirements.txt
├── README.md
├── db.sqlite3                     # SQLite database (not in git)
├── media/                         # uploaded student photos (not in git)
├── student_portal/                # Django project package
│   ├── settings.py                # development settings (environment driven)
│   ├── settings_production.py     # production settings (secure by default)
│   ├── test_runner.py             # runs the tests against a temporary MEDIA_ROOT
│   └── urls.py                    # root URL conf
└── app1/                          # the portal application
    ├── models.py                  # Department, Students, FacultyProfile, ...
    ├── forms.py                   # all forms (student, department, faculty, ...)
    ├── permissions.py             # role helpers and view decorators
    ├── admin.py                   # Django admin registrations
    ├── views/                     # views split per topic
    │   ├── common.py              # shared helpers (search, filter, paginate)
    │   ├── public.py              # landing page, login, logout, password change
    │   ├── dashboards.py          # role specific dashboards
    │   ├── students.py            # student records
    │   ├── departments.py         # departments + audit trail
    │   ├── faculty.py             # faculty management
    │   ├── accounts.py            # student login accounts
    │   └── portal.py              # student self service
    ├── templates/                 # all HTML templates
    ├── static/app1/
    │   ├── css/app.css
    │   └── js/app.js
    ├── management/commands/       # create_admin, create_faculty, setup_roles
    ├── migrations/                # 0001 ... 0008
    └── tests/                     # the test suite
```

---

## Roles and permissions

The role of a user is **always** derived from Django's own data
(`user.is_superuser` and the group membership). It is never read from a form
field or from a URL, so a visitor cannot promote themselves.

| Area | Admin | Faculty | Student |
|------|:-----:|:-------:|:-------:|
| Student directory (read) | yes | yes | no |
| Student record: create / edit / delete | yes | no | no |
| Departments: read | yes | yes (own only) | no |
| Departments: create / delete / deactivate | yes | no | no |
| Departments: edit | yes | limited fields, own departments | no |
| Faculty accounts: manage | yes | no | no |
| Student login accounts: manage | yes | no | no |
| Correction requests: review | yes | no | no |
| Correction requests: submit / follow | no | no | yes (own only) |
| Own profile / own department | yes | yes | yes |

How the rules are enforced:

* `app1/permissions.py` holds `role_required`, `admin_required`,
  `faculty_required`, `student_required` and `active_login_required`. The
  views use them, so the same rule applies no matter which URL is used.
* The **Student** group deliberately has *no* model permissions. A student
  reaches their own record through the one-to-one `Students.account` link
  (`student_record_for()`), which is checked explicitly in the view. That is
  safer than handing out a blanket `view_students` permission.
* The **Faculty** group gets `view_students`, `view_department`,
  `change_department` and `view_facultyprofile`. Which *fields* faculty may
  change is enforced by `DepartmentFacultyEditForm` plus the object level
  check `faculty_can_edit_department()`.
* The **Admin** group gets every `app1` permission but **no** `auth.User` /
  `auth.Group` permission, so an admin cannot escalate to superuser through
  the portal.
* `Students.department` uses `on_delete=PROTECT`. A department that still has
  students or faculty cannot be deleted - deactivate it instead.
* A deactivated account is signed out on the next request
  (`_login_guard()` drops the stale session).

---

## Data model

| Model | Purpose |
|-------|---------|
| `Department` | code, name, description, office location, contact email, active flag |
| `Students` | name, id, department (FK), section, photo, linked login account |
| `FacultyProfile` | employee id, designation, phone, departments (M2M) |
| `DepartmentChangeLog` | who changed a department, when and which fields moved |
| `CorrectionRequest` | a student's request to fix their own record |

The students table keeps its original name (`Students`) and its original
primary key, so the existing rows keep working.

### Migration of the old data

The old portal stored the branch as free text (`student_branch`). The
migrations replace it with a real foreign key **without losing data**:

1. `0004_college_portal_models` - adds the new tables and the new columns
   (all nullable, because SQLite cannot add a `NOT NULL` column to a table
   that already has rows).
2. `0005_migrate_branch_to_department` - every distinct branch value becomes
   one department and the students are pointed at it. Students without a
   branch are moved to an explicit `UNASSIGNED` department and reported in
   the migration output. Reversing the migration only clears the foreign key.
3. `0006_finalize_student_fields` / `0007_remove_students_branch` - the
   timestamps are filled in, the columns are tightened and the old text
   column is dropped.
4. `0008_seed_role_groups` - creates the `Admin`, `Faculty` and `Student`
   groups.

The behaviour of this migration is covered by
`app1/tests/test_models.py::BranchToDepartmentMigrationTests`.

A backup of the database and the media folder is created before such a change
- see the `backups/` folder (not in git).

---

## Setup

```bash
# 1. clone
git clone <repository-url>
cd "College Portal"

# 2. virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. dependencies
pip install -r requirements.txt

# 4. database
python manage.py migrate

# 5. your first administrator (password is asked for interactively)
python manage.py create_admin --username principal --email principal@college.edu

# 6. run the server
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in a browser.

Useful URLs:

| URL | Purpose |
|-----|---------|
| `/` | landing page |
| `/accounts/login/` | sign in |
| `/dashboard/` | dashboard of the current role |
| `/students/` | student directory (admin + faculty) |
| `/departments/` | departments |
| `/manage/faculty/` | faculty management (admin) |
| `/manage/student-accounts/` | student login accounts (admin) |
| `/manage/correction-requests/` | correction requests (admin) |
| `/my/profile/` | own profile (student) |
| `/django-admin/` | Django admin site (superuser) |

---

## Management commands

```bash
# Create the first administrator. The password is typed in and checked by
# Django's own password validators.
python manage.py create_admin
python manage.py create_admin --username principal --email principal@college.edu
python manage.py create_admin --username principal --email principal@college.edu --no-input
#   --no-input creates the account without a password (it cannot sign in
#   until an administrator sets one with "manage.py changepassword")

# Create a faculty account and assign it to departments (codes, comma separated).
python manage.py create_faculty --username iyer --email iyer@college.edu \
    --employee-id EMP-001 --first-name Meera --last-name Iyer \
    --designation "Associate Professor" --phone 9000000000 --departments AIML,CSE

# Recreate the role groups and (re)assign their permissions.
python manage.py setup_roles
```

---

## Configuration

The settings read the environment. A `.env` file in the project root is picked
up automatically (simple `KEY=value` lines, no extra dependency).

| Variable | Default | Meaning |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | development key | **change in production** |
| `DJANGO_DEBUG` | `True` | `False` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1],testserver` | comma separated |
| `DJANGO_TIME_ZONE` | `UTC` | e.g. `Asia/Kolkata` |
| `DJANGO_DB_PATH` | `db.sqlite3` | path to the SQLite file |
| `DJANGO_EMAIL_BACKEND` | console backend | Django email backend |
| `DJANGO_LOG_LEVEL` | `INFO` | logging level |
| `PORTAL_MAX_IMAGE_SIZE` | `2097152` (2 MB) | maximum photo size in bytes |

Uploads are validated again in the forms: only jpg, png, gif and webp are
accepted and the size limit is enforced before the file is stored.

---

## Running the tests

```bash
python manage.py test              # the whole suite
python manage.py test app1.tests.test_auth
python manage.py test -v 2         # verbose
```

The suite covers authentication and session handling, the role helpers, the
student records, the directory, the departments and their audit trail, the
faculty management, the login accounts, the student self service, the
management commands, the models and the data migration.

While the tests run, `MEDIA_ROOT` points at a temporary folder
(`student_portal/test_runner.py`), so a test run never writes into the real
`media/` directory.

---

## Deployment

1. Copy the project to the server, install the dependencies.
2. Set the environment variables - at least `DJANGO_SECRET_KEY`,
   `DJANGO_DEBUG=False` and `DJANGO_ALLOWED_HOSTS`.
3. Use the production settings:

   ```bash
   export DJANGO_SETTINGS_MODULE=student_portal.settings_production
   python manage.py migrate
   python manage.py collectstatic
   python manage.py runserver 0.0.0.0:8000     # behind nginx/Apache in production
   ```

4. Serve `/media/` and `/static/` from the web server.

`student_portal/settings_production.py` turns on the secure cookies, the HSTS
header, the SSL redirect and the strict host header. Check it with:

```bash
DJANGO_SETTINGS_MODULE=student_portal.settings_production python manage.py check --deploy
```

---

## Known limitations

- SQLite is used. It is fine for a single college and for a demo, but a
  busy deployment should switch to PostgreSQL (only `DATABASES` in the
  settings has to change).
- There is no password reset by email yet; an administrator sets a new
  password with `manage.py changepassword`.
- The correction workflow only covers name, department and section.
- `manage.py create_faculty` asks for the password interactively, so it cannot
  run unattended; use `--no-input` style automation or the Django admin for
  that.
