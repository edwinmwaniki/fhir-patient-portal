"""Business logic for `Appointment` FHIR resources."""
import logging
import uuid
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

from app.models.appointment_model import Appointment
from app.models.patient_model import Patient

logger = logging.getLogger(__name__)


class AppointmentService:

    @classmethod
    def create(cls, resource):
        fhir_id = resource.get('id') or uuid.uuid4().hex
        resource = {**resource, 'id': fhir_id}

        patient = cls._resolve_patient(resource)

        appointment = Appointment.objects.create(
            fhir_id=fhir_id,
            status=resource.get('status', ''),
            start=cls._parse_datetime(resource.get('start')),
            end=cls._parse_datetime(resource.get('end')),
            description=resource.get('description') or '',
            patient=patient,
            resource=resource,
        )
        logger.info('Created Appointment %s', appointment.fhir_id)
        return appointment

    @classmethod
    def update(cls, appointment, resource):
        resource = {**resource, 'id': appointment.fhir_id}

        appointment.status = resource.get('status', '')
        appointment.start = cls._parse_datetime(resource.get('start'))
        appointment.end = cls._parse_datetime(resource.get('end'))
        appointment.description = resource.get('description') or ''
        appointment.patient = cls._resolve_patient(resource)
        appointment.resource = resource
        appointment.save()
        logger.info('Updated Appointment %s', appointment.fhir_id)
        return appointment

    @staticmethod
    def _resolve_patient(resource):
        # FHIR Appointment.participant[].actor.reference is a string of the
        # form "Patient/<id>". We pick the first patient participant and
        # attempt to link it to a locally-known Patient row. If the row does
        # not exist (external reference) the FK stays null and the full
        # reference remains queryable in the JSON payload.
        for participant in resource.get('participant') or []:
            actor = participant.get('actor') or {}
            reference = actor.get('reference') or ''
            if not reference.startswith('Patient/'):
                continue
            fhir_id = reference.split('/', 1)[1]
            return Patient.objects.filter(fhir_id=fhir_id).first()
        return None

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            except ValueError:
                return None
        # Ensure aware datetimes for USE_TZ=True; assume UTC if naive.
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone=dt_timezone.utc)
        return parsed
