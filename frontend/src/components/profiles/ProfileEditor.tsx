import { useProfileStore } from '../../stores/profileStore';

const AGENTS = [
  { id: 'security', label: 'Security Scanner' },
  { id: 'performance', label: 'Performance Profiler' },
  { id: 'testcoverage', label: 'Test Coverage' },
  { id: 'dependencies', label: 'Dependency Auditor' },
  { id: 'accessibility', label: 'Accessibility Checker' },
  { id: 'documentation', label: 'Documentation Scorer' },
  { id: 'plagiarism', label: 'Plagiarism Detector' },
  { id: 'complexity', label: 'Complexity Analyzer' },
];

const WEIGHT_CATEGORIES = [
  'code_quality',
  'security',
  'architecture',
  'frontend',
  'backend',
  'testing',
  'performance',
  'documentation',
  'accessibility',
  'originality',
  'requirements',
];

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  padding: '8px 12px',
  color: 'var(--text-primary)',
  fontSize: 14,
  width: '100%',
  outline: 'none',
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  cursor: 'pointer',
};

export function ProfileEditor() {
  const { editingProfile, setEditingProfile, createProfile, updateProfile, deleteProfile } = useProfileStore();

  if (!editingProfile) return null;

  const isBuiltin = editingProfile.is_builtin === true;
  const isNew = !editingProfile.id;
  const skipAgents = editingProfile.skip_agents ?? [];
  const weights = editingProfile.scoring_weights ?? {};

  const update = (patch: Record<string, unknown>) => {
    setEditingProfile({ ...editingProfile, ...patch });
  };

  const toggleAgent = (agentId: string) => {
    const current = skipAgents.slice();
    if (current.includes(agentId)) {
      update({ skip_agents: current.filter(a => a !== agentId) });
    } else {
      update({ skip_agents: [...current, agentId] });
    }
  };

  const setWeight = (category: string, value: number) => {
    update({ scoring_weights: { ...weights, [category]: value } });
  };

  const totalWeight = Object.values(weights).reduce((s, v) => s + v, 0);
  const weightValid = Math.abs(totalWeight - 1.0) < 0.05;

  const handleSave = async () => {
    if (isBuiltin) return;
    if (isNew) {
      await createProfile(editingProfile);
    } else {
      await updateProfile(editingProfile.id!, editingProfile);
    }
  };

  const handleDelete = async () => {
    if (!editingProfile.id || isBuiltin) return;
    if (!window.confirm(`Delete profile "${editingProfile.name}"?`)) return;
    await deleteProfile(editingProfile.id);
    setEditingProfile(null);
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Basic fields */}
      <div className="flex flex-col gap-3">
        <div>
          <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Name</label>
          <input
            type="text"
            value={editingProfile.name ?? ''}
            onChange={e => update({ name: e.target.value })}
            disabled={isBuiltin}
            style={inputStyle}
          />
        </div>
        <div>
          <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Description</label>
          <textarea
            rows={2}
            value={editingProfile.description ?? ''}
            onChange={e => update({ description: e.target.value })}
            disabled={isBuiltin}
            style={{ ...inputStyle, resize: 'vertical' }}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Strictness</label>
            <select
              value={editingProfile.strictness ?? 'moderate'}
              onChange={e => update({ strictness: e.target.value })}
              disabled={isBuiltin}
              style={selectStyle}
            >
              <option value="lenient">Lenient</option>
              <option value="moderate">Moderate</option>
              <option value="strict">Strict</option>
              <option value="very_strict">Very Strict</option>
            </select>
          </div>
          <div>
            <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>LLM Tone</label>
            <input
              type="text"
              value={editingProfile.llm_tone ?? ''}
              onChange={e => update({ llm_tone: e.target.value })}
              disabled={isBuiltin}
              placeholder="e.g. encouraging, direct"
              style={inputStyle}
            />
          </div>
        </div>
      </div>

      {/* Agent toggles */}
      <div>
        <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>ENABLED AGENTS</p>
        <div className="grid grid-cols-2 gap-2">
          {AGENTS.map(agent => {
            const enabled = !skipAgents.includes(agent.id);
            return (
              <label
                key={agent.id}
                className="flex items-center gap-2 cursor-pointer text-sm px-3 py-2 rounded-lg"
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  opacity: isBuiltin ? 0.6 : 1,
                }}
              >
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={() => !isBuiltin && toggleAgent(agent.id)}
                  disabled={isBuiltin}
                  className="w-4 h-4"
                />
                {agent.label}
              </label>
            );
          })}
        </div>
      </div>

      {/* Weight sliders */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>SCORING WEIGHTS</p>
          <span
            className="text-xs"
            style={{ color: weightValid ? 'var(--accent-green)' : 'var(--accent-red)' }}
          >
            Total: {Math.round(totalWeight * 100)}%
            {!weightValid && Object.keys(weights).length > 0 && ' (must be 100%)'}
          </span>
        </div>
        <div className="flex flex-col gap-2">
          {WEIGHT_CATEGORIES.map(cat => {
            const val = weights[cat] ?? 0;
            return (
              <div key={cat} className="flex items-center gap-3">
                <span
                  className="text-xs w-28 flex-shrink-0 capitalize"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {cat.replace(/_/g, ' ')}
                </span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={val}
                  onChange={e => !isBuiltin && setWeight(cat, Number(e.target.value))}
                  disabled={isBuiltin}
                  className="flex-1"
                />
                <span
                  className="text-xs w-10 text-right flex-shrink-0"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {Math.round(val * 100)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Actions */}
      {isBuiltin ? (
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Built-in profiles cannot be modified.
        </p>
      ) : (
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            className="flex-1 py-2 rounded-lg text-sm font-medium"
            style={{
              background: 'var(--accent-blue)',
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            {isNew ? 'Create Profile' : 'Save Changes'}
          </button>
          {!isNew && (
            <button
              onClick={handleDelete}
              className="px-4 py-2 rounded-lg text-sm font-medium"
              style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                color: 'var(--accent-red)',
                cursor: 'pointer',
              }}
            >
              Delete
            </button>
          )}
        </div>
      )}
    </div>
  );
}
