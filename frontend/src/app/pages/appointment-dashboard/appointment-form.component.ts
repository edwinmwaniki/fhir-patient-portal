import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';

import { FhirAppointment } from '../../models/fhir';
import { FhirService } from '../../services/fhir.service';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

/**
 * Minimal appointment form: renders a form to create a new appointment and POSTs it to `/api/fhir/v1/Appointment/`.
 */
@Component({
    selector: 'app-appointment-form',
    standalone: true,
    imports: [CommonModule, RouterLink, FormsModule],
    template: `
    <section>
      <div class="flex justify-between items-center">
        <h2>Create Appointment</h2>
        <a routerLink="/appointments" class="button">Back to Appointments</a>
      </div>

      <form (ngSubmit)="onSubmit()" #appointmentForm="ngForm">
        <div>
          <label for="id">Appointment ID:</label>
          <input type="text" id="id" name="id" [(ngModel)]="id" required />
        </div>

        <div>
          <label for="patientId">Patient ID:</label>
          <input type="text" id="patientId" name="patientId" [(ngModel)]="patientId" required />
        </div>

        <div>
          <label for="practitionerId">Practitioner ID:</label>
          <input type="text" id="practitionerId" name="practitionerId" [(ngModel)]="practitionerId" required />
        </div>

        <div>
          <label for="status">Status:</label>
          <select id="status" name="status" [(ngModel)]="status" required>
            <option value="">Select Status</option>
            <option value="proposed">Proposed</option>
            <option value="pending">Pending</option>
            <option value="booked">Booked</option>
            <option value="arrived">Arrived</option>
            <option value="fulfilled">Fulfilled</option>
            <option value="cancelled">Cancelled</option>
            <option value="noshow">No Show</option>
          </select>
        </div>

        <div>
          <label for="start">Start Date/Time:</label>
          <input type="datetime-local" id="start" name="start" [(ngModel)]="start" required />
        </div>

        <div>
          <label for="end">End Date/Time:</label>
          <input type="datetime-local" id="end" name="end" [(ngModel)]="end" required />
        </div>

        <div>
          <label for="description">Description:</label>
          <input type="text" id="description" name="description" [(ngModel)]="description" />
        </div>

        <button type="submit" [disabled]="appointmentForm.invalid">Create Appointment</button>
      </form>

      @if (loading()) {
        <p class="muted">Creating appointment…</p>
      } @else if (error()) {
        <p class="muted">Failed to create appointment: {{ error() }}</p>
      } @else if (success()) {
        <p class="muted">Appointment created successfully!</p>
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
export class AppointmentFormComponent implements OnInit {
    private readonly fhir = inject(FhirService);

    id = '';
    patientId = '';
    practitionerId = '';
    status: 'proposed' | 'pending' | 'booked' | 'arrived' | 'fulfilled' | 'cancelled' | 'noshow' = 'proposed';
    start = '';
    end = '';
    description = '';

    readonly loading = signal<boolean>(false);
    readonly error = signal<string | null>(null);
    readonly success = signal<boolean>(false);

    ngOnInit(): void { }

    onSubmit(): void {
        this.loading.set(true);
        this.error.set(null);
        this.success.set(false);

        const appointment: FhirAppointment = {
            resourceType: 'Appointment',
            id: this.id,
            status: this.status,
            start: new Date(this.start).toISOString(),
            end: new Date(this.end).toISOString(),
            participant: [
                {
                    actor: {
                        reference: `Patient/${this.patientId}`,
                    },
                    status: 'accepted',
                },
                {
                    actor: {
                        reference: `Practitioner/${this.practitionerId}`,
                    },
                    status: 'accepted',
                },
            ],
            description: this.description,
        };

        this.fhir.createAppointment(appointment).subscribe({
            next: () => {
                this.loading.set(false);
                this.success.set(true);
                // Reset form fields
                this.id = '';
                this.patientId = '';
                this.practitionerId = '';
                this.status = 'proposed';
                this.start = '';
                this.end = '';
                this.description = '';
            },
            error: (err) => {
                this.loading.set(false);
                this.error.set(err?.message ?? 'Unknown error');
            },
        });
    }
}
