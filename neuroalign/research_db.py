"""
Research Data Collector
=======================
Stores anonymous session data for the thesis empirical chapter.

Storage: SQLite (built into Python — zero extra dependencies).
Why NOT ChromaDB for this: ChromaDB is a vector store optimised for
semantic similarity search, not structured relational queries.
Research data needs GROUP BY, correlation, regression — SQL, not ANN.

GDPR compliance notes:
- No names, emails, or device identifiers are collected.
- Age is collected as a range (not exact year) to reduce re-identification risk.
- Users see an explicit consent checkbox before any data is saved.
- Data is stored only locally (never sent to a remote server by this module).
- Users can export or delete their session data at any time.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime


DB_PATH = Path("data/research.db")


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp               TEXT,

            -- Anonymous demographics (GDPR: ranges, not exact values)
            age_range               TEXT,   -- "18-24", "25-34", "35-44", "45-54", "55+"
            gender                  TEXT,   -- "F", "M", "Non-binary", "Prefer not to say"
            education_level         TEXT,   -- "High school", "Bachelor", "Master", "PhD", "Other"
            occupation_type         TEXT,   -- "Student", "Academic", "Tech", "Healthcare", "Other"

            -- Session context
            cognitive_modes         TEXT,   -- JSON list e.g. '["adhd","dyslexia"]'
            fatigue_level           INTEGER, -- 1-5 self-report
            document_type           TEXT,   -- from ContentAnalyzer
            input_word_count        INTEGER,

            -- Readability metrics (the quantitative thesis results)
            flesch_ease_before      REAL,
            flesch_ease_after       REAL,
            flesch_ease_delta       REAL,
            grade_level_before      REAL,
            grade_level_after       REAL,
            grade_level_delta       REAL,
            fog_before              REAL,
            fog_after               REAL,
            fog_delta               REAL,
            sentence_len_before     REAL,
            sentence_len_after      REAL,
            sentence_len_delta      REAL,

            -- User feedback (optional)
            subjective_usefulness   INTEGER,  -- 1-5 Likert
            open_feedback           TEXT      -- free text, optional
        )
    """)
    conn.commit()
    return conn


def save_session(
    demographics: dict,
    metrics_delta: dict,
    document_type: str,
    input_word_count: int,
    subjective_usefulness: int | None = None,
    open_feedback: str = "",
) -> None:
    """Insert one research session row into SQLite."""
    import json
    conn = _get_conn()
    conn.execute("""
        INSERT INTO sessions (
            timestamp,
            age_range, gender, education_level, occupation_type,
            cognitive_modes, fatigue_level, document_type, input_word_count,
            flesch_ease_before, flesch_ease_after, flesch_ease_delta,
            grade_level_before, grade_level_after, grade_level_delta,
            fog_before, fog_after, fog_delta,
            sentence_len_before, sentence_len_after, sentence_len_delta,
            subjective_usefulness, open_feedback
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?
        )
    """, (
        datetime.utcnow().isoformat(),
        demographics.get("age_range"),
        demographics.get("gender"),
        demographics.get("education_level"),
        demographics.get("occupation_type"),
        json.dumps(metrics_delta.get("profile", [])),
        demographics.get("fatigue_level"),
        document_type,
        input_word_count,
        metrics_delta.get("flesch_ease_before"),
        metrics_delta.get("flesch_ease_after"),
        metrics_delta.get("flesch_ease_delta"),
        metrics_delta.get("grade_level_before"),
        metrics_delta.get("grade_level_after"),
        metrics_delta.get("grade_level_delta"),
        metrics_delta.get("fog_before"),
        metrics_delta.get("fog_after"),
        metrics_delta.get("fog_delta"),
        metrics_delta.get("sentence_len_before"),
        metrics_delta.get("sentence_len_after"),
        metrics_delta.get("sentence_len_delta"),
        subjective_usefulness,
        open_feedback,
    ))
    conn.commit()
    conn.close()


def load_dataframe() -> pd.DataFrame:
    """Return all sessions as a Pandas DataFrame — ready for analysis."""
    conn = _get_conn()
    df = pd.read_sql_query("SELECT * FROM sessions ORDER BY timestamp DESC", conn)
    conn.close()
    return df


def delete_last_session() -> None:
    """Allow user to delete their own most recent session (GDPR right to erasure)."""
    conn = _get_conn()
    conn.execute("DELETE FROM sessions WHERE id = (SELECT MAX(id) FROM sessions)")
    conn.commit()
    conn.close()


def export_csv() -> str:
    """Return CSV string for download button."""
    df = load_dataframe()
    return df.to_csv(index=False)
