import { Routes } from '@angular/router';

import { PatientDashboardComponent } from './pages/patient-dashboard/patient-dashboard.component';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'patients' },
  { path: 'patients', component: PatientDashboardComponent },
  { path: '**', redirectTo: 'patients' },
];
