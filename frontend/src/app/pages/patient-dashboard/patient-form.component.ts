import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';

import { FhirPatient } from '../../models/fhir';
import { FhirService } from '../../services/fhir.service';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

/**
 * Minimal patient form: renders a form to create a new patient and POSTs it to `/api/fhir/v1/Patient/`.
 */
@Component({
  selector: 'app-patient-form',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <section>
      <div class="flex justify-between items-center">
        <h2>Create Patient</h2>
        <a routerLink="/patients" class="button">Back to Patients</a>
      </div>

      <form (ngSubmit)="onSubmit()" #patientForm="ngForm">
        <div>
          <label for="given">Patient ID:</label>
          <input type="text" id="id" name="id" [(ngModel)]="id" required />
        </div>

        <div>
          <label for="given">Given Name:</label>
          <input type="text" id="given" name="given" [(ngModel)]="givenName" required />
        </div>

        <div>
          <label for="family">Family Name:</label>
          <input type="text" id="family" name="family" [(ngModel)]="familyName" required />
        </div>

        <div>
          <label for="gender">Gender:</label>
          <select id="gender" name="gender" [(ngModel)]="gender" required>
            <option value="">Select Gender</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
            <option value="unknown">Unknown</option>
          </select>
        </div>

        <div>
          <label for="birthDate">Birth Date:</label>
          <input type="date" id="birthDate" name="birthDate" [(ngModel)]="birthDate" required />
        </div>

        <button type="submit" [disabled]="patientForm.invalid">Create Patient</button>
      </form>

      @if (loading()) {
        <p class="muted">Creating patient…</p>
      } @else if (error()) {
        <p class="muted">Failed to create patient: {{ error() }}</p>
      } @else if (success()) {
        <p class="muted">Patient created successfully!</p>
      }
    </section>
  `,
  styles: [
    `
      form div {
        margin-bottom: 1rem;
      }
    `,
  ],
})
export class PatientFormComponent implements OnInit {
  private readonly fhir = inject(FhirService);

  id = '';
  givenName = '';
  familyName = '';
  gender: 'male' | 'female' | 'other' | 'unknown' = 'unknown';
  birthDate = '';

  readonly loading = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly success = signal<boolean>(false);

  ngOnInit(): void { }

  onSubmit(): void {
    this.loading.set(true);
    this.error.set(null);
    this.success.set(false);

    const patient: FhirPatient = {
      resourceType: 'Patient',
      name: [
        {
          given: [this.givenName],
          family: this.familyName,
        },
      ],
      gender: this.gender,
      birthDate: this.birthDate,
      id: this.id,
    };

    this.fhir.createPatient(patient).subscribe({
      next: () => {
        this.loading.set(false);
        this.success.set(true);
        // Reset form fields
        this.givenName = '';
        this.familyName = '';
        this.gender = 'unknown';
        this.birthDate = '';
        this.id = '';
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err?.message ?? 'Unknown error');
      },
    });
  }
}