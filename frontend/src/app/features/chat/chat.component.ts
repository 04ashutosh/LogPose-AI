import { Component, OnInit, OnDestroy, signal, inject, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../core/services/auth.service';
import { WebSocketService } from '../../core/services/websocket.service';
import { Subscription } from 'rxjs';

interface Message {
  role: string;
  content: string;
  agent_name?: string;
  step_name?: string;
}

interface Session {
  id: string;
  title: string;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html'
})
export class ChatComponent implements OnInit, OnDestroy {
  private authService = inject(AuthService);
  private wsService = inject(WebSocketService);
  private http = inject(HttpClient);

  private wsSubscription: Subscription | null = null;
  private chatUrl = 'http://localhost:8000/api/v1/chat';

  // Signals for state binding
  sessions = signal<Session[]>([]);
  activeSessionId = signal<string | null>(null);
  messages = signal<Message[]>([]);
  userInput = signal<string>('');
  
  // Real-time Agent Pipeline State tracking signals
  activeAgent = signal<string>('Idle');
  agentOutputs = signal<Record<string, string>>({
    'Planner Agent': '',
    'Architect Agent': '',
    'Coder Agent': '',
    'Reviewer Agent': ''
  });
  isOrchestrating = signal<boolean>(false);

    workspaceFiles = signal<{path: string, size: string}[]>([]);

  ngOnInit() {
    this.loadSessions();
  }

  ngOnDestroy() {
    this.wsService.disconnect();
    this.wsSubscription?.unsubscribe();
  }

  loadSessions() {
    this.http.get<Session[]>(`${this.chatUrl}/sessions`).subscribe(res => {
      this.sessions.set(res);
      if (res.length > 0) {
        this.selectSession(res[0].id);
      }
    });
  }

  createSession() {
    const title = prompt('Enter session navigation name:');
    if (!title) return;
    this.http.post<Session>(`${this.chatUrl}/sessions`, { title }).subscribe(res => {
      this.sessions.update(prev => [res, ...prev]);
      this.selectSession(res.id);
    });
  }

  deleteSession(sessionId: string, event: Event) {
    event.stopPropagation();
    
    if (confirm('Delete this session and all its messages?')) {
      this.http.delete(`${this.chatUrl}/sessions/${sessionId}`).subscribe({
        next: () => {
          this.sessions.update(prev => prev.filter(s => s.id !== sessionId));
          
          if (this.activeSessionId() === sessionId) {
            this.wsService.disconnect();
            this.wsSubscription?.unsubscribe();
            this.messages.set([]);
            this.workspaceFiles.set([]);
            this.activeSessionId.set(null);
            
            this.agentOutputs.set({
              'Planner Agent': '',
              'Architect Agent': '',
              'Coder Agent': '',
              'Reviewer Agent': ''
            });
            
            const remaining = this.sessions();
            if (remaining.length > 0) {
              this.selectSession(remaining[0].id);
            }
          }
        },
        error: (err) => console.error('Failed to delete session', err)
      });
    }
  }

  selectSession(sessionId: string) {
    this.wsService.disconnect();
    this.wsSubscription?.unsubscribe();
    
    this.activeSessionId.set(sessionId);
    this.messages.set([]);
    this.workspaceFiles.set([]);
    this.loadWorkspaceFiles();
    
    // Load historical session message traces
    this.http.get<any[]>(`${this.chatUrl}/sessions/${sessionId}/messages`).subscribe(msgs => {
      this.messages.set(msgs);
    });

    // Reconnect socket pipeline
    const token = this.authService.getToken() || '';
    this.wsSubscription = this.wsService.connect(sessionId, token).subscribe({
      next: (event) => this.handleWsMessage(event),
      error: (err) => console.error('WebSocket Error stream context:', err)
    });
  }

  handleWsMessage(event: any) {
    const { event: type, data } = event;
    const node = data.node;
    const content = data.content;

    if (type === 'node_start') {
      this.isOrchestrating.set(true);
      this.activeAgent.set(node);
      this.agentOutputs.update(prev => ({
        ...prev,
        [node]: `[Initiated node processing for ${node}...]\n`
      }));
    } else if (type === 'thinking') {
      // DeepSeek-R1 sends a single "thinking" event while reasoning internally
      this.agentOutputs.update(prev => ({
        ...prev,
        [node]: `${content}\n`
      }));
    } else if (type === 'token') {
      // Real content tokens (empty chunks are now filtered on the backend)
      this.agentOutputs.update(prev => ({
        ...prev,
        [node]: (prev[node] || '') + content
      }));
    } else if (type === 'node_end') {
      this.agentOutputs.update(prev => ({
        ...prev,
        [node]: content
      }));
    } else if (type === 'files_created') {
      // Coder agent created real files — refresh the file explorer
      this.loadWorkspaceFiles();
      this.agentOutputs.update(prev => ({
        ...prev,
        [node]: (prev[node] || '') + '\n\n' + content
      }));
    } else if (type === 'graph_complete') {
      this.loadWorkspaceFiles();
      this.isOrchestrating.set(false);
      this.activeAgent.set('Idle');
      
      // Push compiled agent output trace into chat messages
      this.messages.update(prev => [
        ...prev,
        {
          role: 'assistant',
          content: content,
          agent_name: 'LogPose Orchestrator',
          step_name: 'Execution Complete'
        }
      ]);
    }
  }

  sendMessage() {
    const promptText = this.userInput().trim();
    if (!promptText || !this.activeSessionId()) return;

    // Push local state
    this.messages.update(prev => [...prev, { role: 'user', content: promptText }]);
    this.userInput.set('');
    
    // Reset pipeline layout display state
    this.agentOutputs.set({
      'Planner Agent': '',
      'Architect Agent': '',
      'Coder Agent': '',
      'Reviewer Agent': ''
    });

    this.wsService.sendMessage('send_prompt', { prompt: promptText });
  }

  loadWorkspaceFiles() {
    const sid = this.activeSessionId();
    if (!sid) return;
    this.http.get<any>(`http://localhost:8000/api/v1/workspace/files/${sid}`).subscribe({
      next: (res) => this.workspaceFiles.set(res.files),
      error: (err) => console.error('Failed to load workspace files', err)
    });
  }

  logout() {
    this.authService.logout();
  }
}