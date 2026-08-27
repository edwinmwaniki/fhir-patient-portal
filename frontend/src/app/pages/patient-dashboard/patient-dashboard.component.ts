import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';

import { FhirPatient } from '../../models/fhir';
import { FhirService } from '../../services/fhir.service';
import { RouterLink } from '@angular/router';

/**
 * Minimal patient dashboard: fetches `/api/fhir/v1/Patient/`, renders the
 * canonical name plus a couple of demographic fields, and surfaces load /
 * error state without any UI framework dependency.
 */
@Component({
    selector: 'app-patient-dashboard',
    standalone: true,
    imports: [CommonModule, RouterLink],
    template: `
    <section>
        <div class="flex justify-between items-center">
            <h2>Patients</h2>
            <a routerLink="/patients/new" class="button">Create Patient</a>
        </div>

      @if (loading()) {
        <p class="muted">Loading patients…</p>
      } @else if (error()) {
        <p class="muted">Failed to load patients: {{ error() }}</p>
      } @else if (patients().length === 0) {
        <p class="muted">
          No patients yet. Post one to
          <code>/api/fhir/v1/Patient/</code> to see it here.
        </p>
      } @else {
        <ul class="reset">
          @for (patient of patients(); track patient.id) {
            <li class="card">
              <strong>{{ displayName(patient) }}</strong>
              <div class="muted">
                <span>{{ patient.gender || 'unknown' }}</span>
                @if (patient.birthDate) {
                  <span> · born {{ patient.birthDate }}</span>
                }
                @if (patient.id) {
                  <span> · id {{ patient.id }}</span>
                }
              </div>
            </li>
          }
        </ul>
      }
    </section>
  `,
    styles: [
        `
      ul.reset {
        list-style: none;
        padding: 0;
        margin: 0;
      }
    `,
    ],
})
export class PatientDashboardComponent implements OnInit {
    private readonly fhir = inject(FhirService);

    readonly patients = signal<FhirPatient[]>([]);
    readonly loading = signal<boolean>(true);
    readonly error = signal<string | null>(null);

    ngOnInit(): void {
        this.fhir.listPatients().subscribe({
            next: (patients) => {
                this.patients.set(patients);
                this.loading.set(false);
            },
            error: (err) => {
                this.error.set(err?.message ?? 'Unknown error');
                this.loading.set(false);
            },
        });
    }

    displayName(patient: FhirPatient): string {
        const primary = patient.name?.[0];
        if (!primary) {
            return patient.id ?? 'Unnamed patient';
        }
        const given = (primary.given ?? []).join(' ').trim();
        const family = primary.family ?? '';
        const display = `${given} ${family}`.trim();
        return display || (patient.id ?? 'Unnamed patient');
    }
}
