"""Business logic for `Patient` FHIR resources.

The service is the sole writer to the `Patient` model. Views and signal
handlers call into it rather than mutating the ORM directly, so the
denormalization rules for indexed columns live in exactly one place.
"""
import logging
import uuid
from datetime import date, datetime

from app.models.patient_model import Patient

logger = logging.getLogger(__name__)


class PatientService:

    @classmethod
    def create(cls, resource):
        # `resource` is the validated FHIR JSON dict returned by the
        # serializer. Generate a stable logical id if the client didn't
        # supply one, then persist alongside the denormalized columns.
        fhir_id = resource.get('id') or uuid.uuid4().hex
        resource = {**resource, 'id': fhir_id}

        family, given = cls._extract_name(resource)

        patient = Patient.objects.create(
            fhir_id=fhir_id,
            active=bool(resource.get('active', True)),
            gender=resource.get('gender') or '',
            birth_date=cls._parse_date(resource.get('birthDate')),
            family_name=family,
            given_name=given,
            resource=resource,
        )
        logger.info('Created Patient %s', patient.fhir_id)
        return patient

    @classmethod
    def update(cls, patient, resource):
        # Preserve the existing logical id; FHIR update semantics forbid the
        # client from changing it on PUT.
        resource = {**resource, 'id': patient.fhir_id}

        family, given = cls._extract_name(resource)

        patient.active = bool(resource.get('active', True))
        patient.gender = resource.get('gender') or ''
        patient.birth_date = cls._parse_date(resource.get('birthDate'))
        patient.family_name = family
        patient.given_name = given
        patient.resource = resource
        patient.save()
        logger.info('Updated Patient %s', patient.fhir_id)
        return patient

    @staticmethod
    def _extract_name(resource):
        # FHIR HumanName is an array; convention is to denormalize from the
        # first entry with a `use` of 'official' if present, else the first.
        names = resource.get('name') or []
        if not names:
            return '', ''
        preferred = next(
            (n for n in names if n.get('use') == 'official'), names[0])
        family = preferred.get('family') or ''
        given_parts = preferred.get('given') or []
        given = ' '.join(part for part in given_parts if part)
        return family, given

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            # fhir.resources should have already rejected malformed dates;
            # bail out silently rather than crashing on the denorm write.
            return None
