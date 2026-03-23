
import { DropZone } from './DropZone';
import { useReviewStore } from '../../stores/reviewStore';
import { useUiStore } from '../../stores/uiStore';
import { Rocket, X, FileArchive, Zap } from 'lucide-react';
import { ProfileSelector } from '../shared/ProfileSelector';
import { RubricSelector } from '../shared/RubricSelector';

export function UploadPage() {
  const { uploads, setUploadField, quickMode, setQuickMode, startReview, phase } = useReviewStore();
  const { showToast } = useUiStore();

  const hasFile = uploads.mode === 'combined'
    ? !!uploads.combinedZip
    : !!(uploads.frontendZip || uploads.backendZip);

  const handleSubmit = async () => {
    if (!hasFile) {
      showToast('Please select at least one zip file', 'error');
      return;
    }
    await startReview();
  };

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

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
        New Code Review
      </h1>

      {/* Mode toggle */}
      <div className="card">
        <p className="text-xs font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>UPLOAD MODE</p>
        <div className="flex gap-2">
          {(['combined', 'separate'] as const).map(m => (
            <button
              key={m}
              onClick={() => setUploadField('mode', m)}
              className="flex-1 py-2 rounded-lg text-sm font-medium transition-all"
              style={{
                background: uploads.mode === m ? 'rgba(79,143,247,0.15)' : 'var(--bg-secondary)',
                color: uploads.mode === m ? 'var(--accent-blue)' : 'var(--text-secondary)',
                border: uploads.mode === m ? '1px solid var(--accent-blue)' : '1px solid var(--border)',
              }}
            >
              {m === 'combined' ? 'Combined Zip' : 'Separate FE + BE'}
            </button>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      <div className="card">
        <DropZone mode={uploads.mode} />
        {/* File previews */}
        {uploads.mode === 'combined' && uploads.combinedZip && (
          <FilePreviewRow file={uploads.combinedZip} onRemove={() => setUploadField('combinedZip', null)} />
        )}
        {uploads.mode === 'separate' && (
          <>
            {uploads.frontendZip && (
              <FilePreviewRow file={uploads.frontendZip} label="FE" onRemove={() => setUploadField('frontendZip', null)} />
            )}
            {uploads.backendZip && (
              <FilePreviewRow file={uploads.backendZip} label="BE" onRemove={() => setUploadField('backendZip', null)} />
            )}
          </>
        )}
      </div>

      {/* Configuration */}
      <div className="card flex flex-col gap-4">
        <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>CONFIGURATION</p>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Profile</label>
            <ProfileSelector value={uploads.profileId} onChange={v => setUploadField('profileId', v)} style={selectStyle} />
          </div>
          <div>
            <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Student Name</label>
            <input
              type="text"
              placeholder="Optional"
              value={uploads.studentName}
              onChange={e => setUploadField('studentName', e.target.value)}
              style={inputStyle}
            />
          </div>
          <div>
            <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Rubric</label>
            <RubricSelector value={uploads.rubricId || null} onChange={v => setUploadField('rubricId', v)} style={selectStyle} />
          </div>
          <div>
            <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Project ID</label>
            <input
              type="text"
              placeholder="e.g. todo-app (for history)"
              value={uploads.projectId}
              onChange={e => setUploadField('projectId', e.target.value)}
              style={inputStyle}
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer text-sm" style={{ color: 'var(--text-secondary)' }}>
              <input
                type="checkbox"
                checked={quickMode}
                onChange={e => setQuickMode(e.target.checked)}
                className="w-4 h-4"
              />
              <Zap size={14} style={{ color: 'var(--accent-amber)' }} />
              Quick Mode
            </label>
          </div>
        </div>
      </div>

      {/* Problem statement */}
      <div className="card">
        <label className="text-xs font-medium mb-2 block" style={{ color: 'var(--text-secondary)' }}>
          PROBLEM STATEMENT <span style={{ color: 'var(--text-muted)' }}>(optional — enables Requirements Validation)</span>
        </label>
        <textarea
          rows={4}
          placeholder="Paste the assignment or problem statement here..."
          value={uploads.problemStatement}
          onChange={e => setUploadField('problemStatement', e.target.value)}
          style={{ ...inputStyle, resize: 'vertical' }}
        />
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!hasFile || phase === 'uploading'}
        className="flex items-center justify-center gap-2 py-4 rounded-xl font-semibold text-sm transition-all"
        style={{
          background: hasFile ? 'var(--accent-blue)' : 'var(--bg-card)',
          color: hasFile ? '#fff' : 'var(--text-muted)',
          cursor: hasFile ? 'pointer' : 'not-allowed',
          opacity: phase === 'uploading' ? 0.7 : 1,
        }}
      >
        <Rocket size={18} />
        {phase === 'uploading' ? 'Uploading...' : 'Start Code Review'}
      </button>
    </div>
  );
}

function FilePreviewRow({ file, label, onRemove }: { file: File; label?: string; onRemove: () => void }) {
  const size = (file.size / 1024 / 1024).toFixed(1);
  return (
    <div
      className="flex items-center gap-3 mt-3 px-3 py-2 rounded-lg text-sm"
      style={{ background: 'var(--bg-primary)', border: '1px solid var(--border)' }}
    >
      <FileArchive size={16} style={{ color: 'var(--accent-blue)' }} />
      {label && <span style={{ color: 'var(--text-muted)' }}>[{label}]</span>}
      <span className="flex-1 truncate" style={{ color: 'var(--text-primary)' }}>{file.name}</span>
      <span style={{ color: 'var(--text-muted)' }}>{size} MB</span>
      <button onClick={onRemove} style={{ color: 'var(--text-muted)' }} className="hover:opacity-70">
        <X size={14} />
      </button>
    </div>
  );
}
