# Using Releasesmith Changelog Generator

## Overview

This is **Releasesmith Changelog Generator** — an HTTP API + web UI. This document covers the surface area you can use, with copy-pasteable examples for each entry point. For setup, see `INSTALL.md`.

## Quickstart

After completing the install steps in `INSTALL.md`:

```bash
uvicorn app.main:app --reload    # start the server
# in another terminal:
curl http://localhost:8000/
```

## Endpoints

Every endpoint below was extracted from the source by the route scanner (Next.js / FastAPI / Flask / Django / Express).

| Method | Path | Source file |
|--------|------|-------------|
| `GET` | `/` | `app/main.py` |
| `GET` | `/composer` | `app/routers/composer.py` |
| `GET` | `/dashboard` | `app/routers/dashboard.py` |
| `GET` | `/health` | `app/main.py` |
| `GET` | `/healthz` | `app/main.py` |
| `GET` | `/login` | `app/routers/auth.py` |
| `GET` | `/releases/new` | `app/routers/composer.py` |
| `GET` | `/releases/{release_id}` | `app/routers/releases.py` |
| `GET` | `/releases/{release_id}/edit` | `app/routers/releases.py` |
| `GET` | `/releases/{release_id}/export.md` | `app/routers/releases.py` |
| `GET` | `/signin` | `app/routers/auth.py` |
| `GET` | `/signup` | `app/routers/auth.py` |
| `POST` | `/auth/demo-signin` | `app/routers/auth.py` |
| `POST` | `/auth/signin` | `app/routers/auth.py` |
| `POST` | `/auth/signout` | `app/routers/auth.py` |
| `POST` | `/auth/signup` | `app/routers/auth.py` |
| `POST` | `/composer/preview` | `app/routers/composer.py` |
| `POST` | `/releases` | `app/routers/releases.py` |
| `POST` | `/releases/{release_id}` | `app/routers/releases.py` |
| `POST` | `/releases/{release_id}/delete` | `app/routers/releases.py` |

### curl examples

#### `GET /`

```bash
curl http://localhost:8000/
```

#### `GET /composer`

```bash
curl http://localhost:8000/composer
```

#### `GET /dashboard`

```bash
curl http://localhost:8000/dashboard
```

#### `GET /health`

```bash
curl http://localhost:8000/health
```

#### `GET /healthz`

```bash
curl http://localhost:8000/healthz
```

## Worked example

1. Boot the server (`uvicorn app.main:app --reload`).
2. Hit a smoke-test endpoint:

```bash
curl -sS http://localhost:8000/
```

3. If you get a JSON / HTML response, the server is healthy. Inspect `.env` if it errors with an auth/config failure.

## Reference

### Entry points

_No explicit entry points declared in this project's manifests._

### Surface index (auto-extracted)

| Kind | Title | Source file |
|------|-------|-------------|
| route | `GET /` | `app/main.py` |
| route | `GET /composer` | `app/routers/composer.py` |
| route | `GET /dashboard` | `app/routers/dashboard.py` |
| route | `GET /health` | `app/main.py` |
| route | `GET /healthz` | `app/main.py` |
| route | `GET /login` | `app/routers/auth.py` |
| route | `GET /releases/new` | `app/routers/composer.py` |
| route | `GET /releases/{release_id}` | `app/routers/releases.py` |
| route | `GET /releases/{release_id}/edit` | `app/routers/releases.py` |
| route | `GET /releases/{release_id}/export.md` | `app/routers/releases.py` |
| route | `GET /signin` | `app/routers/auth.py` |
| route | `GET /signup` | `app/routers/auth.py` |
| route | `POST /auth/demo-signin` | `app/routers/auth.py` |
| route | `POST /auth/signin` | `app/routers/auth.py` |
| route | `POST /auth/signout` | `app/routers/auth.py` |
| route | `POST /auth/signup` | `app/routers/auth.py` |
| route | `POST /composer/preview` | `app/routers/composer.py` |
| route | `POST /releases` | `app/routers/releases.py` |
| route | `POST /releases/{release_id}` | `app/routers/releases.py` |
| route | `POST /releases/{release_id}/delete` | `app/routers/releases.py` |

## Next steps

- Read [INSTALL.md](./INSTALL.md) if anything in the Quickstart didn't work.
- Inspect `.env.example` for the full list of environment variables this project understands.
- See [README.md](./README.md) for the architecture diagram + feature list.
