"""DRF serializer for FHIR R4 Patient resources.

Payload validation is delegated to the `fhir.resources` pydantic models so
we get the full R4 schema (element cardinality, code system membership,
data-type coercion) enforced for free. The serializer's job is to translate
between DRF's error contract and pydantic's, and to hand a normalised dict
off to the service layer.
"""
import json

from fhir.resources.R4B.patient import Patient as FHIRPatient
# fhir.resources 7.x rides the pydantic v1 compat shim; import
# ValidationError from the same location it will be raised from.
from pydantic.v1 import ValidationError as PydanticValidationError
from rest_framework import serializers

from app.models.patient_model import Patient


class PatientSerializer(serializers.Serializer):
    # We serialize the entire FHIR resource as a single opaque JSON blob;
    # per-field DRF validation would duplicate what fhir.resources already
    # does and inevitably drift from the spec.

    def to_internal_value(self, data):
        # DRF hands us either a dict (JSONParser) or a raw value; anything
        # non-dict cannot be a valid FHIR resource.
        if not isinstance(data, dict):
            raise serializers.ValidationError({
                'non_field_errors': ['FHIR resource must be a JSON object.'],
            })

        resource_type = data.get('resourceType')
        if resource_type != 'Patient':
            raise serializers.ValidationError({
                'resourceType': [
                    "Expected resourceType 'Patient', "
                    f"got {resource_type!r}."
                ],
            })

        try:
            validated = FHIRPatient.parse_obj(data)
        except PydanticValidationError as exc:
            # Surface pydantic's structured errors to the client in a shape
            # DRF's exception handler will render cleanly.
            raise serializers.ValidationError(_format_pydantic_errors(exc))

        # `.json()` -> `json.loads(...)` guarantees the persisted payload is
        # composed of JSON-safe primitives (dates as strings, etc.) and
        # round-trips cleanly through JSONField.
        return json.loads(validated.json(exclude_none=True, by_alias=True))

    def to_representation(self, instance):
        # Read path: the model already stores canonical FHIR JSON.
        if isinstance(instance, Patient):
            return instance.resource
        return instance


def _format_pydantic_errors(exc):
    # Convert pydantic's list-of-dicts error format into DRF's dict-of-lists
    # so /api/fhir/v1/Patient/ returns 400 responses that clients can parse.
    # pydantic v1 prefixes locations for root validators with the synthetic
    # '__root__' segment; strip it so consumers see real FHIR field paths.
    errors = {}
    for err in exc.errors():
        loc_parts = [str(part) for part in err.get('loc', ())
                     if str(part) != '__root__']
        location = '.'.join(loc_parts) or 'non_field_errors'
        errors.setdefault(location, []).append(err.get('msg', 'Invalid value.'))
    return errors
