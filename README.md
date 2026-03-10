# Student Portal

A web-based Student Portal built using Django (Python) for the backend and HTML/CSS/JavaScript for the frontend. The project was originally called `project1` but has been renamed to `student_portal`.

## Features

- Register students with name, ID, branch, section, and optional photo
- List all students
- Search by ID or name
- View individual student details
- Update or delete student records
- All operations are public (no authentication)

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ajaysai157/student-portal.git
   cd student-portal
   ```
2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # on Windows
   source venv/bin/activate  # on macOS/Linux
   ```
3. **Install requirements**
   ```bash
   pip install -r requirements.txt
   ```
4. **Apply migrations and run the server**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
5. **Visit** `http://127.0.0.1:8000/` in your browser.

## Development notes

- The Django project package is `student_portal` (not `project1`).
- Media uploads are stored in the `media/` directory.
- Database is SQLite (`db.sqlite3`), which is ignored by git.

## Ignored files

The following are excluded from version control:

- `__pycache__/`, `*.pyc`
- `db.sqlite3`
- `media/`
- `.env`
- `.vscode/`

Feel free to extend functionality or add authentication as needed.

