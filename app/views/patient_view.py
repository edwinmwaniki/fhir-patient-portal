"""FHIR R4 Patient ViewSet.

Standard REST CRUD mapped to FHIR-style URLs (`/Patient/<fhir_id>/`). The
viewset stays thin: validation lives in the serializer, persistence lives
in `PatientService`.
"""
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.response import Response

from app.models.patient_model import Patient
from app.serializers.patient_serializer import PatientSerializer
from app.services.patient_service import PatientService


# Reusable example so Swagger UI's "Try it out" button ships with a payload
# a client can POST unchanged.
_PATIENT_EXAMPLE = OpenApiExample(
    name='Minimal FHIR R4 Patient',
    value={
        'resourceType': 'Patient',
        'id': 'example-1',
        'active': True,
        'name': [
            {'use': 'official', 'family': 'Doe', 'given': ['Jane']},
        ],
        'gender': 'female',
        'birthDate': '1985-04-12',
    },
    request_only=False,
    response_only=False,
)


@extend_schema_view(
    list=extend_schema(
        tags=['Patient'],
        summary='Search Patients',
        description='Returns a FHIR `Bundle` (`type: searchset`) of Patients.',
        responses={200: OpenApiTypes.OBJECT},
    ),
    retrieve=extend_schema(
        tags=['Patient'],
        summary='Read Patient by id',
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    ),
    create=extend_schema(
        tags=['Patient'],
        summary='Create Patient',
        request=OpenApiTypes.OBJECT,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
        examples=[_PATIENT_EXAMPLE],
    ),
    update=extend_schema(
        tags=['Patient'],
        summary='Update Patient (PUT)',
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
        examples=[_PATIENT_EXAMPLE],
    ),
    partial_update=extend_schema(
        tags=['Patient'],
        summary='Patch Patient (merge)',
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    ),
    destroy=extend_schema(
        tags=['Patient'],
        summary='Delete Patient',
        responses={204: None, 404: OpenApiTypes.OBJECT},
    ),
)
class PatientViewSet(viewsets.ViewSet):
    serializer_class = PatientSerializer

    # Look up by FHIR logical id rather than the surrogate UUID PK so URLs
    # match the FHIR REST convention (`/Patient/{id}`).
    lookup_field = 'fhir_id'
    lookup_value_regex = r'[A-Za-z0-9\-\.]{1,64}'

    def get_queryset(self):
        return Patient.objects.all()

    def list(self, request):
        queryset = self.get_queryset()
        page_size = _pagination_size(request)
        offset = _pagination_offset(request, page_size)
        rows = queryset[offset:offset + page_size]
        return Response({
            'resourceType': 'Bundle',
            'type': 'searchset',
            'total': queryset.count(),
            'entry': [
                {'resource': row.resource} for row in rows
            ],
        })

    def retrieve(self, request, fhir_id=None):
        patient = _get_or_404(self.get_queryset(), fhir_id)
        return Response(patient.resource)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = PatientService.create(serializer.validated_data)
        return Response(patient.resource, status=status.HTTP_201_CREATED)

    def update(self, request, fhir_id=None):
        patient = _get_or_404(self.get_queryset(), fhir_id)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = PatientService.update(patient, serializer.validated_data)
        return Response(patient.resource)

    def partial_update(self, request, fhir_id=None):
        # FHIR PATCH semantics are non-trivial (JSON Patch / FHIRPath Patch);
        # for the OSS demo we merge the payload onto the stored resource and
        # re-validate. Clients requiring strict PATCH should use PUT.
        patient = _get_or_404(self.get_queryset(), fhir_id)
        merged = {**patient.resource, **(request.data or {})}
        merged['resourceType'] = 'Patient'
        serializer = self.serializer_class(data=merged)
        serializer.is_valid(raise_exception=True)
        patient = PatientService.update(patient, serializer.validated_data)
        return Response(patient.resource)

    def destroy(self, request, fhir_id=None):
        patient = _get_or_404(self.get_queryset(), fhir_id)
        patient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _get_or_404(queryset, fhir_id):
    from django.http import Http404
    instance = queryset.filter(fhir_id=fhir_id).first()
    if instance is None:
        raise Http404(f'Patient {fhir_id} not found')
    return instance


def _pagination_size(request):
    raw = request.query_params.get('_count')
    try:
        value = int(raw) if raw is not None else 25
    except ValueError:
        value = 25
    return max(1, min(value, 100))


def _pagination_offset(request, page_size):
    raw = request.query_params.get('_offset')
    try:
        value = int(raw) if raw is not None else 0
    except ValueError:
        value = 0
    return max(0, value)
