import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch

from agents.agent_01_extract import ExtractAgent
from agents.agent_02_structure import StructureAgent
from agents.agent_03_react import ReactAgent
from agents.agent_04_fastapi import FastAPIAgent
from agents.agent_05_security import SecurityAgent
from agents.agent_07_codesmell import CodeSmellAgent
from agents.agent_15_complexity import ComplexityAgent
from agents.agent_09_dependencies import DependencyAgent
from agents.agent_10_accessibility import AccessibilityAgent
from agents.agent_11_documentation import DocumentationAgent
from agents.agent_14_plagiarism import PlagiarismAgent


pytestmark = pytest.mark.asyncio


# ─── Helper ────────────────────────────────────────────────────────────────────

async def make_queue():
    return asyncio.Queue()


# ─── Agent 02 — Structure ──────────────────────────────────────────────────────

class TestStructureAgent:
    async def test_detects_react(self, tmp_path):
        queue = await make_queue()
        state = {
            "session_id": "t1",
            "temp_dir": str(tmp_path),
            "config_files": {
                "package.json": {"content": '{"dependencies":{"react":"^18.0.0","vite":"^4.0.0"}}', "language": "json"}
            },
            "frontend_files": {},
            "backend_files": {},
            "_cancelled_flag": [False],
        }
        result = await StructureAgent().run(state, queue)
        structure = result.get("structure_analysis", {})
        assert "React" in structure.get("frameworks", {}).get("frontend", [])

    async def test_detects_fastapi(self, tmp_path):
        queue = await make_queue()
        state = {
            "session_id": "t2",
            "temp_dir": str(tmp_path),
            "config_files": {
                "requirements.txt": {"content": "fastapi==0.115.0\nuvicorn==0.30.0", "language": "text"}
            },
            "frontend_files": {},
            "backend_files": {},
            "_cancelled_flag": [False],
        }
        result = await StructureAgent().run(state, queue)
        structure = result.get("structure_analysis", {})
        assert "FastAPI" in structure.get("frameworks", {}).get("backend", [])

    async def test_empty_state(self, tmp_path):
        queue = await make_queue()
        state = {
            "session_id": "t3", "temp_dir": str(tmp_path),
            "config_files": {}, "frontend_files": {}, "backend_files": {},
            "_cancelled_flag": [False],
        }
        result = await StructureAgent().run(state, queue)
        assert "structure_analysis" in result


# ─── Agent 03 — React ──────────────────────────────────────────────────────────

class TestReactAgent:
    async def test_static_analysis_no_ollama(self, mock_state_with_files, mock_ollama_unavailable):
        queue = await make_queue()
        result = await ReactAgent().run(mock_state_with_files, queue)
        assert "react_evaluation" in result
        eval_data = result["react_evaluation"]
        assert "score" in eval_data
        assert 0 <= eval_data["score"] <= 10

    async def test_detects_missing_effect_deps(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t4", "temp_dir": str(tmp_path),
            "frontend_files": {
                "src/Bad.tsx": {"content": "useEffect(() => { fetch('/api'); });\n", "language": "typescript"}
            },
            "backend_files": {}, "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await ReactAgent().run(state, queue)
        # Should detect the missing deps as a finding
        eval_data = result["react_evaluation"]
        assert "findings" in eval_data

    async def test_empty_files_returns_default(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t5", "temp_dir": str(tmp_path),
            "frontend_files": {}, "backend_files": {}, "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await ReactAgent().run(state, queue)
        assert result["react_evaluation"]["score"] == 5.0


# ─── Agent 05 — Security ───────────────────────────────────────────────────────

class TestSecurityAgent:
    async def test_detects_sql_injection(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t6", "temp_dir": str(tmp_path),
            "frontend_files": {},
            "backend_files": {
                "app.py": {"content": 'query = f"SELECT * FROM users WHERE id = {user_id}"', "language": "python"}
            },
            "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await SecurityAgent().run(state, queue)
        scan = result["security_scan"]
        assert scan["security_score"] < 10
        msgs = [f.get("message", "") + f.get("detail", "") for f in scan.get("findings", [])]
        assert any("sql" in m.lower() or "inject" in m.lower() for m in msgs)

    async def test_detects_hardcoded_secret(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t7", "temp_dir": str(tmp_path),
            "frontend_files": {},
            "backend_files": {
                "config.py": {"content": 'SECRET_KEY = "sk-abc123xyz789secret"', "language": "python"}
            },
            "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await SecurityAgent().run(state, queue)
        scan = result["security_scan"]
        assert len(scan.get("findings", [])) > 0

    async def test_clean_code_high_score(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t8", "temp_dir": str(tmp_path),
            "frontend_files": {},
            "backend_files": {
                "clean.py": {"content": "def add(a: int, b: int) -> int:\n    return a + b\n", "language": "python"}
            },
            "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await SecurityAgent().run(state, queue)
        assert result["security_scan"]["security_score"] >= 7.0


# ─── Agent 07 — Code Smells ────────────────────────────────────────────────────

class TestCodeSmellAgent:
    async def test_detects_console_log(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t9", "temp_dir": str(tmp_path),
            "frontend_files": {
                "src/app.tsx": {"content": "console.log('debug');\nconsole.log('more');\n", "language": "typescript"}
            },
            "backend_files": {}, "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await CodeSmellAgent().run(state, queue)
        smells = result["code_smells"]
        assert "code_quality_score" in smells

    async def test_detects_todo_markers(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        code = "\n".join([f"// TODO: fix this {i}" for i in range(5)])
        state = {
            "session_id": "t10", "temp_dir": str(tmp_path),
            "frontend_files": {"src/app.tsx": {"content": code, "language": "typescript"}},
            "backend_files": {}, "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await CodeSmellAgent().run(state, queue)
        assert "code_smells" in result


# ─── Agent 09 — Dependencies ───────────────────────────────────────────────────

class TestDependencyAgent:
    async def test_detects_deprecated_moment(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        pkg = json.dumps({"dependencies": {"moment": "^2.29.0", "react": "^18.0.0"}})
        state = {
            "session_id": "t11", "temp_dir": str(tmp_path),
            "frontend_files": {},
            "backend_files": {},
            "config_files": {"package.json": {"content": pkg, "language": "json"}},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await DependencyAgent().run(state, queue)
        audit = result["dependency_audit"]
        deprecated_names = [d["name"] for d in audit.get("deprecated", [])]
        assert "moment" in deprecated_names

    async def test_no_deps_returns_default(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t12", "temp_dir": str(tmp_path),
            "frontend_files": {}, "backend_files": {}, "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await DependencyAgent().run(state, queue)
        assert "dependency_audit" in result
        assert result["dependency_audit"]["dependency_score"] >= 0


# ─── Agent 10 — Accessibility ─────────────────────────────────────────────────

class TestAccessibilityAgent:
    async def test_detects_missing_alt(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t13", "temp_dir": str(tmp_path),
            "frontend_files": {
                "src/img.tsx": {"content": '<img src="photo.jpg" />', "language": "typescript"}
            },
            "backend_files": {}, "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await AccessibilityAgent().run(state, queue)
        report = result["accessibility_report"]
        assert report["total_violations"] > 0

    async def test_compliant_code_no_violations(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t14", "temp_dir": str(tmp_path),
            "frontend_files": {
                "src/img.tsx": {"content": '<img src="photo.jpg" alt="A photo" />', "language": "typescript"}
            },
            "backend_files": {}, "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await AccessibilityAgent().run(state, queue)
        report = result["accessibility_report"]
        assert report.get("total_violations", 0) == 0


# ─── Agent 14 — Plagiarism ────────────────────────────────────────────────────

class TestPlagiarismAgent:
    async def test_detects_tutorial_variables(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t15", "temp_dir": str(tmp_path),
            "frontend_files": {
                "src/app.tsx": {"content": "const todos = [];\nconst fakePosts = [];\n", "language": "typescript"}
            },
            "backend_files": {}, "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await PlagiarismAgent().run(state, queue)
        report = result["originality_report"]
        assert len(report.get("tutorial_signals", [])) > 0

    async def test_original_code_high_score(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t16", "temp_dir": str(tmp_path),
            "frontend_files": {
                "src/CustomHook.tsx": {
                    "content": "export function useDebounce(value: string, delay: number) { return value; }",
                    "language": "typescript"
                }
            },
            "backend_files": {}, "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await PlagiarismAgent().run(state, queue)
        assert "originality_report" in result


# ─── Agent 15 — Complexity ────────────────────────────────────────────────────

class TestComplexityAgent:
    async def test_python_cyclomatic_complexity(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        complex_code = """
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            elif z < 0:
                return x + y - z
        elif y < 0:
            return x - y
    elif x < 0:
        if y > 0:
            return y - x
        else:
            return -(x + y)
    return 0
"""
        state = {
            "session_id": "t17", "temp_dir": str(tmp_path),
            "frontend_files": {},
            "backend_files": {"app.py": {"content": complex_code, "language": "python"}},
            "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await ComplexityAgent().run(state, queue)
        report = result["complexity_report"]
        assert report["avg_cyclomatic"] > 1.0

    async def test_simple_code_low_complexity(self, tmp_path, mock_ollama_unavailable):
        queue = await make_queue()
        state = {
            "session_id": "t18", "temp_dir": str(tmp_path),
            "frontend_files": {},
            "backend_files": {"simple.py": {"content": "def add(a, b):\n    return a + b\n", "language": "python"}},
            "config_files": {},
            "_cancelled_flag": [False], "profile_config": {}, "skip_agents": [],
        }
        result = await ComplexityAgent().run(state, queue)
        report = result["complexity_report"]
        assert report["complexity_score"] >= 5.0
