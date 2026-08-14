"""Integration tests for `/api/fhir/v1/Patient/`.

The suite exercises the happy path plus the schema-rejection branches so a
regression in either the DRF wiring or the pydantic validation layer surfaces
immediately.
"""
import copy

from rest_framework import status
from rest_framework.test import APITestCase

from app.models.patient_model import Patient


PATIENT_URL = '/api/fhir/v1/Patient/'


class PatientCRUDTestCase(APITestCase):

    def setUp(self):
        # Baseline payload built from the conftest fixture template. Copied
        # per-test to keep mutations isolated.
        self.payload = {
            'resourceType': 'Patient',
            'id': 'test-patient-1',
            'active': True,
            'name': [
                {'use': 'official', 'family': 'Doe', 'given': ['Jane']},
            ],
            'gender': 'female',
            'birthDate': '1985-04-12',
        }

    def _create(self, payload=None):
        return self.client.post(
            PATIENT_URL, payload or self.payload, format='json')

    def test_create_valid_patient_returns_201(self):
        response = self._create()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['resourceType'], 'Patient')
        self.assertEqual(response.data['id'], 'test-patient-1')
        self.assertEqual(response.data['gender'], 'female')

    def test_create_persists_denormalized_columns(self):
        self._create()

        patient = Patient.objects.get(fhir_id='test-patient-1')
        self.assertEqual(patient.family_name, 'Doe')
        self.assertEqual(patient.given_name, 'Jane')
        self.assertEqual(patient.gender, 'female')
        self.assertEqual(patient.birth_date.isoformat(), '1985-04-12')

    def test_retrieve_returns_canonical_resource(self):
        self._create()

        response = self.client.get(f'{PATIENT_URL}test-patient-1/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'Patient')
        self.assertEqual(response.data['id'], 'test-patient-1')

    def test_list_returns_searchset_bundle(self):
        self._create()

        response = self.client.get(PATIENT_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resourceType'], 'Bundle')
        self.assertEqual(response.data['type'], 'searchset')
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(
            response.data['entry'][0]['resource']['id'], 'test-patient-1')

    def test_update_replaces_resource(self):
        self._create()

        updated = copy.deepcopy(self.payload)
        updated['gender'] = 'other'
        updated['name'][0]['family'] = 'Roe'

        response = self.client.put(
            f'{PATIENT_URL}test-patient-1/', updated, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient = Patient.objects.get(fhir_id='test-patient-1')
        self.assertEqual(patient.gender, 'other')
        self.assertEqual(patient.family_name, 'Roe')

    def test_destroy_removes_resource(self):
        self._create()

        response = self.client.delete(f'{PATIENT_URL}test-patient-1/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Patient.objects.filter(fhir_id='test-patient-1').exists())


class PatientValidationTestCase(APITestCase):
    # These tests target the fhir.resources validation layer via the
    # serializer; every case must return HTTP 400 with a structured body.

    def test_rejects_missing_resource_type(self):
        response = self.client.post(
            PATIENT_URL, {'gender': 'female'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('resourceType', response.data)

    def test_rejects_wrong_resource_type(self):
        response = self.client.post(
            PATIENT_URL,
            {'resourceType': 'Practitioner', 'gender': 'female'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('resourceType', response.data)

    def test_rejects_invalid_birth_date(self):
        response = self.client.post(
            PATIENT_URL,
            {'resourceType': 'Patient', 'birthDate': 'not-a-date'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('birthDate', response.data)

    def test_rejects_non_object_payload(self):
        response = self.client.post(
            PATIENT_URL, ['not', 'an', 'object'], format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_unknown_gender_shape(self):
        # `gender` must be a string primitive; a nested object violates the
        # FHIR schema and pydantic should reject it.
        response = self.client.post(
            PATIENT_URL,
            {'resourceType': 'Patient', 'gender': {'nested': 'object'}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('gender', response.data)
