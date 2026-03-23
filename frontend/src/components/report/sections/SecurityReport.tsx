import { Badge } from '../../shared/Badge';
import { ShieldAlert } from 'lucide-react';

interface SecurityFinding {
  severity: string;
  area: string;
  detail: string;
  file?: string;
  line?: number;
  fix_hint?: string;
  owasp?: string;
}

interface SecurityScan {
  severity_counts?: { critical?: number; high?: number; medium?: number; low?: number };
  findings?: SecurityFinding[];
  owasp_coverage?: Record<string, string>;
  security_score?: number;
}

const OWASP_LABELS: Record<string, string> = {
  A01: 'Broken Access Control',
  A02: 'Crypto Failures',
  A03: 'Injection',
  A04: 'Insecure Design',
  A05: 'Security Misconfiguration',
  A06: 'Vulnerable Components',
  A07: 'Auth Failures',
  A08: 'Integrity Failures',
  A09: 'Logging Failures',
  A10: 'SSRF',
};

const severityColor = (s: string): 'red' | 'amber' | 'blue' | 'gray' => {
  if (s === 'critical') return 'red';
  if (s === 'high') return 'amber';
  if (s === 'medium') return 'blue';
  return 'gray';
};

interface Props {
  data: SecurityScan;
}

export function SecurityReport({ data }: Props) {
  const counts = data.severity_counts ?? {};
  const findings = data.findings ?? [];
  const owasp = data.owasp_coverage ?? {};

  return (
    <div className="card flex flex-col gap-5">
      <div className="flex items-center gap-2">
        <ShieldAlert size={18} style={{ color: 'var(--accent-red)' }} />
        <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
          Security Report
        </h3>
        {data.security_score !== undefined && (
          <span className="ml-auto text-sm font-bold" style={{ color: 'var(--accent-red)' }}>
            {data.security_score.toFixed(1)} / 10
          </span>
        )}
      </div>

      {/* Severity breakdown */}
      <div className="grid grid-cols-4 gap-3">
        {(['critical', 'high', 'medium', 'low'] as const).map(sev => (
          <div
            key={sev}
            className="rounded-lg p-3 text-center"
            style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
          >
            <div
              className="text-2xl font-bold"
              style={{
                color:
                  sev === 'critical'
                    ? 'var(--accent-red)'
                    : sev === 'high'
                    ? '#f97316'
                    : sev === 'medium'
                    ? 'var(--accent-amber)'
                    : 'var(--text-muted)',
              }}
            >
              {counts[sev] ?? 0}
            </div>
            <div className="text-xs capitalize mt-1" style={{ color: 'var(--text-muted)' }}>
              {sev}
            </div>
          </div>
        ))}
      </div>

      {/* OWASP coverage */}
      {Object.keys(owasp).length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            OWASP TOP 10 COVERAGE
          </p>
          <div className="grid grid-cols-2 gap-1.5">
            {Object.entries(OWASP_LABELS).map(([code, label]) => {
              const status = owasp[code] ?? 'missing';
              return (
                <div
                  key={code}
                  className="flex items-center gap-2 text-xs px-2 py-1.5 rounded"
                  style={{ background: 'var(--bg-secondary)' }}
                >
                  <div
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{
                      background:
                        status === 'covered'
                          ? 'var(--accent-green)'
                          : status === 'partial'
                          ? 'var(--accent-amber)'
                          : 'var(--text-muted)',
                    }}
                  />
                  <span style={{ color: 'var(--text-secondary)' }}>{code}</span>
                  <span className="truncate" style={{ color: 'var(--text-primary)' }}>
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Findings list */}
      {findings.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            FINDINGS
          </p>
          {findings.slice(0, 10).map((f, i) => (
            <div
              key={i}
              className="p-3 rounded-lg text-sm"
              style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
            >
              <div className="flex items-center gap-2 mb-1">
                <Badge color={severityColor(f.severity)}>{f.severity}</Badge>
                {f.owasp && <Badge color="gray">{f.owasp}</Badge>}
                <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                  {f.area}
                </span>
              </div>
              <p style={{ color: 'var(--text-secondary)' }}>{f.detail}</p>
              {f.file && (
                <p className="text-xs mt-1 font-mono" style={{ color: 'var(--accent-blue)' }}>
                  {f.file}
                  {f.line ? `:${f.line}` : ''}
                </p>
              )}
              {f.fix_hint && (
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Fix: {f.fix_hint}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
