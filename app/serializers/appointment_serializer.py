"""DRF serializer for FHIR R4 Appointment resources."""
import json

from fhir.resources.R4B.appointment import Appointment as FHIRAppointment
# fhir.resources 7.x rides the pydantic v1 compat shim; import
# ValidationError from the same location it will be raised from.
from pydantic.v1 import ValidationError as PydanticValidationError
from rest_framework import serializers

from app.models.appointment_model import Appointment


class AppointmentSerializer(serializers.Serializer):

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({
                'non_field_errors': ['FHIR resource must be a JSON object.'],
            })

        resource_type = data.get('resourceType')
        if resource_type != 'Appointment':
            raise serializers.ValidationError({
                'resourceType': [
                    "Expected resourceType 'Appointment', "
                    f"got {resource_type!r}."
                ],
            })

        try:
            validated = FHIRAppointment.parse_obj(data)
        except PydanticValidationError as exc:
            raise serializers.ValidationError(_format_pydantic_errors(exc))

        return json.loads(validated.json(exclude_none=True, by_alias=True))

    def to_representation(self, instance):
        if isinstance(instance, Appointment):
            return instance.resource
        return instance


def _format_pydantic_errors(exc):
    # See PatientSerializer._format_pydantic_errors for rationale; kept
    # duplicated (rather than shared) because each serializer owns its own
    # translation contract.
    errors = {}
    for err in exc.errors():
        loc_parts = [str(part) for part in err.get('loc', ())
                     if str(part) != '__root__']
        location = '.'.join(loc_parts) or 'non_field_errors'
        errors.setdefault(location, []).append(err.get('msg', 'Invalid value.'))
    return errors
