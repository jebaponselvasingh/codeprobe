import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud } from 'lucide-react';
import { useReviewStore } from '../../stores/reviewStore';
import { MAX_ZIP_SIZE_BYTES } from '../../constants/config';

interface DropZoneProps {
  mode: 'combined' | 'separate';
}

function SingleZone({ label, onFile }: { label: string; onFile: (f: File) => void }) {
  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) onFile(accepted[0]);
  }, [onFile]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: { 'application/zip': ['.zip'] },
    maxSize: MAX_ZIP_SIZE_BYTES,
    multiple: false,
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
        flex: 1,
      }}
    >
      <input {...getInputProps()} />
      <UploadCloud size={32} style={{ color: isDragActive ? 'var(--accent-blue)' : 'var(--text-muted)' }} />
      <div className="text-center">
        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
          {label}
        </p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
          Drag & drop or click to browse · .zip · max 50MB
        </p>
      </div>
    </div>
  );
}

export function DropZone({ mode }: DropZoneProps) {
  const { setUploadField } = useReviewStore();

  if (mode === 'separate') {
    return (
      <div className="flex gap-4">
        <SingleZone label="Frontend zip" onFile={f => setUploadField('frontendZip', f)} />
        <SingleZone label="Backend zip" onFile={f => setUploadField('backendZip', f)} />
      </div>
    );
  }

  return (
    <SingleZone label="Drop your project zip here" onFile={f => setUploadField('combinedZip', f)} />
  );
}
