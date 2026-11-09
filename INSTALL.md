# Installing Releasesmith

Releasesmith is a single Python service: FastAPI + Jinja2 server-rendered pages over a SQLite file.
There is nothing to compile, no Docker image, no database server and no network access needed at
runtime.

## Prerequisites

| Requirement | Notes |
| --- | --- |
| Python 3.11+ | `python3 --version` must report 3.11 or newer. |
| pip | Ships with Python; `python3 -m pip --version`. |
| A writable working directory | The SQLite file and `.env` are created next to the code. |

Nothing else is installed at the system level. `install.sh` only uses the Python package manager.

## 1. Install the dependencies

Either run the setup script, which installs packages, creates the schema, seeds the demo data and
then exits:

```bash
bash install.sh
```

or do the two steps yourself:

```bash
python3 -m pip install -r requirements.txt
```

## 2. Create the database and seed the demo data

This is its own step, and it is idempotent — run it as many times as you like:

```bash
python3 -m app.seed
```

It prints how many users and releases it created. It never starts the web server. The same seeding
check also runs on every application boot, so a fresh clone renders real content even if you skip
this step.

## 3. Run the app

```bash
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Open <http://localhost:8000>. You will be redirected to the sign-in screen (`/signin`; `/login` serves the same card).

`uvicorn main:app --host 0.0.0.0 --port 8000` works too — `main.py` at the repository root is a
one-line alias for `app.main:app`.

## 4. Sign in

| Email | Role | Password |
| --- | --- | --- |
| `cenius@cenius.ai` | Owner / maintainer (six seeded releases) | `cenius` |
| `demo@releasesmith.dev` | Maintainer (three seeded releases) | `demo1234` |

The sign-in card prints the primary credential and offers a one-click
**Sign in with the demo account** button.

## 5. Run the tests (optional)

```bash
python3 -m pytest
```

The tests use a throwaway SQLite file in a temporary directory; they do not touch
`releasesmith.db`.

## Configuration

Every setting has a working default, so `.env` is optional.

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | development fallback | Signs the session cookie. `install.sh` generates a random value into `.env` on first run. |
| `DATABASE_URL` | `sqlite:///./releasesmith.db` | SQLAlchemy URL. Use `postgresql+psycopg2://…` if you have Postgres and `psycopg2` installed. |
| `PORT` | `8000` | Only read by the documented `uvicorn … --port "${PORT:-8000}"` command. |

`.env.example` shows the shape. A blank value falls back to the built-in default.

## Troubleshooting

**`Address already in use`** — another process holds the port. Stop it, or start on another port:
`uvicorn app.main:app --host 0.0.0.0 --port 8001`.

**`ModuleNotFoundError: No module named 'app'`** — run the commands from the repository root (the
directory that contains `app/`), not from inside `app/`.

**The dashboard is empty after signing in** — run `python3 -m app.seed` and reload. If you created
your own account, it starts with no releases by design; pasting commits into `/composer` and saving
one fills it.

**`table users does not exist`** — the schema is created on boot and by the seed command; run
`python3 -m app.seed` once.

**Signed out immediately after signing in** — the session cookie is tied to `SECRET_KEY`. If you
change it, existing cookies stop working; sign in again.

**Reset everything** — stop the server, delete `releasesmith.db`, run `python3 -m app.seed`.
