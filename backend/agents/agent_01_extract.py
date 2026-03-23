import asyncio
import zipfile
import os
import re
from pathlib import Path
from typing import Any, Dict
from .base import AgentBase

SKIP_PATTERNS = {
    "node_modules", "__pycache__", ".git", "dist", "build", "venv",
    ".venv", "env", ".env", ".mypy_cache", ".pytest_cache", "coverage",
    ".next", ".nuxt", "out",
}
SKIP_EXTENSIONS = {
    ".lock", ".whl", ".egg", ".pyc", ".pyo", ".class",
    ".exe", ".dll", ".so", ".dylib", ".png", ".jpg",
    ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf",
    ".eot", ".mp4", ".mp3", ".zip", ".tar", ".gz",
}
FRONTEND_EXTS = {".tsx", ".jsx", ".ts", ".js", ".css", ".scss", ".html", ".vue", ".svelte"}
BACKEND_EXTS = {".py"}
CONFIG_NAMES = {
    "package.json", "requirements.txt", "tsconfig.json", "tsconfig.base.json",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "pyproject.toml", "setup.cfg", "setup.py",
    "vite.config.ts", "vite.config.js", "webpack.config.js",
    ".eslintrc.js", ".eslintrc.json", "prettier.config.js",
    "tailwind.config.js", "tailwind.config.ts",
}

MAX_UNCOMPRESSED_MB = 500
MAX_FILE_COUNT = 2000
MAX_COMPRESSION_RATIO = 100
MAX_FILE_READ_BYTES = 51_200  # 50KB per file


class ExtractAgent(AgentBase):
    agent_id = "extract"
    agent_name = "Extract & Classify"
    phase = 1

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Extracting uploaded zip file(s)...")

        temp_dir = Path(state["temp_dir"])
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)

        zip_paths = state.get("zip_paths", {})
        all_zip_paths = list(zip_paths.values())

        # Extract each zip
        for zip_path_str in all_zip_paths:
            zip_path = Path(zip_path_str)
            if not zip_path.exists():
                continue
            await self._safe_extract(zip_path, files_dir, queue)

        # Walk and classify files
        file_tree = []
        frontend_files = {}
        backend_files = {}
        config_files = {}
        total_files = 0
        limit_reached = False

        for root, dirs, files in os.walk(files_dir):
            if limit_reached:
                break
            # Skip hidden/build dirs in-place
            dirs[:] = [d for d in dirs if d not in SKIP_PATTERNS and not d.startswith(".")]
            for fname in files:
                fpath = Path(root) / fname
                rel = str(fpath.relative_to(files_dir))
                ext = fpath.suffix.lower()
                if ext in SKIP_EXTENSIONS:
                    continue
                total_files += 1
                if total_files > MAX_FILE_COUNT:
                    self.emit(queue, "progress", f"File count limit ({MAX_FILE_COUNT}) reached, skipping remaining files")
                    limit_reached = True
                    break

                size = fpath.stat().st_size
                file_tree.append({"path": rel, "size": size, "extension": ext})

                # Read content
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    if len(content) > MAX_FILE_READ_BYTES:
                        content = content[:MAX_FILE_READ_BYTES] + "\n# [truncated]"
                except Exception:
                    content = ""

                entry = {"path": rel, "content": content, "size": size}

                fname_lower = fname.lower()
                if fname_lower in CONFIG_NAMES or fname_lower.startswith("dockerfile"):
                    config_files[rel] = entry
                elif ext in FRONTEND_EXTS:
                    frontend_files[rel] = entry
                elif ext in BACKEND_EXTS:
                    backend_files[rel] = entry

        fe_count = len(frontend_files)
        be_count = len(backend_files)
        self.emit(queue, "progress",
                  f"Extracted {total_files} files — {fe_count} frontend, {be_count} backend")
        self.emit(queue, "result", data={
            "file_count": total_files,
            "frontend_count": fe_count,
            "backend_count": be_count,
        })

        return {
            **state,
            "file_tree": file_tree,
            "frontend_files": frontend_files,
            "backend_files": backend_files,
            "config_files": config_files,
            "file_count": total_files,
        }

    async def _safe_extract(self, zip_path: Path, dest: Path, queue: asyncio.Queue):
        """Extract zip with bomb protection."""
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                total_uncompressed = 0
                for info in zf.infolist():
                    # Reject path traversal
                    if ".." in info.filename or info.filename.startswith("/"):
                        self.emit(queue, "progress", f"Skipping unsafe path: {info.filename}")
                        continue
                    # Check compression ratio
                    if info.compress_size > 0:
                        ratio = info.file_size / info.compress_size
                        if ratio > MAX_COMPRESSION_RATIO:
                            self.emit(queue, "progress", f"Skipping suspicious file (ratio {ratio:.0f}:1): {info.filename}")
                            continue
                    total_uncompressed += info.file_size
                    if total_uncompressed > MAX_UNCOMPRESSED_MB * 1024 * 1024:
                        self.emit(queue, "progress", "Uncompressed size limit reached, stopping extraction")
                        break
                    zf.extract(info, dest)
        except zipfile.BadZipFile:
            self.emit(queue, "error", "Invalid zip file — not a valid ZIP archive")
