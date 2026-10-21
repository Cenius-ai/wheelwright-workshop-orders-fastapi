# Installation

Wheelwright Workshop Orders is a single Python service. There is no frontend build step and no
external service to provision: the database is a SQLite file created on first boot.

## Prerequisites (installed on the machine, not by this project)

- Python 3.11 or newer with `pip` (`python3 --version`)
- A POSIX shell (the scripts are `sh`/`bash` compatible)

No system packages, database servers, compilers or network services are required beyond the
Python interpreter. The dependencies are pure-Python wheels.

## 1. Install, create the schema and load demo data

```bash
sh install.sh
```

This single step:

1. upgrades the local pip tooling,
2. installs `requirements.txt` with pip,
3. writes a `.env` containing a generated `SESSION_SECRET` (skipped if `.env` exists),
4. creates the SQLite schema,
5. seeds the demo workshop (staff accounts, heritage clients, cartwheel builds, iron tyre
   fittings),
6. imports the application once to prove the install is complete — then exits.

It never starts the server, and it is safe to run again.

## 2. Seed the demo data (separate step, also run by install.sh)

```bash
python3 -m app.seed          # or: python3 -m seed
```

The seed is idempotent: it checks before inserting, so re-running it never duplicates staff,
clients or builds. Fittings are demo content only — once the schedule holds any booking the seed
leaves it alone, so a re-run never disturbs real work. The command exits; it never binds the HTTP
port.

## 3. Run in development

```bash
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Other equivalent start commands:

```bash
python3 main.py                                             # binds 0.0.0.0:${PORT:-8000}
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"      # root ASGI entrypoint
```

Open <http://localhost:8000> and sign in with the demo account:

| Email | Role | Password |
| --- | --- | --- |
| cenius@cenius.ai | admin | cenius |

The schema is created and the demo data seeded on the normal boot path too, so a fresh clone
starts straight into a populated workshop with no `.env` present.

## 4. Run the tests

```bash
python3 -m pytest -q
```

The suite uses its own throwaway SQLite file (`tests/wheelwright_test.db`) and needs no network,
no services and no manual fixtures.

## Deploying

- Put the app behind HTTPS and set `COOKIE_SECURE=true` so the session cookie is only sent over
  TLS.
- Set `SESSION_SECRET` to a long random value (install.sh generates one into `.env`).
- Point `DATABASE_URL` at a persistent path if you want the SQLite file outside the project
  directory.
- Remove the demo staff accounts before going live.
