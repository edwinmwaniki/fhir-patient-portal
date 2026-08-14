"""FHIR R4 `Patient` resource, persisted as an indexed row plus canonical JSON.

The full FHIR payload is stored verbatim in `resource` so no information is
lost on round-trip; a handful of columns are denormalized off the payload to
support efficient search without giving up FHIR fidelity.
"""
import uuid

from django.db import models


class Patient(models.Model):
    # FHIR R4 Patient.gender codes.
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('unknown', 'Unknown'),
    ]

    # Internal surrogate key. FHIR logical id lives in `fhir_id` and is what
    # clients see as `Patient.id` in the resource payload.
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False)

    fhir_id = models.CharField(max_length=64, unique=True, db_index=True)

    active = models.BooleanField(default=True)

    gender = models.CharField(
        max_length=16, choices=GENDER_CHOICES, blank=True, default='')

    birth_date = models.DateField(null=True, blank=True)

    # Denormalized from the first entry in Patient.name[] to keep list/search
    # queries index-friendly. The authoritative value lives in `resource`.
    family_name = models.CharField(max_length=255, blank=True, default='')
    given_name = models.CharField(max_length=255, blank=True, default='')

    # Canonical FHIR R4 Patient JSON, validated by the serializer before it
    # ever reaches the model layer.
    resource = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fhir_patient'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['family_name', 'given_name']),
            models.Index(fields=['birth_date']),
        ]

    def __str__(self):
        display = ' '.join(part for part in (
            self.given_name, self.family_name) if part).strip()
        return display or f'Patient {self.fhir_id}'
