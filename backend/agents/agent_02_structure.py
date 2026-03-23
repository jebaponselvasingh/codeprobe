import asyncio
import json
import re
from typing import Any, Dict
from .base import AgentBase


class StructureAgent(AgentBase):
    agent_id = "structure"
    agent_name = "Structure Analyzer"
    phase = 1

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Analyzing project structure...")

        config_files = state.get("config_files", {})
        frontend_files = state.get("frontend_files", {})
        backend_files = state.get("backend_files", {})
        file_tree = state.get("file_tree", [])

        # Parse package.json
        pkg_json_entry = next(
            (v for k, v in config_files.items() if k.endswith("package.json")), None
        )
        fe_frameworks = []
        fe_deps = {}
        if pkg_json_entry:
            try:
                pkg = json.loads(pkg_json_entry["content"])
                all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                fe_deps = all_deps
                if "react" in all_deps:
                    fe_frameworks.append("React")
                if "next" in all_deps:
                    fe_frameworks.append("Next.js")
                if "vue" in all_deps:
                    fe_frameworks.append("Vue")
                if "@angular/core" in all_deps:
                    fe_frameworks.append("Angular")
                if "svelte" in all_deps:
                    fe_frameworks.append("Svelte")
                if "vite" in all_deps:
                    fe_frameworks.append("Vite")
            except Exception:
                pass

        # Parse requirements.txt
        req_entry = next(
            (v for k, v in config_files.items() if k.endswith("requirements.txt")), None
        )
        be_frameworks = []
        be_deps = {}
        if req_entry:
            for line in req_entry["content"].splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                pkg_name = re.split(r"[>=<!~]", line)[0].strip().lower()
                be_deps[pkg_name] = line
            if "fastapi" in be_deps:
                be_frameworks.append("FastAPI")
            if "django" in be_deps:
                be_frameworks.append("Django")
            if "flask" in be_deps:
                be_frameworks.append("Flask")

        # Folder checks
        all_paths = set(entry["path"] for entry in file_tree)

        def has_folder(patterns):
            return any(p in path.lower() for path in all_paths for p in patterns)

        folder_checks = {
            "frontend": {
                "has_components": has_folder(["components/"]),
                "has_pages": has_folder(["pages/", "views/"]),
                "has_hooks": has_folder(["hooks/"]),
                "has_services": has_folder(["services/", "api/"]),
                "has_types": has_folder(["types/", "interfaces/"]),
                "has_utils": has_folder(["utils/", "helpers/"]),
            },
            "backend": {
                "has_routers": has_folder(["routers/", "routes/", "api/"]),
                "has_models": has_folder(["models/"]),
                "has_schemas": has_folder(["schemas/"]),
                "has_services": has_folder(["services/"]),
                "has_tests": has_folder(["tests/", "test_"]),
            },
        }

        # Count lines
        fe_lines = sum(entry["content"].count("\n") for entry in frontend_files.values())
        be_lines = sum(entry["content"].count("\n") for entry in backend_files.values())

        file_stats = {
            "frontend_files": len(frontend_files),
            "backend_files": len(backend_files),
            "frontend_lines": fe_lines,
            "backend_lines": be_lines,
        }

        structure_analysis = {
            "fe_frameworks": fe_frameworks,
            "be_frameworks": be_frameworks,
            "fe_dependencies": fe_deps,
            "be_dependencies": be_deps,
            "folder_checks": folder_checks,
            "file_stats": file_stats,
        }

        self.emit(queue, "progress",
                  f"Detected: {', '.join(fe_frameworks) or 'Unknown FE'} + {', '.join(be_frameworks) or 'Unknown BE'}")
        self.emit(queue, "result", data={"frameworks": fe_frameworks + be_frameworks})

        return {**state, "structure_analysis": structure_analysis}
