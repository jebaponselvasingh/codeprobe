import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, X, FileArchive, Users } from 'lucide-react';
import { useBatchStore } from '../../stores/batchStore';
import { useUiStore } from '../../stores/uiStore';

const PROFILES = [
  { id: 'beginner',   label: 'Beginner Friendly' },
  { id: 'bootcamp',   label: 'Bootcamp Standard' },
  { id: 'production', label: 'Production Ready' },
  { id: 'interview',  label: 'Interview Prep' },
  { id: 'hackathon',  label: 'Hackathon' },
  { id: 'enterprise', label: 'Enterprise' },
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

function BatchDropZone({ onDrop }: { onDrop: (files: File[]) => void }) {
  const onDropAccepted = useCallback((accepted: File[]) => {
    onDrop(accepted);
  }, [onDrop]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop: onDropAccepted,
    accept: { 'application/zip': ['.zip'] },
    multiple: true,
  });

  const borderColor = isDragReject
    ? 'var(--accent-red)'
    : isDragActive
    ? 'var(--accent-blue)'
    : 'var(--border)';

  return (
    <div
      {...getRootProps()}
      className="flex flex-col items-center justify-center gap-3 p-8 rounded-xl cursor-pointer transition-all"
      style={{
        border: `2px dashed ${borderColor}`,
        background: isDragActive ? 'rgba(79,143,247,0.05)' : 'var(--bg-secondary)',
      }}
    >
      <input {...getInputProps()} />
      <UploadCloud size={32} style={{ color: isDragActive ? 'var(--accent-blue)' : 'var(--text-muted)' }} />
      <div className="text-center">
        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
          Drop student zip files here
        </p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
          Select multiple .zip files at once · Each file = one student
        </p>
      </div>
    </div>
  );
}

export function BatchUploadPage() {
  const {
    students,
    phase,
    problemStatement,
    profileId,
    concurrencyLimit,
    addStudentFiles,
    setStudentName,
    removeStudent,
    setProblemStatement,
    setProfileId,
    setConcurrencyLimit,
    startBatchReview,
  } = useBatchStore();
  const { showToast, navigate } = useUiStore();

  const handleSubmit = async () => {
    if (students.length === 0) {
      showToast('Add at least one student zip file', 'error');
      return;
    }
    navigate('batch');
    await startBatchReview();
  };

  return (
    <div className="max-w-3xl mx-auto py-8 flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Users size={24} style={{ color: 'var(--accent-blue)' }} />
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
          Batch Review
        </h1>
      </div>

      {/* Drop zone */}
      <div className="card">
        <p className="text-xs font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>UPLOAD STUDENT ZIPS</p>
        <BatchDropZone onDrop={addStudentFiles} />
      </div>

      {/* Student list */}
      {students.length > 0 && (
        <div className="card flex flex-col gap-2">
          <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
            STUDENTS ({students.length})
          </p>
          {students.map((s, i) => (
            <div
              key={i}
              className="flex items-center gap-3 p-3 rounded-lg"
              style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
            >
              <FileArchive size={16} style={{ color: 'var(--accent-blue)', flexShrink: 0 }} />
              <span
                className="text-xs truncate"
                style={{ color: 'var(--text-muted)', minWidth: 0, maxWidth: 160, flexShrink: 0 }}
                title={s.file.name}
              >
                {s.file.name}
              </span>
              <input
                type="text"
                value={s.name}
                onChange={e => setStudentName(i, e.target.value)}
                placeholder="Student name"
                style={{
                  ...inputStyle,
                  flex: 1,
                  padding: '4px 10px',
                  fontSize: 13,
                }}
              />
              <button
                onClick={() => removeStudent(i)}
                className="flex-shrink-0 hover:opacity-70 transition-opacity"
                style={{ color: 'var(--text-muted)' }}
                title="Remove"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Config */}
      <div className="card flex flex-col gap-4">
        <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>CONFIGURATION</p>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Profile</label>
            <select
              value={profileId}
              onChange={e => setProfileId(e.target.value)}
              style={{ ...inputStyle, cursor: 'pointer' }}
            >
              {PROFILES.map(p => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>
              Concurrency Limit
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={concurrencyLimit}
              onChange={e => setConcurrencyLimit(Number(e.target.value))}
              style={inputStyle}
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-medium mb-2 block" style={{ color: 'var(--text-secondary)' }}>
            PROBLEM STATEMENT <span style={{ color: 'var(--text-muted)' }}>(optional)</span>
          </label>
          <textarea
            rows={4}
            placeholder="Paste the assignment or problem statement here..."
            value={problemStatement}
            onChange={e => setProblemStatement(e.target.value)}
            style={{ ...inputStyle, resize: 'vertical' }}
          />
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={students.length === 0 || phase === 'uploading'}
        className="flex items-center justify-center gap-2 py-4 rounded-xl font-semibold text-sm transition-all"
        style={{
          background: students.length > 0 ? 'var(--accent-blue)' : 'var(--bg-card)',
          color: students.length > 0 ? '#fff' : 'var(--text-muted)',
          cursor: students.length > 0 && phase !== 'uploading' ? 'pointer' : 'not-allowed',
          opacity: phase === 'uploading' ? 0.7 : 1,
        }}
      >
        <Users size={18} />
        {phase === 'uploading'
          ? 'Uploading...'
          : `Start Batch Review (${students.length} student${students.length !== 1 ? 's' : ''})`}
      </button>
    </div>
  );
}
