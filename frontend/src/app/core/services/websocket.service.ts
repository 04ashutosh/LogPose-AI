import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class WebSocketService {
  private socket: WebSocket | null = null;
  private messageSubject$ = new Subject<any>();

  connect(sessionId: string, token: string): Observable<any> {
    const wsUrl = `ws://localhost:8000/api/v1/chat/ws/${sessionId}?token=${token}`;
    this.socket = new WebSocket(wsUrl);

    this.socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.messageSubject$.next(data);
    };

    this.socket.onerror = (error) => {
      this.messageSubject$.error(error);
    };

    this.socket.onclose = () => {
      this.messageSubject$.complete();
    };

    return this.messageSubject$.asObservable();
  }

  sendMessage(action: string, data: any): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ action, data }));
    } else {
      console.error('WebSocket connection is not active.');
    }
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}