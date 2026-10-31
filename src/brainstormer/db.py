"""Stockage SQLite. Volontairement simple pour la V1 (migration Supabase prévue en V2)."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .models import Insight, Signal

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id           TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    title        TEXT NOT NULL,
    body         TEXT,
    url          TEXT NOT NULL,
    engagement   INTEGER DEFAULT 0,
    created_at   TEXT NOT NULL,
    extra        TEXT,
    collected_at TEXT NOT NULL,
    processed    INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS insights (
    signal_id          TEXT PRIMARY KEY REFERENCES signals(id),
    is_opportunity     INTEGER NOT NULL,
    problem            TEXT,
    audience           TEXT,
    existing_solutions TEXT,
    idea_name          TEXT,
    idea_pitch         TEXT,
    category           TEXT,
    pain_severity      INTEGER,
    willingness_to_pay INTEGER,
    solo_buildable     INTEGER,
    founder_fit        INTEGER,
    score              REAL,
    extracted_at       TEXT NOT NULL,
    reported_at        TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
    signal_id  TEXT REFERENCES signals(id),
    vote       INTEGER NOT NULL,  -- +1 / -1 : futures étiquettes pour le ML (V3)
    created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def upsert_signals(self, signals: list[Signal]) -> int:
        """Insère les nouveaux signaux, ignore les doublons. Retourne le nombre de nouveaux."""
        now = datetime.now(UTC).isoformat()
        before = self.conn.total_changes
        self.conn.executemany(
            """INSERT OR IGNORE INTO signals
               (id, source, title, body, url, engagement, created_at, extra, collected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    s.id,
                    s.source.value,
                    s.title,
                    s.body,
                    s.url,
                    s.engagement,
                    s.created_at.isoformat(),
                    json.dumps(s.extra),
                    now,
                )
                for s in signals
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def unprocessed(self, limit: int = 100) -> list[Signal]:
        rows = self.conn.execute(
            "SELECT * FROM signals WHERE processed = 0 ORDER BY engagement DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            Signal(
                id=r["id"],
                source=r["source"],
                title=r["title"],
                body=r["body"] or "",
                url=r["url"],
                engagement=r["engagement"],
                created_at=datetime.fromisoformat(r["created_at"]),
                extra=json.loads(r["extra"] or "{}"),
            )
            for r in rows
        ]

    def save_insight(self, insight: Insight) -> None:
        d = insight.model_dump()
        d["is_opportunity"] = int(d["is_opportunity"])
        d["extracted_at"] = datetime.now(UTC).isoformat()
        cols = ", ".join(d)
        marks = ", ".join("?" for _ in d)
        self.conn.execute(
            f"INSERT OR REPLACE INTO insights ({cols}) VALUES ({marks})", list(d.values())
        )
        self.conn.execute("UPDATE signals SET processed = 1 WHERE id = ?", (insight.signal_id,))
        self.conn.commit()

    def top_ideas(self, limit: int, include_reported: bool = False) -> list[sqlite3.Row]:
        where = "i.is_opportunity = 1"
        if not include_reported:
            where += " AND i.reported_at IS NULL"
        return self.conn.execute(
            f"""SELECT i.*, s.title, s.url, s.source, s.engagement
                FROM insights i JOIN signals s ON s.id = i.signal_id
                WHERE {where}
                ORDER BY i.score DESC LIMIT ?""",
            (limit,),
        ).fetchall()

    def mark_reported(self, signal_ids: list[str]) -> None:
        now = datetime.now(UTC).isoformat()
        self.conn.executemany(
            "UPDATE insights SET reported_at = ? WHERE signal_id = ?",
            [(now, sid) for sid in signal_ids],
        )
        self.conn.commit()

    def add_feedback(self, signal_id: str, vote: int) -> None:
        self.conn.execute(
            "INSERT INTO feedback (signal_id, vote, created_at) VALUES (?, ?, ?)",
            (signal_id, vote, datetime.now(UTC).isoformat()),
        )
        self.conn.commit()

    def stats(self) -> dict:
        q = lambda sql: self.conn.execute(sql).fetchone()[0]  # noqa: E731
        return {
            "signaux": q("SELECT COUNT(*) FROM signals"),
            "non_traites": q("SELECT COUNT(*) FROM signals WHERE processed = 0"),
            "insights": q("SELECT COUNT(*) FROM insights"),
            "opportunites": q("SELECT COUNT(*) FROM insights WHERE is_opportunity = 1"),
            "votes": q("SELECT COUNT(*) FROM feedback"),
        }
