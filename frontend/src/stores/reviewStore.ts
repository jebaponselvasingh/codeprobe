import { create } from 'zustand';
import type { ReviewPhase, AgentStatus, FullReport, SSEEvent } from '../types/review';
import { API_BASE } from '../constants/config';

interface ProgressMessage {
  agent: string;
  message: string;
  timestamp: number;
}

interface CodeViewerState {
  isOpen: boolean;
  filePath: string | null;
  fileContent: string | null;
  language: string;
  annotations: Array<{ line: number; severity: string; message: string }>;
  activeFindingIndex: number;
}

interface UploadState {
  mode: 'combined' | 'separate';
  combinedZip: File | null;
  frontendZip: File | null;
  backendZip: File | null;
  problemStatement: string;
  studentName: string;
  projectId: string;
  profileId: string;
  rubricId: string | null;
}

interface ReviewStore {
  phase: ReviewPhase;
  sessionId: string | null;
  quickMode: boolean;
  uploads: UploadState;
  progress: {
    currentAgent: string;
    currentPhase: number;
    messages: ProgressMessage[];
    agentStatuses: Record<string, AgentStatus>;
  };
  partialResults: Record<string, unknown>;
  report: FullReport | null;
  codeViewer: CodeViewerState;
  error: string | null;
  _es: EventSource | null;

  setUploadField: <K extends keyof UploadState>(field: K, value: UploadState[K]) => void;
  setQuickMode: (enabled: boolean) => void;
  startReview: () => Promise<void>;
  handleSSEEvent: (event: SSEEvent) => void;
  cancelReview: () => Promise<void>;
  openCodeViewer: (filePath: string, annotations?: CodeViewerState['annotations']) => Promise<void>;
  closeCodeViewer: () => void;
  navigateFinding: (direction: 'next' | 'prev') => void;
  reset: () => void;
}

const defaultProgress = {
  currentAgent: '',
  currentPhase: 1,
  messages: [] as ProgressMessage[],
  agentStatuses: {} as Record<string, AgentStatus>,
};

const defaultCodeViewer: CodeViewerState = {
  isOpen: false,
  filePath: null,
  fileContent: null,
  language: 'text',
  annotations: [],
  activeFindingIndex: 0,
};

const defaultUploads: UploadState = {
  mode: 'combined',
  combinedZip: null,
  frontendZip: null,
  backendZip: null,
  problemStatement: '',
  studentName: '',
  projectId: '',
  profileId: 'bootcamp',
  rubricId: null,
};

export const useReviewStore = create<ReviewStore>()((set, get) => ({
  phase: 'idle',
  sessionId: null,
  quickMode: false,
  uploads: { ...defaultUploads },
  progress: { ...defaultProgress },
  partialResults: {},
  report: null,
  codeViewer: { ...defaultCodeViewer },
  error: null,
  _es: null,

  setUploadField: (field, value) =>
    set(s => ({ uploads: { ...s.uploads, [field]: value } })),

  setQuickMode: (enabled) => set({ quickMode: enabled }),

  startReview: async () => {
    const { uploads, quickMode } = get();
    if (!uploads.combinedZip && !uploads.frontendZip && !uploads.backendZip) return;

    set({ phase: 'uploading', error: null });

    const form = new FormData();
    if (uploads.mode === 'combined' && uploads.combinedZip) {
      form.append('combined_zip', uploads.combinedZip);
    } else {
      if (uploads.frontendZip) form.append('frontend_zip', uploads.frontendZip);
      if (uploads.backendZip) form.append('backend_zip', uploads.backendZip);
    }
    if (uploads.problemStatement) form.append('problem_statement', uploads.problemStatement);
    form.append('profile_id', uploads.profileId);
    if (uploads.rubricId) form.append('rubric_id', uploads.rubricId);
    if (uploads.studentName) form.append('student_name', uploads.studentName);
    if (uploads.projectId) form.append('project_id', uploads.projectId);
    if (quickMode) form.append('quick_mode', 'true');

    try {
      const res = await fetch(`${API_BASE}/review`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      const { session_id } = await res.json();

      set({
        sessionId: session_id,
        phase: 'reviewing',
        progress: { ...defaultProgress },
      });

      // Open SSE stream
      const es = new EventSource(`${API_BASE}/review/${session_id}/stream`);
      set({ _es: es });

      es.onmessage = (e) => {
        try {
          const event: SSEEvent = JSON.parse(e.data);
          get().handleSSEEvent(event);
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        es.close();
        set({ _es: null });
      };
    } catch (err) {
      set({ phase: 'error', error: err instanceof Error ? err.message : String(err) });
    }
  },

  handleSSEEvent: (event) => {
    if (event.type === 'ping') return;

    set(s => {
      if (event.type === 'progress' && event.agent) {
        const newStatuses = { ...s.progress.agentStatuses, [event.agent]: 'running' as const };
        const newMessages = event.message
          ? [...s.progress.messages, { agent: event.agent, message: event.message, timestamp: Date.now() }]
          : s.progress.messages;
        return {
          progress: {
            ...s.progress,
            currentAgent: event.agent,
            currentPhase: event.phase ?? s.progress.currentPhase,
            agentStatuses: newStatuses,
            messages: newMessages,
          },
        };
      }

      if (event.type === 'result' && event.agent) {
        const newStatuses = { ...s.progress.agentStatuses, [event.agent]: 'done' as const };
        return {
          progress: { ...s.progress, agentStatuses: newStatuses },
          partialResults: { ...s.partialResults, [event.agent]: event.data },
        };
      }

      if (event.type === 'report' && event.data) {
        return { report: event.data as FullReport };
      }

      if (event.type === 'error') {
        const newStatuses = event.agent
          ? { ...s.progress.agentStatuses, [event.agent]: 'error' as const }
          : s.progress.agentStatuses;
        if (event.fatal) {
          s._es?.close();
          return {
            phase: 'error' as const,
            error: event.message ?? 'Unknown error',
            _es: null,
            progress: { ...s.progress, agentStatuses: newStatuses },
          };
        }
        return { progress: { ...s.progress, agentStatuses: newStatuses } };
      }

      if (event.type === 'complete') {
        s._es?.close();
        return { phase: 'complete' as const, _es: null };
      }

      return {};
    });

    // After "complete", if no report yet fetch it
    if (event.type === 'complete' && !get().report) {
      const sessionId = get().sessionId;
      if (sessionId) {
        fetch(`${API_BASE}/review/${sessionId}/report`)
          .then(r => r.json())
          .then(report => set({ report, phase: 'complete' }))
          .catch(() => {});
      }
    }
  },

  cancelReview: async () => {
    const { sessionId, _es } = get();
    _es?.close();
    if (sessionId) {
      try {
        await fetch(`${API_BASE}/review/${sessionId}/cancel`, { method: 'POST' });
      } catch {
        // ignore
      }
    }
    set({ phase: 'idle', _es: null, sessionId: null });
  },

  openCodeViewer: async (filePath, annotations = []) => {
    const { sessionId } = get();
    if (!sessionId) return;
    try {
      const res = await fetch(`${API_BASE}/review/${sessionId}/file/${filePath}`);
      const data = await res.json();
      set({
        codeViewer: {
          isOpen: true,
          filePath,
          fileContent: data.content,
          language: data.language,
          annotations,
          activeFindingIndex: 0,
        },
      });
    } catch {
      // ignore
    }
  },

  closeCodeViewer: () =>
    set({ codeViewer: { ...defaultCodeViewer } }),

  navigateFinding: (direction) =>
    set(s => {
      const total = s.codeViewer.annotations.length;
      if (!total) return {};
      const next = direction === 'next'
        ? (s.codeViewer.activeFindingIndex + 1) % total
        : (s.codeViewer.activeFindingIndex - 1 + total) % total;
      return { codeViewer: { ...s.codeViewer, activeFindingIndex: next } };
    }),

  reset: () => {
    get()._es?.close();
    set({
      phase: 'idle',
      sessionId: null,
      error: null,
      report: null,
      _es: null,
      uploads: { ...defaultUploads },
      progress: { ...defaultProgress },
      partialResults: {},
      codeViewer: { ...defaultCodeViewer },
    });
  },
}));
