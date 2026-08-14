"""FHIR R4 Appointment ViewSet."""
from django.http import Http404
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.response import Response

from app.models.appointment_model import Appointment
from app.serializers.appointment_serializer import AppointmentSerializer
from app.services.appointment_service import AppointmentService


_APPOINTMENT_EXAMPLE = OpenApiExample(
    name='Minimal FHIR R4 Appointment',
    value={
        'resourceType': 'Appointment',
        'id': 'appt-example-1',
        'status': 'booked',
        'start': '2026-09-01T10:00:00+00:00',
        'end': '2026-09-01T10:30:00+00:00',
        'description': 'Follow-up visit',
        'participant': [
            {
                'actor': {'reference': 'Patient/example-1'},
                'status': 'accepted',
            },
        ],
    },
)


@extend_schema_view(
    list=extend_schema(
        tags=['Appointment'],
        summary='Search Appointments',
        description='Returns a FHIR `Bundle` (`type: searchset`) of Appointments.',
        responses={200: OpenApiTypes.OBJECT},
    ),
    retrieve=extend_schema(
        tags=['Appointment'],
        summary='Read Appointment by id',
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    ),
    create=extend_schema(
        tags=['Appointment'],
        summary='Create Appointment',
        request=OpenApiTypes.OBJECT,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
        examples=[_APPOINTMENT_EXAMPLE],
    ),
    update=extend_schema(
        tags=['Appointment'],
        summary='Update Appointment (PUT)',
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
        examples=[_APPOINTMENT_EXAMPLE],
    ),
    partial_update=extend_schema(
        tags=['Appointment'],
        summary='Patch Appointment (merge)',
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    ),
    destroy=extend_schema(
        tags=['Appointment'],
        summary='Delete Appointment',
        responses={204: None, 404: OpenApiTypes.OBJECT},
    ),
)
class AppointmentViewSet(viewsets.ViewSet):
    serializer_class = AppointmentSerializer

    lookup_field = 'fhir_id'
    lookup_value_regex = r'[A-Za-z0-9\-\.]{1,64}'

    def get_queryset(self):
        # select_related on the denormalized patient FK keeps list responses
        # from N+1'ing when we start returning included resources.
        return Appointment.objects.select_related('patient').all()

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
        appointment = _get_or_404(self.get_queryset(), fhir_id)
        return Response(appointment.resource)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = AppointmentService.create(serializer.validated_data)
        return Response(appointment.resource, status=status.HTTP_201_CREATED)

    def update(self, request, fhir_id=None):
        appointment = _get_or_404(self.get_queryset(), fhir_id)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = AppointmentService.update(
            appointment, serializer.validated_data)
        return Response(appointment.resource)

    def partial_update(self, request, fhir_id=None):
        appointment = _get_or_404(self.get_queryset(), fhir_id)
        merged = {**appointment.resource, **(request.data or {})}
        merged['resourceType'] = 'Appointment'
        serializer = self.serializer_class(data=merged)
        serializer.is_valid(raise_exception=True)
        appointment = AppointmentService.update(
            appointment, serializer.validated_data)
        return Response(appointment.resource)

    def destroy(self, request, fhir_id=None):
        appointment = _get_or_404(self.get_queryset(), fhir_id)
        appointment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _get_or_404(queryset, fhir_id):
    instance = queryset.filter(fhir_id=fhir_id).first()
    if instance is None:
        raise Http404(f'Appointment {fhir_id} not found')
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
