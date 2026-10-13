# CareerCompass AI

CareerCompass AI is a student project for exploring technology career paths. It uses a transparent, deterministic, rule-based weighted scoring system written in ordinary Python. It does **not** use machine learning, trained models, or external AI services. A match score is an estimate from the configured rules, not an employment probability, salary prediction, or guarantee of suitability.

## Features

- Student registration and sign-in with Werkzeug password hashing and Flask sessions
- Six-step guided assessment with server-side validation
- Ten career profiles with skills, responsibilities, resources, project ideas, and learning stages
- Explainable top-three matches, comparison, and skill-gap views
- Searchable career explorer
- User-specific SQLite assessment history and saved roadmap checklist progress
- Dashboard and history charts using Chart.js
- CSRF token checks on submitted forms and parameterized SQL queries

## Architecture

- `app.py` contains Flask routes, authentication, form handling, and page orchestration.
- `recommendation_engine.py` owns the career catalogue and weighted matching logic.
- `database.py` initializes SQLite tables and provides connections.
- `templates/` contains reusable Jinja pages; `static/` contains CSS and browser JavaScript.
- `tests/` contains automated checks for scoring, auth, routes, and assessment storage.

Scoring weights are configured in `recommendation_engine.py`: skills 40%, interests 30%, strengths 15%, work styles 10%, and goals 5%. Categories without answers are omitted from the denominator; this prevents a skipped question from lowering a result. When no answers are available, all scores safely return zero.

## Requirements

- Windows 10/11, Python 3.10 or newer, and PowerShell
- A browser with internet access to load Bootstrap, Bootstrap Icons, fonts, and Chart.js from their CDNs
- SQLite is included through Python's `sqlite3` module; no separate SQLite installation is required

## Run on Windows PowerShell

From the project directory:

```powershell
# Use the existing virtual environment, or create one if it is absent.
if (-not (Test-Path .venv\Scripts\python.exe)) { py -3 -m venv .venv }
\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Set a private session key for this terminal session.
$env:CAREERCOMPASS_SECRET = [guid]::NewGuid().ToString('N')
\.venv\Scripts\python.exe app.py
```

Open `http://127.0.0.1:5000`. The database and tables are initialized automatically in `instance\careercompass.sqlite3` at application startup. The generated database is ignored by Git.

Run the tests:

```powershell
\.venv\Scripts\python.exe -m pytest
```

## Safety and deployment notes

The built-in development server is for local development only. Before deploying, set a long random `CAREERCOMPASS_SECRET` using the hosting provider's secret manager, set `FLASK_DEBUG=0`, use a production WSGI server, enable HTTPS, and review the hosting platform's secure cookie settings. Never commit a real secret, database containing personal data, or virtual environment. For a public service, add rate limiting, account recovery, privacy/retention notices, and a production-grade CSRF package/configuration review.

External career-resource links are suggestions, not endorsements; verify availability and content before relying on them.
