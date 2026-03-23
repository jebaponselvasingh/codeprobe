import { create } from 'zustand';
import { API_BASE } from '../constants/config';

export interface ReviewSummary {
  review_id: string;
  version: number;
  overall_score: number;
  grade: string;
  created_at: string;
  student_name?: string;
}

export interface ProgressData {
  project_id: string;
  versions: Array<{
    version: number;
    grade: string;
    overall_score: number;
    scores_by_category: Record<string, number>;
    date: string;
  }>;
  trends: { improving: string[]; declining: string[]; stable: string[] };
  resolved_issues: string[];
  persistent_issues: string[];
  new_issues: string[];
}

interface HistoryStore {
  reviews: ReviewSummary[];
  selectedProjectId: string | null;
  selectedStudentName: string | null;
  progressData: ProgressData | null;
  selectedReviewId: string | null;
  isLoading: boolean;
  error: string | null;
  page: number;
  total: number;
  limit: number;
  studentNameFilter: string;

  fetchHistory: (projectId: string, page?: number) => Promise<void>;
  fetchStudentHistory: (studentName: string) => Promise<void>;
  fetchProgress: (projectId: string) => Promise<void>;
  selectReview: (reviewId: string) => void;
  deleteReview: (reviewId: string) => Promise<void>;
  setStudentNameFilter: (name: string) => void;
  clearHistory: () => void;
}

export const useHistoryStore = create<HistoryStore>()((set, get) => ({
  reviews: [],
  selectedProjectId: null,
  selectedStudentName: null,
  progressData: null,
  selectedReviewId: null,
  isLoading: false,
  error: null,
  page: 1,
  total: 0,
  limit: 20,
  studentNameFilter: '',

  fetchHistory: async (projectId, page = 1) => {
    set({ isLoading: true, error: null, selectedProjectId: projectId });
    const { studentNameFilter, limit } = get();
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(limit),
      });
      if (studentNameFilter) params.set('student_name', studentNameFilter);
      const res = await fetch(`${API_BASE}/history/${projectId}?${params.toString()}`);
      if (!res.ok) throw new Error(`Failed to fetch history: ${res.status}`);
      const data = await res.json();
      set({
        reviews: data.reviews ?? data,
        total: data.total ?? 0,
        page,
        isLoading: false,
      });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), isLoading: false });
    }
  },

  fetchStudentHistory: async (studentName) => {
    set({ isLoading: true, error: null, selectedStudentName: studentName });
    try {
      const res = await fetch(`${API_BASE}/history/students/${encodeURIComponent(studentName)}`);
      if (!res.ok) throw new Error(`Failed to fetch student history: ${res.status}`);
      const data = await res.json();
      set({ reviews: data.reviews ?? data, isLoading: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), isLoading: false });
    }
  },

  fetchProgress: async (projectId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}/history/${projectId}/progress`);
      if (!res.ok) throw new Error(`Failed to fetch progress: ${res.status}`);
      const progressData: ProgressData = await res.json();
      set({ progressData, isLoading: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), isLoading: false });
    }
  },

  selectReview: (reviewId) => set({ selectedReviewId: reviewId }),

  deleteReview: async (reviewId) => {
    try {
      const res = await fetch(`${API_BASE}/history/${reviewId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`Failed to delete review: ${res.status}`);
      const { selectedProjectId, page } = get();
      if (selectedProjectId) {
        await get().fetchHistory(selectedProjectId, page);
      } else {
        set(s => ({ reviews: s.reviews.filter(r => r.review_id !== reviewId) }));
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  setStudentNameFilter: (name) => {
    set({ studentNameFilter: name });
    const { selectedProjectId } = get();
    if (selectedProjectId) {
      get().fetchHistory(selectedProjectId, 1);
    }
  },

  clearHistory: () => set({
    reviews: [],
    selectedProjectId: null,
    selectedStudentName: null,
    progressData: null,
    selectedReviewId: null,
    error: null,
    page: 1,
    total: 0,
    studentNameFilter: '',
  }),
}));
