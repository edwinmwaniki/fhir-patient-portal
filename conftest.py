"""Project-wide pytest configuration.

Provides synthetic FHIR R4 payloads and a small ergonomic helper so tests
never hand-craft JSON blobs inline. External-service mocking hooks live
here too; they're no-ops today because the OSS demo has no outbound calls
yet, but the plumbing is in place for future integrations (e.g. notify
services) so tests fail loudly if a real HTTP call sneaks in.
"""
import copy
import uuid

import pytest


# ---------------------------------------------------------------------------
# Outbound-call safety net.
# ---------------------------------------------------------------------------
# Any future service that hits the network should register a corresponding
# autouse fixture here to swap the client for a fake. Keeping the hook empty
# but explicit signals intent to future contributors.

@pytest.fixture(autouse=True)
def _disable_external_calls(monkeypatch):
    # Deliberately empty. Add monkeypatches here when outbound HTTP is
    # introduced so tests never accidentally hit real endpoints.
    yield


# ---------------------------------------------------------------------------
# Synthetic FHIR payloads.
# ---------------------------------------------------------------------------
# Fresh deepcopy per fixture invocation so tests can freely mutate the dict
# without leaking state into their neighbours.

_PATIENT_TEMPLATE = {
    'resourceType': 'Patient',
    'active': True,
    'name': [
        {'use': 'official', 'family': 'Doe', 'given': ['Jane', 'Q']},
    ],
    'gender': 'female',
    'birthDate': '1985-04-12',
    'telecom': [
        {'system': 'email', 'value': 'jane.doe@example.com', 'use': 'home'},
    ],
}


_APPOINTMENT_TEMPLATE = {
    'resourceType': 'Appointment',
    'status': 'booked',
    'start': '2026-09-01T10:00:00+00:00',
    'end': '2026-09-01T10:30:00+00:00',
    'description': 'Follow-up visit',
    'participant': [
        {
            'actor': {'reference': 'Patient/placeholder'},
            'status': 'accepted',
        },
    ],
}


@pytest.fixture
def patient_payload():
    """A minimally-valid FHIR R4 Patient with a random logical id."""
    payload = copy.deepcopy(_PATIENT_TEMPLATE)
    payload['id'] = f'pat-{uuid.uuid4().hex[:12]}'
    return payload


@pytest.fixture
def appointment_payload():
    """A minimally-valid FHIR R4 Appointment with a random logical id."""
    payload = copy.deepcopy(_APPOINTMENT_TEMPLATE)
    payload['id'] = f'app-{uuid.uuid4().hex[:12]}'
    return payload


@pytest.fixture
def appointment_payload_for(patient_payload):
    """Build an Appointment payload whose participant links to a Patient.

    Usage:
        appt = appointment_payload_for(patient_payload)
    """
    def _factory(patient):
        payload = copy.deepcopy(_APPOINTMENT_TEMPLATE)
        payload['id'] = f'app-{uuid.uuid4().hex[:12]}'
        payload['participant'][0]['actor']['reference'] = (
            f"Patient/{patient['id']}")
        return payload
    return _factory
