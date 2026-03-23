
import { CheckCircle, XCircle, Clock, SkipForward } from 'lucide-react';
import { AGENTS } from '../../constants/agents';
import type { AgentStatus } from '../../types/review';
import { useReviewStore } from '../../stores/reviewStore';

const PHASE_LABELS: Record<number, string> = {
  1: 'Phase 1 — Setup',
  2: 'Phase 2 — Deep Analysis ⚡ parallel',
  3: 'Phase 3 — Cross-Analysis',
  4: 'Phase 4 — Report',
};

function StatusIcon({ status }: { status: AgentStatus }) {
  if (status === 'done')    return <CheckCircle size={18} style={{ color: 'var(--accent-green)' }} />;
  if (status === 'error')   return <XCircle size={18} style={{ color: 'var(--accent-red)' }} />;
  if (status === 'skipped') return <SkipForward size={18} style={{ color: 'var(--text-muted)' }} />;
  if (status === 'running') return (
    <div className="w-4 h-4 rounded-full border-2 border-t-transparent animate-spin"
      style={{ borderColor: 'var(--accent-blue)', borderTopColor: 'transparent' }} />
  );
  return <Clock size={18} style={{ color: 'var(--text-muted)' }} />;
}

export function AgentTimeline() {
  const { progress } = useReviewStore();
  const { agentStatuses } = progress;

  const phases = [1, 2, 3, 4] as const;

  return (
    <div className="flex flex-col gap-4">
      {phases.map(phase => {
        const agents = AGENTS.filter(a => a.phase === phase);
        return (
          <div key={phase}>
            <p className="text-xs font-semibold mb-2 px-1" style={{ color: 'var(--text-secondary)' }}>
              {PHASE_LABELS[phase]}
            </p>
            <div className={`flex gap-2 ${phase === 2 ? 'flex-wrap' : 'flex-col'}`}>
              {agents.map(agent => {
                const status: AgentStatus = agentStatuses[agent.id] ?? 'pending';
                return (
                  <div
                    key={agent.id}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg"
                    style={{
                      background: status === 'running' ? 'rgba(79,143,247,0.08)' : 'var(--bg-secondary)',
                      border: `1px solid ${status === 'running' ? 'var(--accent-blue)' : 'var(--border)'}`,
                      minWidth: phase === 2 ? 180 : undefined,
                    }}
                  >
                    <StatusIcon status={status} />
                    <span className="text-lg">{agent.icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate" style={{
                        color: status === 'running' ? 'var(--accent-blue)' : 'var(--text-primary)',
                      }}>
                        {agent.name}
                      </p>
                      {status === 'running' && progress.currentAgent === agent.id && progress.messages.length > 0 && (
                        <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                          {progress.messages[progress.messages.length - 1]?.message}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
