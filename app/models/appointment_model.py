"""FHIR R4 `Appointment` resource.

The canonical FHIR JSON is stored in `resource`; scalar columns are
denormalized off the payload to support scheduling queries (by status, by
time range, by patient) without scanning JSON.
"""
import uuid

from django.db import models

from app.models.patient_model import Patient


class Appointment(models.Model):
    # FHIR R4 Appointment.status value set.
    APPOINTMENT_STATUS = [
        ('proposed', 'Proposed'),
        ('pending', 'Pending'),
        ('booked', 'Booked'),
        ('arrived', 'Arrived'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
        ('noshow', 'No Show'),
        ('entered-in-error', 'Entered in Error'),
        ('checked-in', 'Checked In'),
        ('waitlist', 'Waitlist'),
    ]

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False)

    fhir_id = models.CharField(max_length=64, unique=True, db_index=True)

    status = models.CharField(max_length=32, choices=APPOINTMENT_STATUS)

    # start/end are optional in FHIR R4 (required only when status is booked,
    # arrived, or fulfilled). We enforce that constraint at the service layer.
    start = models.DateTimeField(null=True, blank=True, db_index=True)
    end = models.DateTimeField(null=True, blank=True)

    description = models.TextField(blank=True, default='')

    # Denormalized FK to Patient. FHIR appointments can reference multiple
    # participant actors (Practitioner, Location, Device...); for the OSS
    # demo scope we index the primary Patient participant. The full
    # participant array remains available in `resource`.
    patient = models.ForeignKey(
        Patient, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='appointments')

    resource = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fhir_appointment'
        ordering = ['-start', '-created_at']
        indexes = [
            models.Index(fields=['status', 'start']),
            models.Index(fields=['patient', 'start']),
        ]

    def __str__(self):
        return f'Appointment {self.fhir_id} ({self.status})'
