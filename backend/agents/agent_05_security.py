import asyncio
import re
from typing import Any, Dict, List
from .base import AgentBase
from .graphs.security_graph import run_security_graph

OWASP_CATEGORIES = {
    "A01": "Broken Access Control",
    "A02": "Cryptographic Failures",
    "A03": "Injection",
    "A04": "Insecure Design",
    "A05": "Security Misconfiguration",
    "A06": "Vulnerable Components",
    "A07": "Auth Failures",
    "A08": "Integrity Failures",
    "A09": "Logging Failures",
    "A10": "SSRF",
}

# Severity weights for scoring
SEVERITY_WEIGHTS = {
    "critical": 2.0,
    "high": 1.5,
    "medium": 0.5,
    "low": 0.1,
}


class SecurityAgent(AgentBase):
    agent_id = "security"
    agent_name = "Security Scanner"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Running static security analysis across all files...")

        frontend_files = state.get("frontend_files", {})
        backend_files = state.get("backend_files", {})
        all_files = {**frontend_files, **backend_files}

        if not all_files:
            self.emit(queue, "progress", "No files found, skipping security scan")
            return {
                **state,
                "security_scan": {
                    "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                    "findings": [],
                    "owasp_coverage": {},
                    "security_score": 5.0,
                },
            }

        # --- Static analysis ---
        static_findings = self._static_analysis(all_files)
        severity_counts = self._count_severities(static_findings)

        self.emit(
            queue,
            "progress",
            f"Static security scan complete: {len(static_findings)} issues found "
            f"(critical={severity_counts['critical']}, high={severity_counts['high']}, "
            f"medium={severity_counts['medium']}, low={severity_counts['low']})",
        )

        # --- LLM analysis (via LangGraph subgraph) ---
        llm_context = self.get_llm_context(state)
        combined_content = self._build_combined_content(all_files, static_findings)
        llm_findings, owasp_coverage = await run_security_graph(
            all_files=all_files,
            static_findings=static_findings,
            queue=queue,
            llm_context=llm_context,
            combined_content=combined_content,
        )

        # Merge and deduplicate findings
        all_findings = self._merge_findings(static_findings, llm_findings)
        severity_counts = self._count_severities(all_findings)

        # Compute score
        security_score = self._compute_score(severity_counts)

        # Add to shared findings list
        findings_with_agent = []
        for f in all_findings:
            finding = dict(f)
            finding["agent_id"] = "security"
            findings_with_agent.append(finding)

        existing_all_findings = state.get("_all_findings", [])
        existing_all_findings.extend(findings_with_agent)

        self.emit(queue, "result", data={"score": security_score})

        return {
            **state,
            "_all_findings": existing_all_findings,
            "security_scan": {
                "severity_counts": severity_counts,
                "findings": all_findings,
                "owasp_coverage": owasp_coverage,
                "security_score": security_score,
            },
        }

    def _static_analysis(self, all_files: Dict[str, Any]) -> List[Dict]:
        findings = []

        for file_path, entry in all_files.items():
            content = entry.get("content", "")
            if not content:
                continue

            lines = content.splitlines()
            is_example = ".example" in file_path or ".sample" in file_path

            # 1. Hardcoded secrets
            secret_patterns = [
                (r"sk-[a-zA-Z0-9]{20,}", "critical", "A02", "OpenAI API key exposed"),
                (r"ghp_[a-zA-Z0-9]{36}", "critical", "A02", "GitHub personal access token exposed"),
                (r"AKIA[A-Z0-9]{16}", "critical", "A02", "AWS access key ID exposed"),
                (r"(?i)private_key\s*=", "critical", "A02", "Private key assignment found"),
            ]
            if not is_example:
                secret_patterns.append(
                    (
                        r"(?i)(password|secret|api_key|apikey|token)\s*=\s*['\"][^'\"]{6,}['\"]",
                        "high",
                        "A02",
                        "Hardcoded credential or secret detected",
                    )
                )

            for pattern, severity, owasp, description in secret_patterns:
                for i, line in enumerate(lines, start=1):
                    if re.search(pattern, line):
                        findings.append(
                            self._make_finding(description, file_path, i, severity, owasp, "Move secrets to environment variables")
                        )

            # 2. SQL injection — .py files only
            if file_path.endswith(".py"):
                for i, line in enumerate(lines, start=1):
                    if re.search(r"\.execute\s*\(\s*f['\"]", line):
                        findings.append(
                            self._make_finding(
                                "SQL injection risk: f-string in execute()",
                                file_path, i, "critical", "A03",
                                "Use parameterized queries instead of f-strings",
                            )
                        )

            # 3. XSS — .tsx/.jsx files
            if file_path.endswith((".tsx", ".jsx", ".js", ".ts")):
                for i, line in enumerate(lines, start=1):
                    if "dangerouslySetInnerHTML" in line:
                        findings.append(
                            self._make_finding(
                                "XSS risk: dangerouslySetInnerHTML usage",
                                file_path, i, "high", "A03",
                                "Sanitize HTML with DOMPurify before using dangerouslySetInnerHTML",
                            )
                        )

            # 4. CORS wildcard — .py files
            if file_path.endswith(".py"):
                for i, line in enumerate(lines, start=1):
                    if re.search(r"allow_origins\s*=\s*\[\s*['\*]['\"]?\s*\]", line) or re.search(r'allow_origins\s*=\s*\["?\*"?\]', line):
                        findings.append(
                            self._make_finding(
                                "CORS wildcard allows all origins",
                                file_path, i, "high", "A05",
                                "Restrict allow_origins to specific trusted domains",
                            )
                        )

            # 5. Unprotected routes — .py files
            if file_path.endswith(".py"):
                for i, line in enumerate(lines, start=1):
                    if re.search(r"@(app|router)\.(get|post|put|delete|patch)\s*\(", line):
                        # Check surrounding 3 lines for Depends(
                        context_start = max(0, i - 1)
                        context_end = min(len(lines), i + 3)
                        context = "\n".join(lines[context_start:context_end])
                        if "Depends(" not in context:
                            findings.append(
                                self._make_finding(
                                    "Potentially unprotected route (no Depends() dependency injection found nearby)",
                                    file_path, i, "medium", "A01",
                                    "Add authentication dependency via Depends(get_current_user) or similar",
                                )
                            )

            # 6. Insecure eval/exec/pickle — .py files
            if file_path.endswith(".py"):
                for i, line in enumerate(lines, start=1):
                    if re.search(r"\beval\s*\(|\bexec\s*\(|\bpickle\.loads\s*\(", line):
                        findings.append(
                            self._make_finding(
                                "Insecure function usage: eval/exec/pickle.loads",
                                file_path, i, "critical", "A03",
                                "Avoid eval/exec; use ast.literal_eval or safe alternatives; avoid pickle for untrusted data",
                            )
                        )

            # 7. Path traversal
            for i, line in enumerate(lines, start=1):
                if re.search(r"\.\./", line):
                    findings.append(
                        self._make_finding(
                            "Potential path traversal: '../' in file operation",
                            file_path, i, "high", "A01",
                            "Validate and sanitize file paths; use os.path.abspath and check against allowed base directory",
                        )
                    )

            # 8. Insecure HTTP (not localhost/127.0.0.1), skip comment lines
            if not file_path.endswith((".md", ".txt", ".rst")):
                for i, line in enumerate(lines, start=1):
                    stripped = line.strip()
                    if stripped.startswith(("#", "//", "*", "<!--")):
                        continue
                    if re.search(r"http://(?!localhost|127\.0\.0\.1)", stripped):
                        findings.append(
                            self._make_finding(
                                "Insecure HTTP URL (non-localhost)",
                                file_path, i, "medium", "A05",
                                "Use HTTPS for all external URLs",
                            )
                        )

            # 9. Missing rate limiting on auth endpoints — .py files
            if file_path.endswith(".py"):
                has_rate_limit = bool(
                    re.search(r"slowapi|rate_limit|RateLimiter|limiter", content, re.IGNORECASE)
                )
                for i, line in enumerate(lines, start=1):
                    if re.search(r"['\"/](login|register|auth)['\"/]", line) and re.search(
                        r"@(app|router)\.(get|post|put|delete|patch)", line
                    ):
                        if not has_rate_limit:
                            findings.append(
                                self._make_finding(
                                    "Auth endpoint without rate limiting",
                                    file_path, i, "high", "A07",
                                    "Add rate limiting (e.g., slowapi) to auth endpoints to prevent brute-force attacks",
                                )
                            )

            # 10. Exposed error details
            if file_path.endswith(".py"):
                for i, line in enumerate(lines, start=1):
                    if re.search(r"return.*exception.*detail.*str\s*\(\s*e\s*\)", line, re.IGNORECASE):
                        findings.append(
                            self._make_finding(
                                "Exposed exception details in response",
                                file_path, i, "medium", "A09",
                                "Log exception internally; return generic error messages to clients",
                            )
                        )

        return findings

    def _make_finding(
        self,
        description: str,
        file_path: str,
        line: int,
        severity: str,
        owasp: str,
        fix_hint: str,
    ) -> Dict:
        return {
            "type": "negative",
            "area": "security",
            "detail": description,
            "file": file_path,
            "line": line,
            "fix_hint": fix_hint,
            "severity": severity,
            "owasp": owasp,
        }

    def _count_severities(self, findings: List[Dict]) -> Dict[str, int]:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = f.get("severity", "low")
            if sev in counts:
                counts[sev] += 1
        return counts

    def _compute_score(self, severity_counts: Dict[str, int]) -> float:
        penalty = (
            severity_counts["critical"] * 2
            + severity_counts["high"] * 1.5
            + severity_counts["medium"] * 0.5
            + severity_counts["low"] * 0.1
        )
        score = 10.0 - penalty
        return round(max(0.0, min(10.0, score)), 2)

    def _merge_findings(self, static_findings: List[Dict], llm_findings: List[Dict]) -> List[Dict]:
        """Merge static and LLM findings, deduplicating by file+detail similarity."""
        merged = list(static_findings)
        existing_keys = set()
        for f in static_findings:
            key = (f.get("file", ""), f.get("detail", "")[:40])
            existing_keys.add(key)

        for f in llm_findings:
            key = (f.get("file", ""), f.get("detail", "")[:40])
            if key not in existing_keys:
                merged.append(f)
                existing_keys.add(key)

        return merged

    def _build_combined_content(self, all_files: Dict[str, Any], static_findings: List[Dict]) -> str:
        """Build truncated file content string for the security LangGraph subgraph."""
        flagged_files = set(f.get("file", "") for f in static_findings)
        auth_keywords = re.compile(r"auth|login|user|token|password|security|jwt|session", re.IGNORECASE)

        selected = {
            path: entry for path, entry in all_files.items()
            if path in flagged_files or auth_keywords.search(path)
        }
        if not selected:
            sorted_files = sorted(all_files.items(), key=lambda x: x[1].get("size", 0), reverse=True)
            selected = dict(sorted_files[:5])

        file_sections = []
        total_chars = 0
        max_chars = 5000
        for path, entry in list(selected.items())[:8]:
            content = entry.get("content", "")
            header = f"\n--- {path} ---\n"
            available = max_chars - total_chars - len(header) - 100
            if available <= 0:
                break
            section = header + content[:available]
            file_sections.append(section)
            total_chars += len(section)
            if total_chars >= max_chars:
                break

        return "".join(file_sections)

