/**
 * Narrow TypeScript models for the FHIR R4 resources this SPA touches.
 *
 * These are intentionally partial — the FHIR spec is huge and the SPA only
 * reads a handful of fields. Widen these types as new UI surfaces are added,
 * rather than trying to pre-model every optional element up front.
 */

export interface HumanName {
  use?: string;
  family?: string;
  given?: string[];
}

export interface FhirPatient {
  resourceType: 'Patient';
  id?: string;
  active?: boolean;
  name?: HumanName[];
  gender?: 'male' | 'female' | 'other' | 'unknown';
  birthDate?: string;
}

export interface FhirAppointment {
  resourceType: 'Appointment';
  id?: string;
  status: string;
  start?: string;
  end?: string;
  description?: string;
  participant: Array<{
    actor?: { reference?: string; display?: string };
    status: string;
  }>;
}

/** FHIR Bundle wrapper returned by list endpoints. */
export interface FhirBundle<T> {
  resourceType: 'Bundle';
  type: 'searchset';
  total: number;
  entry: Array<{ resource: T }>;
}
