import { Injectable, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private apiUrl = 'http://localhost:8000/api/v1/auth';
  
  // Track authenticated status using Angular Signals
  currentUserToken = signal<string | null>(localStorage.getItem('token'));

  register(email: string, password: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/register`, { email, password });
  }

  login(email: string, password: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/login`, { email, password }).pipe(
      tap(res => {
        localStorage.setItem('token', res.access_token);
        this.currentUserToken.set(res.access_token);
      })
    );
  }

  logout(): void {
    localStorage.removeItem('token');
    this.currentUserToken.set(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return this.currentUserToken();
  }

  isAuthenticated(): boolean {
    return !!this.currentUserToken();
  }
}