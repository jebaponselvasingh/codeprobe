import asyncio
import os
import tempfile
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Set up test DB in temp dir before importing app
os.environ.setdefault("TEST_MODE", "1")

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_python_file():
    return {
        "content": """
def login(username, password):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    result = db.execute(query)
    return result

def calculate(x, y):
    if x > 0:
        if y > 0:
            if x > y:
                return x - y
            else:
                return y - x
    return 0

API_KEY = "sk-1234567890abcdef"
""",
        "language": "python",
    }


@pytest.fixture
def sample_ts_file():
    return {
        "content": """
import React from 'react';

export function Button({ onClick, children }: any) {
  return <button onClick={onClick}>{children}</button>;
}

export const UserCard = ({ user }: any) => {
  const [data, setData] = React.useState(null);
  React.useEffect(() => {
    fetch('/api/user').then(r => r.json()).then(setData);
  });  // Missing deps array
  return <div>{user.name}</div>;
};
""",
        "language": "typescript",
    }


@pytest.fixture
def mock_state_with_files(tmp_path, sample_python_file, sample_ts_file):
    """Full mock pipeline state with sample files."""
    return {
        "session_id": "test-session-001",
        "temp_dir": str(tmp_path),
        "frontend_files": {
            "src/components/Button.tsx": sample_ts_file,
        },
        "backend_files": {
            "app/routes.py": sample_python_file,
        },
        "config_files": {},
        "file_count": 2,
        "structure_analysis": {
            "frameworks": {"frontend": ["React"], "backend": ["FastAPI"]},
            "folder_checks": {
                "frontend": {"has_components": True, "has_hooks": False},
                "backend": {"has_routers": True, "has_models": False},
            },
        },
        "_cancelled_flag": [False],
        "profile_config": {},
        "skip_agents": [],
    }


@pytest.fixture
def mock_ollama_unavailable():
    """Patch ollama_chat to return empty string (simulates Ollama offline)."""
    with patch("utils.ollama.ollama_chat", new_callable=AsyncMock, return_value="") as mock:
        yield mock


@pytest.fixture
def mock_ollama_json():
    """Patch ollama_chat to return a plausible JSON response."""
    response = '{"findings": [], "score": 7.5, "sub_scores": {"hooks": 8.0}}'
    with patch("utils.ollama.ollama_chat", new_callable=AsyncMock, return_value=response) as mock:
        yield mock
