import mermaid from 'mermaid';
import { useEffect, useRef, useState } from 'react';
import { API_BASE } from '../../../constants/config';

type DiagramType = 'component_tree' | 'api_flow' | 'data_model' | 'dependency_graph';

const DIAGRAM_TABS: Array<{ type: DiagramType; label: string }> = [
  { type: 'component_tree', label: 'Component Tree' },
  { type: 'api_flow', label: 'API Flow' },
  { type: 'data_model', label: 'Data Model' },
  { type: 'dependency_graph', label: 'Dependencies' },
];

export function ArchitectureDiagram({ sessionId }: { sessionId: string }) {
  const [activeType, setActiveType] = useState<DiagramType>('component_tree');
  const [diagrams, setDiagrams] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({ startOnLoad: false, theme: 'dark' });
  }, []);

  useEffect(() => {
    if (diagrams[activeType]) {
      renderDiagram(diagrams[activeType]);
      return;
    }
    loadDiagram(activeType);
  }, [activeType]);

  const loadDiagram = async (type: DiagramType) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/review/${sessionId}/diagram/${type}`);
      const data = await res.json();
      const code: string = data.mermaid_code;
      setDiagrams(prev => ({ ...prev, [type]: code }));
      renderDiagram(code);
    } catch {
      setError('Failed to generate diagram');
    } finally {
      setLoading(false);
    }
  };

  const renderDiagram = async (code: string) => {
    if (!containerRef.current) return;
    try {
      const id = `diagram-${Date.now()}`;
      const { svg } = await mermaid.render(id, code);
      containerRef.current.innerHTML = svg;
    } catch {
      setError('Failed to render diagram');
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        {DIAGRAM_TABS.map(tab => (
          <button
            key={tab.type}
            onClick={() => setActiveType(tab.type)}
            className="px-3 py-1.5 rounded-lg text-sm"
            style={{
              background: activeType === tab.type ? 'var(--accent-blue)' : 'var(--bg-secondary)',
              color: activeType === tab.type ? '#fff' : 'var(--text-secondary)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Diagram area */}
      {loading && (
        <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Generating diagram...
        </div>
      )}
      {error && (
        <div className="text-sm" style={{ color: '#f87171' }}>
          {error}
        </div>
      )}
      <div
        ref={containerRef}
        className="overflow-auto rounded-lg p-4"
        style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border)',
          minHeight: 192,
        }}
      />
    </div>
  );
}
