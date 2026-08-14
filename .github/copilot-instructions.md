# General Constraints
- You are a mid-level Full-Stack Engineer writing enterprise-grade, production-ready code.
- Prioritize modularity, clear separation of concerns, and security.
- Never use "magic numbers" or hardcoded credentials; always use environment variables.

## Architecture

- `app/models/` — one file per domain model (e.g. `appointment_model.py`), imported individually (`from app.models.staff_model import Staff`), not via a package-level `models` re-export.
- `app/services/` — business logic lives in `*Service` classes. Views and signals call into services rather than querying models directly.
- `app/views/` — DRF generic views, one file per domain, importing serializers from `app/serializers/` and services from `app/services/`.
- `app/signals/` — one file per model's signal handlers, wired up in `app/apps.py`/`AppConfig.ready()`.
- Polymorphic relations (e.g. `Appointment.client` can be a `Patient` or `Lead`) use Django's `GenericForeignKey` with paired `client_type` (`ContentType`) / `client_id` (`UUIDField`) columns — follow this pattern for new polymorphic fields, and use `GenericPrefetch`/`Prefetch` in `get_queryset` to avoid N+1s.
- Model choice fields are defined as UPPER_CASE list-of-tuples class attributes inside the model (see `Appointment.APPOINTMENT_STATUS`), not as separate enums.

## Code Style

- 4-space indentation; long calls wrap with hanging indents inside parens (autopep8 style), e.g.:
  ```python
  appointments = Appointment.objects.filter(
      status='booked', start_time__lt=timezone.now())
  ```
- Comments explain *why*, placed above the line/block they describe, in plain sentences — not docstrings for simple methods.
- Timestamps: always use `django.utils.timezone` (`timezone.now()`, `timezone.make_aware()`), never naive `datetime.now()`/`datetime.utcnow()`. Note `django.utils.timezone` has no `.utc` — use `datetime.timezone.utc` when explicit tzinfo is needed.
- Logging: services with external calls or background jobs (`services/smart.py`, `services/notifications.py`, `services/waha.py`, `signals/`) use `logger = logging.getLogger(__name__)` at module scope. Management commands, Celery tasks (`app/tasks.py`) and older signal handlers use `print(...)` for status/progress messages — match whichever pattern the surrounding file already uses.

## Testing

- Test runner is pytest (`pytest-django`, see [pytest.ini](../pytest.ini)), but tests are written as `django.test`/`rest_framework.test.APITestCase` classes with `setUp`/`test_*` methods, not bare pytest functions.
- Tests live under `app/tests/<feature>/test_*.py`, mirroring the domain grouping used in `app/views/` and `app/services/`.
- [conftest.py](../conftest.py) auto-disables outbound WAHA/WhatsApp calls and background dispatch threads for every test — don't re-mock `WAHA_URL` unless a test needs it enabled.
- Run tests with `pytest` or `python manage.py test`; only `pytest` picks up `conftest.py`.

## Build and Run

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver          # Django
```
