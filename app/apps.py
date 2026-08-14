from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    verbose_name = 'FHIR Patient Portal'

    def ready(self):
        # Signal handlers will be wired here in later tasks; keeping the
        # hook in place now so newer modules can register cleanly.
        return None
