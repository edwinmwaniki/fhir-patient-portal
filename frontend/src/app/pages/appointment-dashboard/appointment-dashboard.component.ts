import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';

import { FhirAppointment } from '../../models/fhir';
import { FhirService } from '../../services/fhir.service';
import { RouterLink } from '@angular/router';

/**
 * Minimal appointment dashboard: fetches `/api/fhir/v1/Appointment/`, renders the
 * canonical name plus a couple of demographic fields, and surfaces load /
 * error state without any UI framework dependency.
 */
@Component({
  selector: 'app-appointment-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <section>
      <div class="flex justify-between items-center">
        <h2>Appointments</h2>
        <a routerLink="/appointments/new" class="button">Create Appointment</a>
      </div>

      @if (loading()) {
        <p class="muted">Loading appointments…</p>
      } @else if (error()) {
        <p class="muted">Failed to load appointments: {{ error() }}</p>
      } @else if (appointments().length === 0) {
        <p class="muted">
          No appointments yet. Post one to
          <code>/api/fhir/v1/Appointment/</code> to see it here.
        </p>
      } @else {
        <ul class="reset">
          @for (appointment of appointments(); track appointment.id) {
            <li class="card">
              <strong>{{ displayName(appointment) }}</strong>
              <div class="muted">
                <span>{{ appointment.status || 'unknown' }}</span>
                @if (appointment.start) {
                  <span> · starts {{ appointment.start | date:'short' }}</span>
                }
                @if (appointment.end) {
                  <span> · ends {{ appointment.end | date:'short' }}</span>
                }
                @if (appointment.id) {
                  <span> · id {{ appointment.id }}</span>
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
export class AppointmentDashboardComponent implements OnInit {
  private readonly fhir = inject(FhirService);

  readonly appointments = signal<FhirAppointment[]>([]);
  readonly loading = signal<boolean>(true);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.fhir.listAppointments().subscribe({
      next: (appointments) => {
        this.appointments.set(appointments);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err?.message ?? 'Unknown error');
        this.loading.set(false);
      },
    });
  }

  displayName(appointment: FhirAppointment): string {
    const primary = appointment.participant?.[0];
    if (!primary) {
      return appointment.id ?? 'Unnamed appointment';
    }
    const display = primary.actor?.display ?? '';
    return display || (appointment.id ?? 'Unnamed appointment');
  }
}
