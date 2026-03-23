
import Editor, { type OnMount } from '@monaco-editor/react';
import { useReviewStore } from '../../stores/reviewStore';
import { X, ChevronUp, ChevronDown } from 'lucide-react';
import { useUiStore } from '../../stores/uiStore';

export function CodeViewerPanel() {
  const { codeViewer, closeCodeViewer, navigateFinding } = useReviewStore();
  const { theme } = useUiStore();
  const { isOpen, filePath, fileContent, language, annotations, activeFindingIndex } = codeViewer;

  if (!isOpen) return null;

  const activeAnnotation = annotations[activeFindingIndex];

  const handleMount: OnMount = (editor, monaco) => {
    // Highlight annotation lines
    const decorations = annotations.map(ann => ({
      range: new monaco.Range(ann.line, 1, ann.line, 1),
      options: {
        isWholeLine: true,
        glyphMarginClassName: 'finding-gutter',
        className:
          ann.severity === 'critical' || ann.severity === 'negative'
            ? 'finding-line-critical'
            : 'finding-line-warning',
      },
    }));

    if (editor.createDecorationsCollection) {
      editor.createDecorationsCollection(decorations);
    } else {
      // Fallback for older Monaco versions
      (editor as unknown as { deltaDecorations: (old: string[], next: typeof decorations) => void }).deltaDecorations([], decorations);
    }

    // Jump to active annotation line
    if (activeAnnotation) {
      editor.revealLineInCenter(activeAnnotation.line);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        width: '50%',
        height: '100vh',
        background: 'var(--bg-secondary)',
        borderLeft: '1px solid var(--border)',
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '-8px 0 40px rgba(0,0,0,0.5)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-card)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, fontFamily: 'monospace', color: 'var(--accent-blue)' }}>
            {filePath}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {annotations.length > 0 && (
            <>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {activeFindingIndex + 1} / {annotations.length}
              </span>
              <button
                onClick={() => navigateFinding('prev')}
                style={{ color: 'var(--text-secondary)', padding: '4px' }}
                title="Previous issue"
              >
                <ChevronUp size={16} />
              </button>
              <button
                onClick={() => navigateFinding('next')}
                style={{ color: 'var(--text-secondary)', padding: '4px' }}
                title="Next issue"
              >
                <ChevronDown size={16} />
              </button>
            </>
          )}
          <button
            onClick={closeCodeViewer}
            style={{ color: 'var(--text-secondary)', padding: '4px' }}
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Active annotation tooltip */}
      {activeAnnotation && (
        <div
          style={{
            padding: '8px 16px',
            background: 'rgba(248,113,113,0.1)',
            borderBottom: '1px solid rgba(248,113,113,0.3)',
            fontSize: 12,
            color: 'var(--accent-red)',
          }}
        >
          <strong>Line {activeAnnotation.line}:</strong> {activeAnnotation.message}
        </div>
      )}

      {/* Monaco Editor */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Editor
          value={fileContent ?? ''}
          language={language}
          theme={theme === 'dark' ? 'vs-dark' : 'light'}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            glyphMargin: true,
          }}
          onMount={handleMount}
        />
      </div>
    </div>
  );
}
