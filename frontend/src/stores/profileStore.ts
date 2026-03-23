import { create } from 'zustand';
import { API_BASE } from '../constants/config';

interface RubricCategory {
  name: string;
  weight: number;
  min_expectations: string;
}

interface Profile {
  id: string;
  name: string;
  description: string;
  is_builtin: boolean;
  strictness?: string;
  skip_agents?: string[];
  llm_tone?: string;
  scoring_weights?: Record<string, number>;
}

interface Rubric {
  id: string;
  name: string;
  categories: RubricCategory[];
  created_at?: string;
}

interface ProfileStore {
  profiles: Profile[];
  rubrics: Rubric[];
  selectedProfileId: string;
  selectedRubricId: string | null;
  editingProfile: Partial<Profile> | null;
  editingRubric: Partial<Rubric> | null;
  isLoading: boolean;
  error: string | null;

  fetchProfiles: () => Promise<void>;
  fetchRubrics: () => Promise<void>;
  createProfile: (config: Partial<Profile>) => Promise<void>;
  updateProfile: (id: string, config: Partial<Profile>) => Promise<void>;
  deleteProfile: (id: string) => Promise<void>;
  createRubric: (config: Partial<Rubric>) => Promise<void>;
  updateRubric: (id: string, config: Partial<Rubric>) => Promise<void>;
  deleteRubric: (id: string) => Promise<void>;
  selectProfile: (id: string) => void;
  selectRubric: (id: string | null) => void;
  setEditingProfile: (p: Partial<Profile> | null) => void;
  setEditingRubric: (r: Partial<Rubric> | null) => void;
}

export const useProfileStore = create<ProfileStore>()((set, get) => ({
  profiles: [],
  rubrics: [],
  selectedProfileId: '',
  selectedRubricId: null,
  editingProfile: null,
  editingRubric: null,
  isLoading: false,
  error: null,

  fetchProfiles: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}/api/profiles`);
      const profiles: Profile[] = await res.json();
      set({ profiles });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    } finally {
      set({ isLoading: false });
    }
  },

  fetchRubrics: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}/api/rubrics`);
      const rubrics: Rubric[] = await res.json();
      set({ rubrics });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    } finally {
      set({ isLoading: false });
    }
  },

  createProfile: async (config) => {
    try {
      await fetch(`${API_BASE}/api/profiles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: config.name,
          description: config.description,
          agent_config: {
            skip_agents: config.skip_agents,
            strictness: config.strictness,
          },
          scoring_weights: config.scoring_weights,
          llm_tone: config.llm_tone,
        }),
      });
      await get().fetchProfiles();
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  updateProfile: async (id, config) => {
    try {
      await fetch(`${API_BASE}/api/profiles/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: config.name,
          description: config.description,
          agent_config: {
            skip_agents: config.skip_agents,
            strictness: config.strictness,
          },
          scoring_weights: config.scoring_weights,
          llm_tone: config.llm_tone,
        }),
      });
      await get().fetchProfiles();
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  deleteProfile: async (id) => {
    try {
      await fetch(`${API_BASE}/api/profiles/${id}`, { method: 'DELETE' });
      await get().fetchProfiles();
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  createRubric: async (config) => {
    try {
      await fetch(`${API_BASE}/api/rubrics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      await get().fetchRubrics();
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  updateRubric: async (id, config) => {
    try {
      await fetch(`${API_BASE}/api/rubrics/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      await get().fetchRubrics();
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  deleteRubric: async (id) => {
    try {
      await fetch(`${API_BASE}/api/rubrics/${id}`, { method: 'DELETE' });
      await get().fetchRubrics();
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  selectProfile: (id) => set({ selectedProfileId: id }),
  selectRubric: (id) => set({ selectedRubricId: id }),
  setEditingProfile: (p) => set({ editingProfile: p }),
  setEditingRubric: (r) => set({ editingRubric: r }),
}));
