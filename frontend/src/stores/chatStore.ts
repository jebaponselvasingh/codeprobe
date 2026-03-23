import { create } from 'zustand';
import { API_BASE } from '../constants/config';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

interface ChatStore {
  isOpen: boolean;
  sessionId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  suggestedQuestions: string[];
  error: string | null;

  openChat: (sessionId: string, criticalFindings?: string[]) => void;
  closeChat: () => void;
  sendMessage: (text: string) => Promise<void>;
  clearChat: () => void;
}

function buildSuggestedQuestions(findings: string[]): string[] {
  const questions: string[] = [];
  const templates = [
    (f: string) => `Can you explain the "${f}" issue?`,
    (f: string) => `How do I fix the "${f}" issue?`,
    (f: string) => `Why is "${f}" a problem?`,
  ];
  for (let i = 0; i < Math.min(findings.length, 3); i++) {
    const finding = findings[i];
    if (finding) {
      questions.push(templates[i % templates.length](finding));
    }
  }
  return questions;
}

export const useChatStore = create<ChatStore>()((set, get) => ({
  isOpen: false,
  sessionId: null,
  messages: [],
  isStreaming: false,
  suggestedQuestions: [],
  error: null,

  openChat: (sessionId, criticalFindings = []) => {
    set({
      isOpen: true,
      sessionId,
      suggestedQuestions: buildSuggestedQuestions(criticalFindings),
    });
  },

  closeChat: () => set({ isOpen: false }),

  clearChat: () => set({ messages: [], error: null }),

  sendMessage: async (text: string) => {
    const { sessionId, messages } = get();
    if (!sessionId || !text.trim()) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    };

    const assistantPlaceholder: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      isStreaming: true,
    };

    set(s => ({
      messages: [...s.messages, userMessage, assistantPlaceholder],
      isStreaming: true,
      error: null,
    }));

    const assistantId = assistantPlaceholder.id;

    try {
      const history = [...messages, userMessage].slice(-10);
      const response = await fetch(`${API_BASE}/review/${sessionId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      });

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6)) as {
                type: 'token' | 'complete' | 'error';
                content?: string;
                message?: string;
              };

              if (event.type === 'token' && event.content) {
                set(s => ({
                  messages: s.messages.map(m =>
                    m.id === assistantId
                      ? { ...m, content: m.content + event.content! }
                      : m
                  ),
                }));
              } else if (event.type === 'complete') {
                set(s => ({
                  isStreaming: false,
                  messages: s.messages.map(m =>
                    m.id === assistantId ? { ...m, isStreaming: false } : m
                  ),
                }));
              } else if (event.type === 'error') {
                set(s => ({
                  isStreaming: false,
                  error: event.message ?? 'An error occurred',
                  messages: s.messages.map(m =>
                    m.id === assistantId ? { ...m, isStreaming: false } : m
                  ),
                }));
              }
            } catch {
              // ignore parse errors
            }
          }
        }
      }

      // Ensure streaming is marked done after stream ends
      set(s => ({
        isStreaming: false,
        messages: s.messages.map(m =>
          m.id === assistantId ? { ...m, isStreaming: false } : m
        ),
      }));
    } catch (err) {
      set(s => ({
        isStreaming: false,
        error: err instanceof Error ? err.message : String(err),
        messages: s.messages.map(m =>
          m.id === assistantId ? { ...m, isStreaming: false } : m
        ),
      }));
    }
  },
}));
