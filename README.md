# Music Platform

## Project layout

### Frontend

Canonical UI code lives under `feishin/src/renderer`.

```text
feishin/src/renderer/
  features/consumer/
    components/   # reusable UI building blocks
    constants/    # static nav and screen metadata
    layout/       # app shell and shared layout styling
    screens/      # route-level consumer screens
```

### Backend

Canonical API code lives under `backend/app`.

```text
backend/
  app/
    api/routers/  # FastAPI route modules
    core/         # static config and catalogs
    services/     # business logic
    seeding/      # mock data fixtures and seed runner
    db.py         # SQLAlchemy engine/session setup
    models.py     # ORM models
    schemas.py    # Pydantic schemas
    main.py       # FastAPI app factory/registration
```

`backend/main.py` and `backend/seed.py` are compatibility entrypoints for Docker and local scripts.

Backend quality tooling lives in:

- `backend/pyproject.toml`: `black`, `ruff`, `mypy`, and `pytest` config
- `backend/requirements-dev.txt`: backend-only dev tools
- `backend/tests/`: backend test structure

### Infra and local data

- `docker-compose.yml`: local services
- `music/`: music library mounted into Navidrome
- `navidrome-data/`: Navidrome local state
- `postgres-data/`: Postgres local state

## Run locally

Start backend services:

```powershell
cd c:\Users\u\Music\music-platform
docker compose up -d
```

Start the frontend:

```powershell
cd c:\Users\u\Music\music-platform\feishin
npx vite dev --config web.vite.config.ts --host 0.0.0.0 --port 5173
```

## Quality checks

Frontend:

```powershell
cd c:\Users\u\Music\music-platform\feishin
npx eslint src
npx tsc --noEmit -p tsconfig.node.json --composite false
npx tsc --noEmit -p tsconfig.web.json --composite false
npx prettier --check .
```

Backend:

```powershell
cd c:\Users\u\Music\music-platform\backend
python -m py_compile main.py seed.py
python -m pytest
ruff check .
black --check .
mypy .
```
