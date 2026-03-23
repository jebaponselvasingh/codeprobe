import { useEffect } from 'react';
import { useProfileStore } from '../../stores/profileStore';
import { ProfileEditor } from './ProfileEditor';
import { RubricEditorModal } from './RubricEditorModal';

export function ProfilesPage() {
  const {
    profiles,
    rubrics,
    editingProfile,
    editingRubric,
    fetchProfiles,
    fetchRubrics,
    setEditingProfile,
    setEditingRubric,
    deleteRubric,
  } = useProfileStore();

  useEffect(() => {
    fetchProfiles();
    fetchRubrics();
  }, []);

  return (
    <div className="max-w-5xl mx-auto py-8 flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
        Review Profiles
      </h1>

      {/* Profiles: list + editor */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left: profile list */}
        <div className="col-span-1 flex flex-col gap-2">
          {profiles.map(p => (
            <button
              key={p.id}
              onClick={() => setEditingProfile(p)}
              className="text-left p-3 rounded-lg border text-sm transition-colors"
              style={{
                background: 'var(--bg-card)',
                border: editingProfile && 'id' in editingProfile && editingProfile.id === p.id
                  ? '1px solid var(--accent-blue)'
                  : '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
            >
              <div className="font-medium">{p.name}</div>
              {p.description && (
                <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-secondary)' }}>
                  {p.description}
                </div>
              )}
              {p.is_builtin && (
                <span className="text-xs mt-1 inline-block" style={{ color: 'var(--text-muted)' }}>
                  Built-in
                </span>
              )}
            </button>
          ))}
          <button
            onClick={() =>
              setEditingProfile({
                name: '',
                description: '',
                skip_agents: [],
                strictness: 'moderate',
                llm_tone: '',
              })
            }
            className="p-3 rounded-lg text-sm text-center transition-colors hover:opacity-80"
            style={{
              border: '1px dashed var(--border)',
              color: 'var(--text-secondary)',
              background: 'transparent',
            }}
          >
            + New Profile
          </button>
        </div>

        {/* Right: editor */}
        <div className="col-span-2">
          {editingProfile ? (
            <div
              className="card flex flex-col gap-4"
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 12, padding: 24 }}
            >
              <ProfileEditor />
            </div>
          ) : (
            <div
              className="flex items-center justify-center h-32 rounded-xl text-sm"
              style={{ border: '1px dashed var(--border)', color: 'var(--text-muted)' }}
            >
              Select a profile to edit
            </div>
          )}
        </div>
      </div>

      {/* Rubrics section */}
      <div className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
          Custom Rubrics
        </h2>

        {rubrics.length === 0 && (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            No custom rubrics yet.
          </p>
        )}

        {rubrics.map(r => (
          <div
            key={r.id}
            className="card flex items-center justify-between"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 16px' }}
          >
            <span className="text-sm" style={{ color: 'var(--text-primary)' }}>
              {r.name}{' '}
              <span style={{ color: 'var(--text-muted)' }}>
                ({r.categories.length} {r.categories.length === 1 ? 'category' : 'categories'})
              </span>
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setEditingRubric(r)}
                className="px-3 py-1.5 rounded-lg text-xs"
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                }}
              >
                Edit
              </button>
              <button
                onClick={() => {
                  if (window.confirm(`Delete rubric "${r.name}"?`)) deleteRubric(r.id);
                }}
                className="px-3 py-1.5 rounded-lg text-xs"
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  color: 'var(--accent-red)',
                  cursor: 'pointer',
                }}
              >
                Delete
              </button>
            </div>
          </div>
        ))}

        <button
          onClick={() => setEditingRubric({ name: '', categories: [] })}
          className="py-3 rounded-xl text-sm"
          style={{
            border: '1px dashed var(--border)',
            color: 'var(--text-secondary)',
            background: 'transparent',
            cursor: 'pointer',
          }}
        >
          + New Rubric
        </button>
      </div>

      {/* Rubric editor modal */}
      {editingRubric && <RubricEditorModal />}
    </div>
  );
}
