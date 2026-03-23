import { useEffect, useRef } from 'react';
import { useReviewStore } from '../../stores/reviewStore';

export function LiveLog() {
  const { progress } = useReviewStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [progress.messages.length]);

  return (
    <div
      className="rounded-lg p-3 font-mono text-xs overflow-y-auto"
      style={{
        background: '#0a0c12',
        border: '1px solid var(--border)',
        height: 160,
        color: '#7ec8a0',
      }}
    >
      {progress.messages.length === 0 && (
        <span style={{ color: 'var(--text-muted)' }}>Waiting for pipeline to start...</span>
      )}
      {progress.messages.map((msg, i) => {
        const t = new Date(msg.timestamp);
        const ts = `${String(t.getHours()).padStart(2,'0')}:${String(t.getMinutes()).padStart(2,'0')}:${String(t.getSeconds()).padStart(2,'0')}`;
        return (
          <div key={i} className="mb-0.5">
            <span style={{ color: '#4a5568' }}>[{ts}]</span>{' '}
            <span style={{ color: '#68d391' }}>{msg.agent}:</span>{' '}
            <span style={{ color: '#7ec8a0' }}>{msg.message}</span>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
