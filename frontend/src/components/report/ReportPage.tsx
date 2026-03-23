import { useState, type ReactNode } from 'react';
import { useReviewStore } from '../../stores/reviewStore';
import { OverallScoreCard } from './OverallScoreCard';
import { CategoryScoresGrid } from './CategoryScoresGrid';
import { FindingsPanel } from './FindingsPanel';
import { RotateCcw, ChevronDown, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { SecurityReport } from './sections/SecurityReport';
import { CodeSmellReport } from './sections/CodeSmellReport';
import { ComplexityReport } from './sections/ComplexityReport';
import { PerformanceReport } from './sections/PerformanceReport';
import { TestCoverageReport } from './sections/TestCoverageReport';
import { DependencyReport } from './sections/DependencyReport';
import { AccessibilityReport } from './sections/AccessibilityReport';
import { DocumentationReport } from './sections/DocumentationReport';
import { OriginalityReport } from './sections/OriginalityReport';
import { ArchitectureDiagram } from './sections/ArchitectureDiagram';
import { CodeViewerPanel } from '../codeviewer/CodeViewerPanel';
import { useChatStore } from '../../stores/chatStore';
import { ChatPanel } from '../chat/ChatPanel';
import { LearningPathPanel } from './LearningPathPanel';
import { PriorityActionItems } from './PriorityActionItems';
import { CodeHeatmap } from './CodeHeatmap';
import { ExportPanel } from './ExportPanel';

function AccordionSection({ title, children, defaultOpen = false }: { title: string; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between text-sm font-medium"
        style={{ color: 'var(--text-primary)' }}
      >
        {title}
        <ChevronDown
          size={16}
          style={{
            transform: open ? 'rotate(180deg)' : 'none',
            transition: '0.2s',
            color: 'var(--text-secondary)',
          }}
        />
      </button>
      {open && <div className="mt-4">{children}</div>}
    </div>
  );
}

export function ReportPage() {
  const { report, reset } = useReviewStore();
  const openChat = useChatStore(s => s.openChat);
  const isChatOpen = useChatStore(s => s.isOpen);

  if (!report) return null;

  const { scores, executive_summary, priority_actions, findings, meta } = report;
  const agents = report.agents ?? {};

  const criticalFindings = findings.critical
    .slice(0, 3)
    .map(f => f.detail)
    .filter(Boolean);

  return (
    <>
      <div id="report-export-root" className="max-w-4xl mx-auto flex flex-col gap-6 p-4 sm:p-6">
        {/* Export panel */}
        <ExportPanel report={report} />

        {/* Header row */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Review Report
            </h1>
            {meta.student_name ? (
              <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                {meta.student_name}{meta.project_id ? ` · ${meta.project_id}` : ''} · v{meta.version}
              </p>
            ) : null}
          </div>
          <button
            onClick={reset}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm hover:opacity-80 transition-opacity"
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              color: 'var(--text-secondary)',
            }}
          >
            <RotateCcw size={14} />
            New Review
          </button>
        </div>

        {/* Score + categories */}
        <div className="flex gap-6 flex-wrap">
          <OverallScoreCard
            score={scores.overall}
            grade={scores.grade}
            durationSeconds={meta.review_duration_seconds}
          />
          <CategoryScoresGrid categories={scores.categories} />
        </div>

        {/* Priority actions */}
        {priority_actions && priority_actions.length > 0 && (
          <AccordionSection title="Priority Actions" defaultOpen={true}>
            <PriorityActionItems actions={priority_actions} />
          </AccordionSection>
        )}

        {/* Executive summary */}
        {executive_summary ? (
          <div className="card">
            <p className="text-xs font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>EXECUTIVE SUMMARY</p>
            <div className="prose prose-sm max-w-none text-sm" style={{ color: 'var(--text-primary)' }}>
              <ReactMarkdown>{executive_summary}</ReactMarkdown>
            </div>
          </div>
        ) : null}

        {/* Findings */}
        <FindingsPanel findings={findings} />

        {/* Code heatmap */}
        {report.code_heatmap && report.code_heatmap.length > 0 && (
          <AccordionSection title="Code Heatmap" defaultOpen={false}>
            <CodeHeatmap files={report.code_heatmap} />
          </AccordionSection>
        )}

        {/* Security report */}
        {agents.security != null ? (
          <AccordionSection title="Security Analysis">
            <SecurityReport data={agents.security as Parameters<typeof SecurityReport>[0]['data']} />
          </AccordionSection>
        ) : null}

        {/* Code smell report */}
        {agents.codesmell != null ? (
          <AccordionSection title="Code Quality & Smells">
            <CodeSmellReport data={agents.codesmell as Parameters<typeof CodeSmellReport>[0]['data']} />
          </AccordionSection>
        ) : null}

        {/* Complexity report */}
        {agents.complexity != null ? (
          <AccordionSection title="Complexity Analysis">
            <ComplexityReport data={agents.complexity as Parameters<typeof ComplexityReport>[0]['data']} />
          </AccordionSection>
        ) : null}

        {/* Performance report */}
        {agents.performance_profile != null ? (
          <AccordionSection title="Performance Profile">
            <PerformanceReport data={agents.performance_profile as Parameters<typeof PerformanceReport>[0]['data']} />
          </AccordionSection>
        ) : null}

        {/* Test coverage report */}
        {agents.test_coverage != null ? (
          <AccordionSection title="Test Coverage">
            <TestCoverageReport data={agents.test_coverage as Parameters<typeof TestCoverageReport>[0]['data']} />
          </AccordionSection>
        ) : null}

        {/* Dependency audit */}
        {agents.dependency_audit != null ? (
          <AccordionSection title="Dependency Audit">
            <DependencyReport data={agents.dependency_audit as Parameters<typeof DependencyReport>[0]['data']} />
          </AccordionSection>
        ) : null}

        {/* Accessibility report */}
        {agents.accessibility_report != null ? (
          <AccordionSection title="Accessibility">
            <AccessibilityReport data={agents.accessibility_report as Parameters<typeof AccessibilityReport>[0]['data']} />
          </AccordionSection>
        ) : null}

        {/* Documentation review */}
        {agents.documentation_review != null ? (
          <AccordionSection title="Documentation">
            <DocumentationReport data={agents.documentation_review as Parameters<typeof DocumentationReport>[0]['data']} />
          </AccordionSection>
        ) : null}

        {/* Originality analysis */}
        {agents.originality_report != null ? (
          <AccordionSection title="Originality Analysis">
            <OriginalityReport data={agents.originality_report as Parameters<typeof OriginalityReport>[0]['data']} />
          </AccordionSection>
        ) : null}

        {/* Learning path */}
        {report.learning_path && (
          <AccordionSection title="Learning Path" defaultOpen={false}>
            <LearningPathPanel data={report.learning_path as any} />
          </AccordionSection>
        )}

        {/* Architecture diagrams */}
        <AccordionSection title="Architecture Diagrams" defaultOpen={false}>
          <ArchitectureDiagram sessionId={meta.session_id} />
        </AccordionSection>
      </div>

      {/* Floating "Ask AI" button */}
      <button
        onClick={() => openChat(meta.session_id, criticalFindings)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 rounded-full shadow-lg transition-colors"
        style={{ background: '#2563eb', color: '#ffffff' }}
        onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = '#3b82f6'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = '#2563eb'; }}
      >
        <MessageSquare size={18} />
        <span className="text-sm font-medium">Ask AI</span>
      </button>

      {/* Code viewer panel — rendered outside the max-w container so it can overlay full viewport */}
      <CodeViewerPanel />

      {/* Chat panel */}
      {isChatOpen && <ChatPanel />}
    </>
  );
}
