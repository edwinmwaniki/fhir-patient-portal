import { Routes } from '@angular/router';

import { PatientDashboardComponent } from './pages/patient-dashboard/patient-dashboard.component';
import { AppointmentDashboardComponent } from './pages/appointment-dashboard/appointment-dashboard.component';
import { PatientFormComponent } from './pages/patient-dashboard/patient-form.component';
import { AppointmentFormComponent } from './pages/appointment-dashboard/appointment-form.component';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'patients' },
  { path: 'patients', component: PatientDashboardComponent },
  { path: 'patients/new', component: PatientFormComponent },
  { path: 'appointments', component: AppointmentDashboardComponent },
  { path: 'appointments/new', component: AppointmentFormComponent },
  { path: '**', redirectTo: 'patients' },
];
