# FHIR Patient Portal

An open-source, enterprise-shaped **FHIR R4 Patient Portal** built with Django REST Framework, PostgreSQL, Angular, and Nginx, packaged for local reproducibility with Docker Compose and gated by GitHub Actions CI.

The goal is not to be a complete EHR — it's a compact, honest reference for **how to structure** a FHIR-first web application: strict schema validation, canonical JSON as the source of truth, denormalized columns for search, thin views over a service layer, and a reverse-proxied SPA front-end.

---

## Table of contents

- [Architecture](#architecture)
- [Design choices](#design-choices)
- [Project layout](#project-layout)
- [Quick start with Docker Compose](#quick-start-with-docker-compose)
- [Development workflow](#development-workflow)
- [API surface](#api-surface)
- [Testing](#testing)
- [CI/CD pipeline](#cicd-pipeline)
- [Environment variables](#environment-variables)
- [Operational notes](#operational-notes)

---

## Architecture

```
                                 ┌──────────────────────────────┐
                                 │           Browser            │
                                 └──────────────┬───────────────┘
                                                │  http :80
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              nginx (reverse proxy)                          │
│  · /            → Angular SPA (frontend/dist/browser)                       │
│  · /static/     → Django collected static (shared named volume)             │
│  · /api/, /admin/, /healthz → upstream django_upstream (keepalive)          │
│  · rate-limit zone on /api/, X-Forwarded-* headers, server_tokens off       │
└──────────────┬──────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐          ┌───────────────────────────────┐
│   web (Django + Gunicorn)    │          │      db (PostgreSQL 16)       │
│  · fhir_portal (settings)    │◀────────▶│   volume: postgres_data       │
│  · app/ (Patient, Appt)      │          │   healthcheck: pg_isready     │
│  · drf-spectacular schema    │          └───────────────────────────────┘
│  · gunicorn 3 workers        │
└──────────────────────────────┘
```

Three services, one shared network:

| Service | Image | Role |
| ------- | ----- | ---- |
| `db`    | `postgres:16-alpine` | Canonical data store; port not exposed to host. |
| `web`   | `python:3.11-slim` (custom) | Django + DRF + Gunicorn behind a non-root user. |
| `nginx` | `nginx:1.27-alpine` | Only host-exposed ingress; serves SPA + static, proxies API. |

---

## Design choices

### FHIR-native domain model

- Every resource stores the **entire canonical FHIR JSON payload** in a `JSONField` named `resource`. This is the source of truth: nothing is lost on round-trip, and a client that POSTs a valid FHIR document gets back a byte-equivalent representation.
- A small set of **denormalized columns** (e.g. `Patient.family_name`, `Appointment.status`, `Appointment.start`) are extracted from the payload so search and indexing don't require JSONB traversal.
- Choice sets on those columns are declared as **UPPER_CASE `list-of-tuples` class attributes** on the model (see `Appointment.APPOINTMENT_STATUS`), matching the project convention.

### Strict schema validation via `fhir.resources`

- DRF serializers delegate validation to the [`fhir.resources`](https://pypi.org/project/fhir.resources/) pydantic models (R4B). Element cardinality, primitive types, and structure are enforced for free.
- Pydantic errors are translated into DRF's `{field: [messages]}` shape; the synthetic `__root__` prefix pydantic v1 emits for root validators is stripped so clients see real FHIR paths (`{"status": [...]}`, not `{"__root__.status": [...]}`).
- **Note**: `fhir.resources` 7.x rides pydantic's v1 compatibility shim even when pydantic v2 is installed — use `.parse_obj()` / `.json()` / `pydantic.v1.ValidationError`, **not** `.model_validate()` / `.model_dump()`.

### Layered application structure

Following the project's [copilot-instructions.md](.github/copilot-instructions.md) conventions:

- **`app/models/<domain>_model.py`** — one file per model, imported individually (no package-level re-exports).
- **`app/serializers/<domain>_serializer.py`** — one per domain, thin wrappers over `fhir.resources`.
- **`app/services/<domain>_service.py`** — `*Service` classes own writes and encapsulate denormalization/FK resolution. Views never touch the ORM directly.
- **`app/views/<domain>_view.py`** — DRF ViewSets, look up by FHIR `logical id` (`lookup_field = 'fhir_id'`), URLs use FHIR-style capitalized segments (`/Patient/`, `/Appointment/`).
- **`app/tests/<domain>/test_*.py`** — mirrors the domain grouping; tests written as `APITestCase` classes with `setUp` / `test_*`, run under `pytest-django`.

### FHIR REST conventions on the wire

- URL segments capitalized (`/Patient/`, `/Appointment/`) — matches HL7 FHIR REST convention rather than DRF's default lowercase.
- Resource lookup by **FHIR logical id**, not the surrogate UUID PK, so URLs are stable and human-readable.
- List endpoints return a **`Bundle` of type `searchset`** rather than a bare array.
- Polymorphic references (e.g. `Appointment.participant.actor`) resolve to a local FK when the target exists; unresolved external references leave the FK null and preserve the reference verbatim in JSON.

### Security posture

- **No hardcoded secrets or "magic numbers".** All configuration flows through environment variables; required keys fail loudly at boot (`_env(..., required=True)`).
- **Non-root container user** (`django`, uid 1000). The runtime image pre-creates `/app/staticfiles` and `/app/media` with the right ownership so mounted named volumes inherit uid 1000 instead of coming up root-owned.
- **Hardened non-DEBUG defaults**: `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS, `X_FRAME_OPTIONS = 'DENY'`, `SECURE_CONTENT_TYPE_NOSNIFF`.
- **Nginx** publishes only port 80 on the host; `web:8000` and `db:5432` stay on the internal Docker network. `server_tokens off`, `X-Forwarded-*` headers forwarded, `client_max_body_size 5m`, `limit_req_zone` on `/api/`.
- **Multi-stage Dockerfile** — `build-essential` / `libpq-dev` live only in the builder stage; the runtime image ships just `libpq5` + `curl`.

### Frontend as a static SPA

- **Angular 19 standalone** — no NgModules; providers and routes live in `app.config.ts` so the composition root is discoverable in one file.
- The SPA calls the API via a **relative** `/api/fhir/v1/` base URL, which "just works" behind Nginx (same origin) and via the `ng serve` dev-server proxy (`proxy.conf.json`).
- Angular's `application` builder emits to `frontend/dist/browser/` — that's the directory Nginx mounts at its web root. A checked-in `frontend/placeholder/index.html` gives Nginx something to serve before the first build.

### Interactive API docs

- `drf-spectacular` generates the OpenAPI 3 schema and exposes it under `/api/`, so the existing Nginx proxy covers it for free:
  - `GET /api/schema/` — OpenAPI 3 (YAML by default, `?format=json` for JSON)
  - `GET /api/docs/` — Swagger UI, with `OpenApiExample` bodies pre-populated so "Try it out" ships a valid FHIR payload.
  - `GET /api/redoc/` — Redoc.

---

## Project layout

```
.
├── app/
│   ├── apps.py
│   ├── migrations/
│   ├── models/
│   │   ├── appointment_model.py
│   │   └── patient_model.py
│   ├── serializers/
│   │   ├── appointment_serializer.py
│   │   └── patient_serializer.py
│   ├── services/
│   │   ├── appointment_service.py
│   │   └── patient_service.py
│   ├── tests/
│   │   ├── appointment/test_appointment_api.py
│   │   └── patient/test_patient_api.py
│   ├── urls.py
│   └── views/
│       ├── appointment_view.py
│       └── patient_view.py
├── fhir_portal/            # Django project (settings, root urls, wsgi/asgi)
├── frontend/               # Angular 19 standalone SPA
│   ├── src/app/
│   │   ├── models/fhir.ts
│   │   ├── pages/
│   │   ├── services/fhir.service.ts
│   │   ├── app.component.ts
│   │   ├── app.config.ts
│   │   └── app.routes.ts
│   ├── angular.json
│   ├── package.json
│   ├── placeholder/index.html
│   └── proxy.conf.json
├── nginx/nginx.conf
├── .github/workflows/ci.yml
├── conftest.py             # synthetic FHIR payload fixtures + outbound-call safety net
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile              # multi-stage, non-root
└── docker-compose.yml
```

---

## Quick start with Docker Compose

### Prerequisites

- Docker Engine ≥ 24 with the Compose plugin (`docker compose …`).
- Node.js 20+ and npm if you want to build the Angular SPA locally.

### 1. Configure environment

```bash
cp .env.example .env
# edit .env if you need to change ports or credentials
```

The stack refuses to boot in non-DEBUG mode if `DJANGO_SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, or `POSTGRES_PASSWORD` are unset.

### 2. Bring the stack up

```bash
docker compose up --build
```

This starts three containers:

- `db` — Postgres 16 with a `pg_isready` healthcheck; `web` waits on it before running migrations.
- `web` — runs `migrate → collectstatic → gunicorn` on start (3 workers, access + error logs to stdout).
- `nginx` — publishes `${NGINX_HOST_PORT:-80}:80`; the only container reachable from the host by default.

Once healthy:

| URL | What it serves |
| --- | -------------- |
| http://localhost/            | Angular SPA (or the placeholder page pre-`npm run build`) |
| http://localhost/api/fhir/v1/Patient/ | FHIR Patient CRUD |
| http://localhost/api/fhir/v1/Appointment/ | FHIR Appointment CRUD |
| http://localhost/api/docs/   | Swagger UI |
| http://localhost/api/redoc/  | Redoc |
| http://localhost/api/schema/ | OpenAPI 3 schema |
| http://localhost/admin/      | Django admin |
| http://localhost/healthz     | Liveness probe (`{"status":"ok"}`) |

### 3. Build the SPA (optional but recommended)

```bash
cd frontend
npm install
npm run build
```

Angular's `application` builder writes to `frontend/dist/browser/` — the exact directory the `nginx` service mounts. Refresh the browser and the real dashboard replaces the placeholder.

### 4. Stop / clean up

```bash
docker compose down            # keep volumes
docker compose down -v         # nuke db + static volumes too
```

### One-off commands inside the web container

```bash
docker compose run --rm --no-deps web python manage.py createsuperuser
docker compose run --rm --no-deps web python manage.py shell
docker compose run --rm web python manage.py makemigrations
```

`--no-deps` avoids spinning up `db` for commands that don't need it.

---

## Development workflow

### Backend hot-reload

The `web` service bind-mounts the repo at `/app`, so Python edits land inside the container immediately. Gunicorn is not auto-reloading, so after changing Python code either:

```bash
docker compose restart web
```

or drop the `--workers` flag and add `--reload` in `docker-compose.yml` for iterative work.

### Frontend hot-reload

The Angular dev-server proxies API calls straight to Django:

```bash
cd frontend
npm start          # ng serve, proxied via proxy.conf.json
```

Then open http://localhost:4200/. The proxy config forwards `/api`, `/admin`, `/healthz` to `http://localhost:8000` — make sure `web` is up and, for host-side access, un-comment its `ports:` block in `docker-compose.yml`.

### Native (non-Docker) backend

If you prefer running Django on the host directly:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
```

You still need a Postgres instance reachable at the credentials in `.env`.

---

## API surface

All FHIR endpoints live under `/api/fhir/v1/`. Each resource follows FHIR REST conventions:

| Method | Path | Behaviour |
| ------ | ---- | --------- |
| `GET`    | `/Patient/`                 | Search — returns `Bundle{type:searchset}` (`_count`, `_offset` query params) |
| `POST`   | `/Patient/`                 | Create — full FHIR validation via pydantic |
| `GET`    | `/Patient/{fhir_id}/`       | Read |
| `PUT`    | `/Patient/{fhir_id}/`       | Update (replace) |
| `PATCH`  | `/Patient/{fhir_id}/`       | Merge patch (server merges body onto the stored resource, re-validates) |
| `DELETE` | `/Patient/{fhir_id}/`       | Delete |

Same shape for `/Appointment/`. The interactive Swagger UI (`/api/docs/`) is the canonical, always-in-sync reference — invalid FHIR payloads return `400` with a structured `{field: [messages]}` body.

Example valid Patient payload:

```json
{
  "resourceType": "Patient",
  "id": "example-1",
  "active": true,
  "name": [{"use": "official", "family": "Doe", "given": ["Jane"]}],
  "gender": "female",
  "birthDate": "1985-04-12"
}
```

---

## Testing

24 tests covering the happy path plus every schema-rejection branch for both resources.

```bash
# Locally (venv, host Postgres available):
pip install -r requirements-dev.txt
pytest -v

# Or fully inside Docker without touching your host:
docker compose up -d db
docker compose run --rm -e POSTGRES_HOST=db web \
    sh -c "pip install --quiet pytest pytest-django && python -m pytest -v"
```

Layout & conventions:

- `pytest-django` is wired through `pytest.ini` (`DJANGO_SETTINGS_MODULE = fhir_portal.settings`).
- Tests are `APITestCase` classes with `setUp` + `test_*` methods, grouped under `app/tests/<domain>/` mirroring `app/views/`.
- `conftest.py` provides synthetic FHIR payload fixtures (`patient_payload`, `appointment_payload`, `appointment_payload_for`) plus an autouse `_disable_external_calls` fixture — a hook point for mocking outbound HTTP once integrations land.

---

## CI/CD pipeline

Defined in [.github/workflows/ci.yml](.github/workflows/ci.yml). One job, gated by a Postgres 16 service container so the tests run against the same engine as production.

### Triggers

- `push` to `main`
- `pull_request` targeting `main`
- `concurrency` group cancels stale runs of the same ref, so PR force-pushes don't burn minutes.

### Job: `test`

Runs on `ubuntu-latest` under a 15-minute cap. Steps:

1. **Checkout** — `actions/checkout@v4`.
2. **Set up Python 3.11** — `actions/setup-python@v5` with pip cache keyed on both `requirements.txt` and `requirements-dev.txt`.
3. **Install dependencies** — `pip install -r requirements-dev.txt`.
4. **Django system check** — `python manage.py check`. Fails on any Django config error.
5. **Migration drift check** — `python manage.py makemigrations --check --dry-run`. Fails the job if a model change was committed without a paired migration, keeping schema drift out of `main`.
6. **Run pytest** — `pytest --maxfail=1`.

### Services

A Postgres 16 service container comes up alongside the job with a `pg_isready` health check on its `options`, so pytest never races the DB.

### How merges are blocked

The workflow **fails on any non-zero exit** in the steps above; that's the mechanical half. To make it actually block merges into `main`, add a branch protection rule on the repo:

- Settings → Branches → Add rule for `main`
- Require status checks to pass before merging → select `pytest (Python 3.11 + Postgres 16)` (this job's name).
- Optional: require branches to be up to date, require conversation resolution, require linear history.

The workflow's job name is stable, so once selected it stays selected across future runs.

### Extending the pipeline

Sensible next additions when the codebase grows:

- **Frontend job** — `actions/setup-node@v4` + `npm ci && npm run build` on `frontend/`.
- **Static analysis** — `ruff check` and `mypy` on the Python side, `ng lint` on the SPA.
- **Container image build/push** — `docker/build-push-action@v6` on `main` merges only, tagged with the commit SHA.
- **Coverage gate** — `pytest --cov=app --cov-fail-under=85`.

---

## Environment variables

Sourced from `.env` locally, from GitHub Actions env in CI, and from the orchestrator's secret store in production. All are read in [fhir_portal/settings.py](fhir_portal/settings.py).

| Key | Default | Description |
| --- | ------- | ----------- |
| `DJANGO_DEBUG`         | `false` | Enable debug tracebacks & lax defaults. Never `true` in production. |
| `DJANGO_SECRET_KEY`    | *required outside DEBUG* | Django cryptographic signing key. Long random string. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` (DEBUG only) | Comma-separated Host header allow-list. |
| `DJANGO_TIME_ZONE`     | `UTC` | Server timezone. `USE_TZ=True` regardless. |
| `DJANGO_LOG_LEVEL`     | `INFO` | Root logger level. |
| `DJANGO_HSTS_SECONDS`  | `3600` | HSTS max-age when `DEBUG=false`. |
| `POSTGRES_DB`          | *required* | Database name. |
| `POSTGRES_USER`        | *required* | Database user. |
| `POSTGRES_PASSWORD`    | *required* | Database password. |
| `POSTGRES_HOST`        | `db` | Hostname (Docker service name inside the network). |
| `POSTGRES_PORT`        | `5432` | Database port. |
| `POSTGRES_CONN_MAX_AGE`| `60` | Persistent connection lifetime (seconds). |
| `WEB_HOST_PORT`        | `8000` | Only used if you re-enable the `ports:` block on the `web` service for direct host access. |
| `NGINX_HOST_PORT`      | `80` | Host port Nginx binds. Set to e.g. `8080` if port 80 is taken. |

---

## Operational notes

### Static & media volumes

`web` writes Django's collected static assets to a **named volume** (`static_data`) that `nginx` mounts read-only at `/app/staticfiles`. This is why the runtime image pre-creates the directory with `django:django` ownership — a fresh named volume inherits the ownership of the seed directory, otherwise it comes up root-owned and `collectstatic` fails with `PermissionError`.

### Ingress topology

Only `nginx` publishes a host port. `web:8000` is on `expose` (internal Docker network only); `db:5432` isn't even exposed. If you need host-side debugging access to Gunicorn or Postgres, temporarily add a `ports:` block in `docker-compose.yml` — the config already has commented placeholders showing where.

### Angular build path gotcha

Angular's `@angular-devkit/build-angular:application` builder always emits into a `browser/` subdirectory of `outputPath`. Nginx therefore mounts `./frontend/dist/browser`, not `./frontend/dist`. Mounting the wrong one causes a `403` because Nginx sees no `index.html` at the mount root.

### Production checklist

Before shipping anywhere non-local, at minimum:

- Set `DJANGO_DEBUG=false` and issue a real `DJANGO_SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(64))"`).
- Populate `DJANGO_ALLOWED_HOSTS` with the real hostnames.
- Terminate TLS in front of Nginx (or add a `server` block with certs and a 443 listener).
- Swap `psycopg2-binary` for `psycopg2` compiled against your target libpq, or accept the binary wheel trade-off.
- Remove the bind-mount `volumes: - .:/app` from the `web` service so the container ships an immutable image.
- Layer real auth on top — the demo runs `DEFAULT_PERMISSION_CLASSES = AllowAny`.
- Move secrets out of `.env` into a secret store (SOPS, Vault, AWS SM, k8s secrets, etc.).

---

## License

MIT — see [LICENSE](LICENSE) if present, otherwise treat this repo as an unencumbered reference implementation.
