import aiosqlite
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("./data/reviews.db")

BUILTIN_PROFILES = [
    ("beginner",   "Beginner Friendly", "Lenient, encouraging, skips advanced checks", 1,
     '{"strictness":"lenient","skip_agents":["complexity","plagiarism","dependencies"],"llm_tone":"encouraging and supportive"}'),
    ("bootcamp",   "Bootcamp Standard", "Full-stack completeness, CRUD, basic auth", 1,
     '{"strictness":"moderate","skip_agents":[],"llm_tone":"constructive and direct"}'),
    ("production", "Production Ready",  "Security, performance, testing, error handling", 1,
     '{"strictness":"strict","skip_agents":[],"llm_tone":"professional and thorough"}'),
    ("interview",  "Interview Prep",    "Code quality, patterns, complexity, best practices", 1,
     '{"strictness":"strict","skip_agents":[],"llm_tone":"evaluative, like a senior interviewer"}'),
    ("hackathon",  "Hackathon",         "Creativity, completeness, demo-readiness", 1,
     '{"strictness":"lenient","skip_agents":["plagiarism","documentation","accessibility"],"llm_tone":"enthusiastic and practical"}'),
    ("enterprise", "Enterprise",        "Security, docs, testing, maintainability, CI/CD", 1,
     '{"strictness":"very_strict","skip_agents":[],"llm_tone":"formal and compliance-focused"}'),
]


async def init_db():
    Path("./data").mkdir(exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                project_id TEXT,
                student_name TEXT,
                version INTEGER DEFAULT 1,
                profile_id TEXT DEFAULT 'bootcamp',
                rubric_id TEXT,
                overall_score REAL,
                grade TEXT,
                category_scores_json TEXT,
                report_json TEXT,
                file_count INTEGER DEFAULT 0,
                problem_statement TEXT,
                phase TEXT DEFAULT 'idle',
                cancelled INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_project_version ON reviews(project_id, version);
            CREATE INDEX IF NOT EXISTS idx_student ON reviews(student_name, created_at);

            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                is_builtin INTEGER DEFAULT 0,
                config_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id, created_at);

            CREATE TABLE IF NOT EXISTS batch_reviews (
                id TEXT PRIMARY KEY,
                profile_id TEXT DEFAULT 'bootcamp',
                rubric_id TEXT,
                problem_statement TEXT,
                student_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'reviewing',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS batch_members (
                batch_id TEXT NOT NULL,
                review_id TEXT NOT NULL,
                student_name TEXT,
                student_index INTEGER,
                PRIMARY KEY (batch_id, review_id)
            );
            CREATE INDEX IF NOT EXISTS idx_batch_members ON batch_members(batch_id, student_index);

            CREATE TABLE IF NOT EXISTS rubrics (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                categories_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS submission_fingerprints (
                session_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, file_path)
            );
            CREATE INDEX IF NOT EXISTS idx_fingerprint ON submission_fingerprints(fingerprint);
        """)
        # Seed built-in profiles
        for pid, name, desc, builtin, config in BUILTIN_PROFILES:
            await db.execute(
                "INSERT OR IGNORE INTO profiles (id, name, description, is_builtin, config_json) VALUES (?,?,?,?,?)",
                (pid, name, desc, builtin, config)
            )
        await db.commit()
    logger.info(f"Database initialized at {DB_PATH}")


async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
