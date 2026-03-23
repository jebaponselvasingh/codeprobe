import { create } from 'zustand';
import { API_BASE } from '../constants/config';

export interface StudentEntry {
  name: string;
  file: File;
  status: 'pending' | 'reviewing' | 'complete' | 'error';
  currentAgent: string | null;
  score: number | null;
  grade: string | null;
  sessionId: string | null;
}

export interface ComparisonData {
  batch_id: string;
  students: Array<{
    name: string;
    overall_score: number;
    grade: string;
    category_scores: Record<string, { score: number; weight: number }>;
    critical_count: number;
  }>;
  class_stats: {
    mean: number;
    median: number;
    std_dev: number;
    per_category: Record<string, number>;
  };
  common_issues: Array<{ issue: string; frequency: number; affected_students: number }>;
  percentile_ranks: Record<string, number>;
}

interface BatchStore {
  phase: 'idle' | 'uploading' | 'reviewing' | 'complete' | 'error';
  batchId: string | null;
  problemStatement: string;
  profileId: string;
  rubricId: string | null;
  concurrencyLimit: number;
  students: StudentEntry[];
  comparison: ComparisonData | null;
  error: string | null;
  _es: EventSource | null;

  addStudentFiles: (files: File[]) => void;
  setStudentName: (index: number, name: string) => void;
  removeStudent: (index: number) => void;
  setProblemStatement: (v: string) => void;
  setProfileId: (v: string) => void;
  setConcurrencyLimit: (v: number) => void;
  startBatchReview: () => Promise<void>;
  fetchComparison: () => Promise<void>;
  reset: () => void;
}

export const useBatchStore = create<BatchStore>()((set, get) => ({
  phase: 'idle',
  batchId: null,
  problemStatement: '',
  profileId: 'bootcamp',
  rubricId: null,
  concurrencyLimit: 3,
  students: [],
  comparison: null,
  error: null,
  _es: null,

  addStudentFiles: (files) => {
    set(s => {
      const base = s.students.length;
      const newEntries: StudentEntry[] = files.map((file, i) => ({
        name: `Student ${base + i + 1}`,
        file,
        status: 'pending',
        currentAgent: null,
        score: null,
        grade: null,
        sessionId: null,
      }));
      return { students: [...s.students, ...newEntries] };
    });
  },

  setStudentName: (index, name) => {
    set(s => {
      const students = s.students.map((stu, i) => i === index ? { ...stu, name } : stu);
      return { students };
    });
  },

  removeStudent: (index) => {
    set(s => ({ students: s.students.filter((_, i) => i !== index) }));
  },

  setProblemStatement: (v) => set({ problemStatement: v }),
  setProfileId: (v) => set({ profileId: v }),
  setConcurrencyLimit: (v) => set({ concurrencyLimit: v }),

  startBatchReview: async () => {
    const { students, problemStatement, profileId, rubricId } = get();
    if (students.length === 0) return;

    set({ phase: 'uploading', error: null });

    const formData = new FormData();
    students.forEach(s => formData.append('zips', s.file));
    formData.append('student_names', JSON.stringify(students.map(s => s.name)));
    if (problemStatement) formData.append('problem_statement', problemStatement);
    formData.append('profile_id', profileId);
    if (rubricId) formData.append('rubric_id', rubricId);

    try {
      const res = await fetch(`${API_BASE}/review/batch`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      const data = await res.json();
      const batchId: string = data.batch_id;

      set({
        batchId,
        phase: 'reviewing',
        students: get().students.map(s => ({ ...s, status: 'pending' })),
      });

      const es = new EventSource(`${API_BASE}/review/batch/${batchId}/stream`);
      set({ _es: es });

      es.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data as string);
          const type: string = event.type;

          set(s => {
            if (type === 'progress' && typeof event.student_index === 'number') {
              const students = s.students.map((stu, i) =>
                i === event.student_index
                  ? { ...stu, currentAgent: event.agent ?? stu.currentAgent, status: 'reviewing' as const }
                  : stu
              );
              return { students };
            }

            if (type === 'result' && typeof event.student_index === 'number') {
              const students = s.students.map((stu, i) =>
                i === event.student_index
                  ? {
                      ...stu,
                      score: event.data?.overall_score ?? stu.score,
                      grade: event.data?.grade ?? stu.grade,
                    }
                  : stu
              );
              return { students };
            }

            if (type === 'complete' && typeof event.student_index === 'number') {
              const students = s.students.map((stu, i) =>
                i === event.student_index
                  ? { ...stu, status: 'complete' as const, currentAgent: null }
                  : stu
              );
              return { students };
            }

            if (type === 'error' && typeof event.student_index === 'number') {
              const students = s.students.map((stu, i) =>
                i === event.student_index
                  ? { ...stu, status: 'error' as const, currentAgent: null }
                  : stu
              );
              return { students };
            }

            if (type === 'batch_complete') {
              s._es?.close();
              return { phase: 'complete' as const, _es: null };
            }

            return {};
          });
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

  fetchComparison: async () => {
    const { batchId } = get();
    if (!batchId) return;
    try {
      const res = await fetch(`${API_BASE}/review/batch/${batchId}/comparison`);
      if (!res.ok) throw new Error(`Failed to fetch comparison: ${res.status}`);
      const comparison: ComparisonData = await res.json();
      set({ comparison });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  reset: () => {
    get()._es?.close();
    set({
      phase: 'idle',
      batchId: null,
      problemStatement: '',
      profileId: 'bootcamp',
      rubricId: null,
      concurrencyLimit: 3,
      students: [],
      comparison: null,
      error: null,
      _es: null,
    });
  },
}));
