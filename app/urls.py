"""URL routing for the FHIR REST API.

Mounted at `/api/fhir/v1/` by the project urlconf. Resource names match the
FHIR REST convention (`Patient`, `Appointment`) rather than DRF's default
lowercase style.
"""
from rest_framework.routers import DefaultRouter

from app.views.appointment_view import AppointmentViewSet
from app.views.patient_view import PatientViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r'Patient', PatientViewSet, basename='patient')
router.register(r'Appointment', AppointmentViewSet, basename='appointment')

urlpatterns = router.urls
