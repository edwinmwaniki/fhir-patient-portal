"""WSGI config for fhir_portal."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhir_portal.settings')

application = get_wsgi_application()
