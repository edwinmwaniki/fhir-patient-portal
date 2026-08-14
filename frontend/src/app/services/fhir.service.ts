import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import {
  FhirAppointment,
  FhirBundle,
  FhirPatient,
} from '../models/fhir';

/**
 * Thin HTTP client for the FHIR REST API mounted at `/api/fhir/v1/`.
 *
 * When served through Nginx (docker-compose) the SPA and the API share an
 * origin so the relative base URL below "just works" without CORS.
 * During `ng serve` development, wire this same path through the Angular
 * dev-server proxy (`proxy.conf.json`).
 */
@Injectable({ providedIn: 'root' })
export class FhirService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = '/api/fhir/v1';

  listPatients(): Observable<FhirPatient[]> {
    return this.http
      .get<FhirBundle<FhirPatient>>(`${this.baseUrl}/Patient/`)
      .pipe(map((bundle) => (bundle.entry ?? []).map((e) => e.resource)));
  }

  getPatient(id: string): Observable<FhirPatient> {
    return this.http.get<FhirPatient>(`${this.baseUrl}/Patient/${id}/`);
  }

  createPatient(patient: FhirPatient): Observable<FhirPatient> {
    return this.http.post<FhirPatient>(`${this.baseUrl}/Patient/`, patient);
  }

  listAppointments(): Observable<FhirAppointment[]> {
    return this.http
      .get<FhirBundle<FhirAppointment>>(`${this.baseUrl}/Appointment/`)
      .pipe(map((bundle) => (bundle.entry ?? []).map((e) => e.resource)));
  }
}
