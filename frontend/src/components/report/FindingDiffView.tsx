import { useState, useEffect } from 'react';
import ReactDiffViewer from 'react-diff-viewer-continued';
import { X, Loader2 } from 'lucide-react';
import { API_BASE } from '../../constants/config';

interface Props {
  sessionId: string;
  findingId: string;
  file: string;
  line?: number;
  codeSnippet: string;
  description: string;
  onClose: () => void;
}

interface FixResult {
  original_code: string;
  fixed_code: string;
  explanation: string;
}

export function FindingDiffView({
  sessionId,
  findingId,
  file,
  line,
  codeSnippet,
  description,
  onClose,
}: Props) {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<FixResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchFix() {
      setLoading(true);
      setError(null);
      setResult(null);

      try {
        const response = await fetch(
          `${API_BASE}/review/${sessionId}/fix-suggestion`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              finding_id: findingId,
              file,
              line,
              code_snippet: codeSnippet,
              description,
            }),
          }
        );

        if (!response.ok) {
          throw new Error(`Request failed: ${response.status}`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        const accumulated: Partial<FixResult> = {};

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.slice(6)) as {
                  type: 'token' | 'complete' | 'error' | 'result';
                  content?: string;
                  message?: string;
                  original_code?: string;
                  fixed_code?: string;
                  explanation?: string;
                };

                if (event.type === 'result') {
                  if (!cancelled) {
                    setResult({
                      original_code: event.original_code ?? '',
                      fixed_code: event.fixed_code ?? '',
                      explanation: event.explanation ?? '',
                    });
                    setLoading(false);
                  }
                } else if (event.type === 'complete') {
                  if (!cancelled && (accumulated.original_code || accumulated.fixed_code)) {
                    setResult(accumulated as FixResult);
                  }
                  if (!cancelled) setLoading(false);
                } else if (event.type === 'error') {
                  if (!cancelled) {
                    setError(event.message ?? 'An error occurred');
                    setLoading(false);
                  }
                } else if (event.type === 'token' && event.content) {
                  // token streaming — try to parse partial JSON
                  try {
                    const partial = JSON.parse(event.content) as Partial<FixResult>;
                    Object.assign(accumulated, partial);
                  } catch {
                    // not JSON, ignore
                  }
                }
              } catch {
                // ignore parse errors
              }
            }
          }
        }

        if (!cancelled) {
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    }

    fetchFix();
    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, findingId, file]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.6)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-xl overflow-hidden shadow-2xl"
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--color-border)',
        }}
      >
        {/* Modal header */}
        <div
          className="flex items-center justify-between px-5 py-3 flex-shrink-0"
          style={{ borderBottom: '1px solid var(--color-border)' }}
        >
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
              Fix Suggestion
            </h3>
            <p className="text-xs mt-0.5 font-mono truncate" style={{ color: 'var(--accent-blue)' }}>
              {file}{line ? `:${line}` : ''}
            </p>
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 ml-3 flex items-center justify-center w-7 h-7 rounded-md hover:opacity-70 transition-opacity"
            style={{ color: 'var(--text-secondary)' }}
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Modal body */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <Loader2 size={24} className="animate-spin" style={{ color: 'var(--accent-blue)' }} />
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Generating fix suggestion...
              </p>
            </div>
          )}

          {error && !loading && (
            <div
              className="rounded-lg px-4 py-3 text-sm"
              style={{
                background: 'rgba(239,68,68,0.1)',
                border: '1px solid rgba(239,68,68,0.3)',
                color: '#f87171',
              }}
            >
              {error}
            </div>
          )}

          {result && !loading && (
            <div className="flex flex-col gap-4">
              {result.explanation && (
                <div
                  className="rounded-lg px-4 py-3 text-sm"
                  style={{
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                    EXPLANATION
                  </p>
                  {result.explanation}
                </div>
              )}

              <div className="overflow-x-auto rounded-lg" style={{ border: '1px solid var(--color-border)' }}>
                <ReactDiffViewer
                  oldValue={result.original_code}
                  newValue={result.fixed_code}
                  splitView={true}
                  leftTitle="Current Code"
                  rightTitle="Suggested Fix"
                  useDarkTheme={true}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
