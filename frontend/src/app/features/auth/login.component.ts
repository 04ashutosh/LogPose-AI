import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="flex items-center justify-center min-h-screen bg-[#0B0F19] text-white">
      <div class="w-full max-w-md p-8 bg-[#151D30] rounded-2xl border border-[#1E293B] shadow-2xl">
        <h2 class="text-3xl font-bold text-center bg-gradient-to-r from-indigo-400 to-pink-500 bg-clip-text text-transparent mb-8">
          Navigate Intelligence
        </h2>
        
        @if (errorMessage()) {
          <div class="p-3 mb-4 text-sm bg-pink-900/50 border border-pink-700/50 text-pink-300 rounded-lg">
            {{ errorMessage() }}
          </div>
        }

        <form (submit)="onSubmit()" class="space-y-6">
          <div>
            <label class="block text-xs uppercase tracking-wider font-semibold text-slate-400 mb-2">Email Address</label>
            <input 
              type="email" 
              [(ngModel)]="email" 
              name="email" 
              required
              class="w-full px-4 py-3 bg-[#0B0F19] border border-[#1E293B] rounded-xl outline-none focus:border-indigo-500 transition text-sm"
            />
          </div>

          <div>
            <label class="block text-xs uppercase tracking-wider font-semibold text-slate-400 mb-2">Password</label>
            <input 
              type="password" 
              [(ngModel)]="password" 
              name="password" 
              required
              class="w-full px-4 py-3 bg-[#0B0F19] border border-[#1E293B] rounded-xl outline-none focus:border-indigo-500 transition text-sm"
            />
          </div>

          <button 
            type="submit" 
            [disabled]="isLoading()"
            class="w-full py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-bold transition text-sm disabled:opacity-50"
          >
            {{ isLoading() ? 'Securing passage...' : 'Login' }}
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-slate-400">
          First voyage? 
          <a routerLink="/register" class="text-indigo-400 hover:text-indigo-300 font-semibold">Sign up here</a>
        </p>
      </div>
    </div>
  `
})
export class LoginComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  email = signal<string>('');
  password = signal<string>('');
  isLoading = signal<boolean>(false);
  errorMessage = signal<string | null>(null);

  onSubmit() {
    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.authService.login(this.email(), this.password()).subscribe({
      next: () => {
        this.router.navigate(['/chat']);
      },
      error: (err) => {
        this.errorMessage.set(err.error?.detail || 'Authentication failed. Please verify credentials.');
        this.isLoading.set(false);
      }
    });
  }
}