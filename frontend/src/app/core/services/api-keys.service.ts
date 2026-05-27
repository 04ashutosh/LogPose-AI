import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export interface ApiKey { provider: string; masked_key: string; }

@Injectable({ providedIn: 'root' })
export class ApiKeyService {
  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:8000/api/v1/keys';

  getKeys() { return this.http.get<ApiKey[]>(this.apiUrl); }
  setKey(provider: string, api_key: string) { return this.http.post<ApiKey>(this.apiUrl, { provider, api_key }); }
}