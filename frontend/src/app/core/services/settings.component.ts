import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiKeyService, ApiKey } from '../../core/services/api-keys.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 bg-[#151D30] text-white rounded-xl border border-[#1E293B]">
      <h3 class="text-xl font-bold mb-4">Integrations (BYOK)</h3>
      
      <div class="space-y-4">
        <!-- OpenAI Input -->
        <div>
          <label>OpenAI API Key</label>
          <div class="flex gap-2 mt-1">
            <input type="password" [(ngModel)]="openaiKey" placeholder="sk-..." class="bg-[#0B0F19] p-2 rounded flex-1">
            <button (click)="saveKey('openai', openaiKey)" class="bg-indigo-600 px-4 rounded">Save</button>
          </div>
        </div>
        
        <!-- Anthropic Input -->
        <div>
          <label>Anthropic API Key</label>
          <div class="flex gap-2 mt-1">
            <input type="password" [(ngModel)]="anthropicKey" placeholder="sk-ant-..." class="bg-[#0B0F19] p-2 rounded flex-1">
            <button (click)="saveKey('anthropic', anthropicKey)" class="bg-indigo-600 px-4 rounded">Save</button>
          </div>
        </div>

        <!-- Gemini Input -->
        <div>
          <label>Google Gemini API Key</label>
          <div class="flex gap-2 mt-1">
            <input type="password" [(ngModel)]="geminiKey" placeholder="AIzaSy..." class="bg-[#0B0F19] p-2 rounded flex-1">
            <button (click)="saveKey('gemini', geminiKey)" class="bg-indigo-600 px-4 rounded">Save</button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class SettingsComponent {
  private keyService = inject(ApiKeyService);
  
  openaiKey = '';
  anthropicKey = '';
  geminiKey = '';
  
  ngOnInit() {
    this.keyService.getKeys().subscribe(keys => {
       // Loop through keys and display the masked versions in the UI if they exist
    });
  }

  saveKey(provider: string, key: string) {
    if(!key) return;
    this.keyService.setKey(provider, key).subscribe(() => {
       alert(`${provider} key saved securely!`);
       // clear input
       if(provider==='openai') this.openaiKey = '';
       if(provider==='anthropic') this.anthropicKey = '';
       if(provider==='gemini') this.geminiKey = '';
    });
  }
}