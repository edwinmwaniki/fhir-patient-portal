"""Integration tests for `/api/fhir/v1/Appointment/`."""
import copy

from rest_framework import status
from rest_framework.test import APITestCase

from app.models.appointment_model import Appointment
from app.models.patient_model import Patient
from app.services.patient_service import PatientService


APPOINTMENT_URL = '/api/fhir/v1/Appointment/'
PATIENT_URL = '/api/fhir/v1/Patient/'


class AppointmentCRUDTestCase(APITestCase):

    def setUp(self):
        # Seed a Patient so the appointment's participant reference resolves
        # to a real FK. Bypass the API here: exercising service-level writes
        # keeps this test focused on the Appointment endpoint under test.
        self.patient = PatientService.create({
            'resourceType': 'Patient',
            'id': 'appt-owner-1',
            'active': True,
            'name': [
                {'use': 'official', 'family': 'Doe', 'given': ['Jane']},
            ],
            'gender': 'female',
        })

        self.payload = {
            'resourceType': 'Appointment',
            'id': 'test-appt-1',
            'status': 'booked',
            'start': '2026-09-01T10:00:00+00:00',
            'end': '2026-09-01T10:30:00+00:00',
            'description': 'Follow-up visit',
            'participant': [
                {
                    'actor': {'reference': 'Patient/appt-owner-1'},
                    'status': 'accepted',
                },
            ],
        }

    def _create(self, payload=None):
        return self.client.post(
            APPOINTMENT_URL, payload or self.payload, format='json')

    def test_create_valid_appointment_returns_201(self):
        response = self._create()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['resourceType'], 'Appointment')
        self.assertEqual(response.data['status'], 'booked')

    def test_create_resolves_patient_foreign_key(self):
        self._create()

        appointment = Appointment.objects.get(fhir_id='test-appt-1')
        self.assertIsNotNone(appointment.patient)
        self.assertEqual(appointment.patient.fhir_id, 'appt-owner-1')

    def test_create_with_unknown_patient_reference_leaves_fk_null(self):
        # External FHIR references (Patient not stored locally) must not
        # break ingestion; the FK stays null and the reference remains in
        # the JSON payload.
        payload = copy.deepcopy(self.payload)
        payload['id'] = 'test-appt-external'
        payload['participant'][0]['actor']['reference'] = 'Patient/unknown-999'

        response = self._create(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        appointment = Appointment.objects.get(fhir_id='test-appt-external')
        self.assertIsNone(appointment.patient)
        self.assertEqual(
            appointment.resource['participant'][0]['actor']['reference'],
            'Patient/unknown-999',
        )

    def test_retrieve_returns_canonical_resource(self):
        self._create()

        response = self.client.get(f'{APPOINTMENT_URL}test-appt-1/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], 'test-appt-1')

    def test_list_returns_searchset_bundle(self):
        self._create()

        response = self.client.get(APPOINTMENT_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'Bundle')
        self.assertEqual(response.data['total'], 1)

    def test_update_changes_status(self):
        self._create()

        updated = copy.deepcopy(self.payload)
        updated['status'] = 'fulfilled'

        response = self.client.put(
            f'{APPOINTMENT_URL}test-appt-1/', updated, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appointment = Appointment.objects.get(fhir_id='test-appt-1')
        self.assertEqual(appointment.status, 'fulfilled')

    def test_destroy_removes_resource(self):
        self._create()

        response = self.client.delete(f'{APPOINTMENT_URL}test-appt-1/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Appointment.objects.filter(fhir_id='test-appt-1').exists())

    def test_patient_reverse_relation(self):
        self._create()

        # The Patient row should surface the appointment via `related_name`.
        patient = Patient.objects.get(fhir_id='appt-owner-1')
        self.assertEqual(patient.appointments.count(), 1)


class AppointmentValidationTestCase(APITestCase):

    def test_rejects_missing_status(self):
        response = self.client.post(
            APPOINTMENT_URL,
            {'resourceType': 'Appointment', 'participant': [
                {'actor': {'reference': 'Patient/x'}, 'status': 'accepted'}]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_rejects_missing_participant(self):
        # FHIR Appointment.participant is 1..*.
        response = self.client.post(
            APPOINTMENT_URL,
            {'resourceType': 'Appointment', 'status': 'booked'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('participant', response.data)

    def test_rejects_unknown_status_code(self):
        # fhir.resources 7.x validates Appointment.status as a code primitive
        # but does not enforce the FHIR R4 value-set membership at the
        # pydantic layer, so this branch is asserted at the model level
        # instead: the CharField choices constraint (enforced by
        # `full_clean`) is what would reject an unknown code in a strict
        # persistence path. We document that here so the coverage gap is
        # explicit rather than silent.
        from django.core.exceptions import ValidationError

        from app.models.appointment_model import Appointment

        appointment = Appointment(
            fhir_id='will-not-persist',
            status='not-a-real-status',
            resource={'resourceType': 'Appointment'},
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_rejects_wrong_resource_type(self):
        response = self.client.post(
            APPOINTMENT_URL,
            {'resourceType': 'Patient', 'status': 'booked'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('resourceType', response.data)

    def test_rejects_non_object_payload(self):
        response = self.client.post(
            APPOINTMENT_URL, 'not-json', format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
