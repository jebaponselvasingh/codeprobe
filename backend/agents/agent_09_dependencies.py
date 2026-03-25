import asyncio
import json
import re
from typing import Any, Dict, List
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json
from guardrails.schemas import DependencyLLMOutput


# Known problematic frontend packages
ABANDONED_FE = {
    "moment": ("abandoned", "high", "Replace with date-fns or Day.js — moment is in maintenance mode"),
    "request": ("abandoned", "high", "request is deprecated; use axios, node-fetch, or native fetch"),
    "node-uuid": ("abandoned", "medium", "node-uuid is deprecated; use the 'uuid' package instead"),
    "underscore": ("abandoned", "medium", "underscore is largely superseded by lodash or native ES6+"),
    "bower": ("abandoned", "medium", "bower is deprecated; use npm/yarn instead"),
}

# Known problematic backend packages
DEPRECATED_BE = {
    "python-jose": ("deprecated", "high", "python-jose has unresolved CVEs; migrate to PyJWT"),
    "Flask-JWT": ("deprecated", "high", "Flask-JWT is unmaintained; use flask-jwt-extended"),
}

# Duplicate functionality pairs (if both present, flag)
DUPLICATE_PAIRS = [
    (("axios", "isomorphic-fetch"), "duplicate", "medium",
     "Both axios and a custom fetch wrapper detected — pick one HTTP client"),
    (("lodash", "underscore"), "duplicate", "low",
     "Both lodash and underscore present — consolidate to one utility library"),
]

# License red flags
LICENSE_RED_FLAGS = re.compile(r'"license"\s*:\s*"(GPL|AGPL)', re.IGNORECASE)


class DependencyAgent(AgentBase):
    agent_id = "dependencies"
    agent_name = "Dependency Auditor"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Auditing project dependencies...")

        config_files = state.get("config_files", {})

        # 1. Parse package.json
        fe_deps: Dict[str, str] = {}
        fe_dev_deps: Dict[str, str] = {}
        pkg_json_raw = ""
        for path, entry in config_files.items():
            if path.endswith("package.json") and "node_modules" not in path:
                content = entry.get("content", "")
                if content:
                    pkg_json_raw = content
                    try:
                        pkg = json.loads(content)
                        fe_deps = pkg.get("dependencies", {}) or {}
                        fe_dev_deps = pkg.get("devDependencies", {}) or {}
                    except Exception:
                        pass
                break

        # 2. Parse requirements.txt
        be_deps: List[str] = []
        requirements_raw = ""
        for path, entry in config_files.items():
            if "requirements" in path.lower() and path.endswith(".txt"):
                content = entry.get("content", "")
                if content:
                    requirements_raw = content
                    for line in content.splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            be_deps.append(line)
                break

        fe_dep_count = len(fe_deps)
        be_dep_count = len(be_deps)

        static_concerns = self._static_analysis(fe_deps, fe_dev_deps, be_deps, config_files)

        self.emit(
            queue,
            "progress",
            f"Dependency audit: {fe_dep_count} FE deps, {be_dep_count} BE deps, "
            f"{len(static_concerns)} static concerns found",
        )

        # 3. LLM analysis
        llm_concerns = await self._llm_analysis(pkg_json_raw, requirements_raw, queue)

        # Merge (deduplicate by package name)
        seen_packages = {c["package"] for c in static_concerns}
        for concern in llm_concerns:
            if isinstance(concern, dict) and concern.get("package") not in seen_packages:
                static_concerns.append(concern)
                seen_packages.add(concern.get("package", ""))

        all_concerns = static_concerns

        # Compute score
        high_count = sum(1 for c in all_concerns if c.get("severity") == "high")
        medium_count = sum(1 for c in all_concerns if c.get("severity") == "medium")
        score = 10.0 - (high_count * 2 + medium_count * 0.5)
        score = round(max(0.0, min(10.0, score)), 2)

        # Build findings
        findings: List[Dict] = []
        for concern in all_concerns:
            sev = concern.get("severity", "low")
            findings.append({
                "type": "error" if sev == "high" else "suggestion",
                "area": "Dependencies",
                "detail": f"{concern.get('package', 'unknown')}: {concern.get('suggestion', '')}",
                "file": "package.json" if concern.get("concern_type") in ("abandoned", "deprecated", "duplicate", "license", "version") else "",
                "fix_hint": concern.get("suggestion", ""),
            })

        self.emit(queue, "result", data={"score": score})

        return {
            **state,
            "dependency_audit": {
                "fe_dep_count": fe_dep_count,
                "be_dep_count": be_dep_count,
                "concerns": all_concerns,
                "findings": findings,
                "dependency_score": score,
            },
        }

    def _static_analysis(
        self,
        fe_deps: Dict[str, str],
        fe_dev_deps: Dict[str, str],
        be_deps: List[str],
        config_files: Dict[str, Any],
    ) -> List[Dict]:
        concerns: List[Dict] = []
        all_fe = {**fe_deps, **fe_dev_deps}

        # Abandoned FE packages
        for pkg_name, (ctype, sev, suggestion) in ABANDONED_FE.items():
            if pkg_name in all_fe:
                concerns.append({
                    "package": pkg_name,
                    "concern_type": ctype,
                    "severity": sev,
                    "suggestion": suggestion,
                })

        # Deprecated BE packages
        be_pkg_names = [re.split(r"[>=<!~\[]", dep)[0].strip() for dep in be_deps]
        for pkg_name, (ctype, sev, suggestion) in DEPRECATED_BE.items():
            if pkg_name in be_pkg_names:
                concerns.append({
                    "package": pkg_name,
                    "concern_type": ctype,
                    "severity": sev,
                    "suggestion": suggestion,
                })

        # Duplicate functionality
        for pair, ctype, sev, suggestion in DUPLICATE_PAIRS:
            if all(p in all_fe for p in pair):
                concerns.append({
                    "package": " + ".join(pair),
                    "concern_type": ctype,
                    "severity": sev,
                    "suggestion": suggestion,
                })

        # License red flags — scan all config files
        for path, entry in config_files.items():
            content = entry.get("content", "")
            if content and LICENSE_RED_FLAGS.search(content):
                concerns.append({
                    "package": path,
                    "concern_type": "license",
                    "severity": "high",
                    "suggestion": f"GPL/AGPL license detected in {path} — verify compatibility with your project license",
                })

        # Version pinning issues: * or latest
        unpinned = [
            pkg for pkg, ver in fe_deps.items()
            if isinstance(ver, str) and (ver == "*" or ver == "latest")
        ]
        if unpinned:
            concerns.append({
                "package": ", ".join(unpinned[:5]),
                "concern_type": "version",
                "severity": "medium",
                "suggestion": "Pin dependency versions to avoid unexpected breaking changes on install",
            })

        # Excessive production deps (> 30)
        if len(fe_deps) > 30:
            concerns.append({
                "package": "package.json",
                "concern_type": "version",
                "severity": "low",
                "suggestion": f"Excessive production dependencies ({len(fe_deps)}): audit and remove unused packages",
            })

        return concerns

    async def _llm_analysis(
        self, pkg_json_raw: str, requirements_raw: str, queue: asyncio.Queue
    ) -> List[Dict]:
        self.emit(queue, "progress", "Running LLM dependency analysis...")

        if not pkg_json_raw and not requirements_raw:
            return []

        content_parts = []
        if pkg_json_raw:
            content_parts.append(f"--- package.json ---\n{pkg_json_raw[:2000]}")
        if requirements_raw:
            content_parts.append(f"--- requirements.txt ---\n{requirements_raw[:1000]}")

        combined = "\n\n".join(content_parts)

        prompt = f"""Review these frontend and backend dependencies. Identify: outdated packages with known CVEs, abandoned projects, packages with lighter alternatives, and any security concerns. Return ONLY valid JSON: {{"concerns": [{{"package": "string", "concern_type": "abandoned|deprecated|duplicate|license|version", "severity": "high|medium|low", "suggestion": "string"}}], "overall_health": "good|fair|poor", "dependency_score": 0.0}}

{combined}"""

        try:
            response = await ollama_chat(prompt, timeout=180)
            if not response:
                return []
            parsed = parse_llm_json(response, default=None)
            if not parsed or not isinstance(parsed, dict):
                return []
            validated = self.validate_output(parsed, DependencyLLMOutput, queue)
            concerns = validated.get("concerns", [])
            return [c if isinstance(c, dict) else c.model_dump() if hasattr(c, "model_dump") else {}
                    for c in concerns]
        except Exception as e:
            self.emit(queue, "progress", f"LLM dependency analysis failed: {e}")
            return []
