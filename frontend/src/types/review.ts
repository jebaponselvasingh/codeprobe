export type ReviewPhase = 'idle' | 'uploading' | 'reviewing' | 'complete' | 'error';
export type AgentStatus = 'pending' | 'running' | 'done' | 'error' | 'skipped';

export interface AgentMeta {
  id: string;
  name: string;
  icon: string;
  phase: 1 | 2 | 3 | 4;
  description: string;
}

export interface Finding {
  type: 'negative' | 'suggestion' | 'positive';
  area: string;
  detail: string;
  file?: string;
  line?: number;
  fix_hint?: string;
}

export interface CategoryScore {
  score: number;
  weight: number;
  weighted: number;
}

export interface PriorityAction {
  rank: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  detail: string;
  file?: string;
  estimated_hours: number;
  category: string;
}

export interface FullReport {
  meta: {
    session_id: string;
    student_name?: string;
    project_id?: string;
    version: number;
    profile: string;
    generated_at: string;
    review_duration_seconds: number;
  };
  scores: {
    overall: number;
    grade: string;
    categories: Record<string, CategoryScore>;
  };
  executive_summary: string;
  priority_actions: PriorityAction[];
  findings: {
    critical: Finding[];
    suggestions: Finding[];
    strengths: Finding[];
  };
  agents: Record<string, unknown>;
  learning_path?: {
    weeks: Array<{
      week: number;
      focus: string;
      items: Array<{ day: string; topic: string; why: string; exercise: string; estimated_hours: number }>;
    }>;
    skill_gaps: Record<string, number>;
  };
  code_heatmap?: Array<{ file: string; issue_count: number; severity_sum: number }>;
}

export interface SSEEvent {
  type: 'progress' | 'result' | 'report' | 'error' | 'complete' | 'ping';
  agent?: string;
  phase?: number;
  message?: string;
  data?: unknown;
  fatal?: boolean;
}
