import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header class="container">
      <h1>FHIR Patient Portal</h1>
      <nav>
        <a routerLink="/patients" routerLinkActive="active">Patients</a>
        <a routerLink="/appointments" routerLinkActive="active">Appointments</a>
      </nav>
    </header>
    <main class="container">
      <router-outlet></router-outlet>
    </main>
  `,
  styles: [
    `
      header {
        border-bottom: 1px solid var(--color-border);
      }
      h1 {
        margin: 0 0 0.5rem;
      }
      nav a {
        color: var(--color-accent);
        text-decoration: none;
        margin-right: 1rem;
      }
      nav a.active {
        font-weight: 600;
        text-decoration: underline;
      }
    `,
  ],
})
export class AppComponent {}
