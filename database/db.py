"""
database/db.py — SQLite persistence layer for CIVISIM simulation runs.

Schema (single table — intentionally simple to start):

    simulation_runs
    ───────────────────────────────────────────────────────────────────
    id              INTEGER   PK AUTOINCREMENT
    run_id          TEXT      UNIQUE — matches meta_agent run_id
    created_at      TEXT      ISO-8601 UTC timestamp
    policy_text     TEXT      Raw user input
    domain          TEXT      Parsed domain label
    mechanism       TEXT      Parsed mechanism
    affected_groups TEXT      JSON array
    population_size INTEGER
    sample_size     INTEGER
    steps           INTEGER
    final_happiness REAL
    final_support   REAL
    avg_income_end  REAL
    recommendation  TEXT      "good_to_go" | "needs_changes" | "not_recommended"
    happiness_trend TEXT      JSON array of floats
    support_trend   TEXT      JSON array of floats
    income_trend    TEXT      JSON array of floats
    diary_entries   TEXT      JSON array of {citizen_id, diary_entry, ...}

Public API:
    SimulationDB()              — creates DB + schema if not exists
    .save_run(run_id, payload)  — persist a completed simulation
    .list_runs(limit)           — summary rows for sidebar
    .get_run(run_id)            — full run data for replay
    .delete_run(run_id)         — remove a run
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default DB file lives inside the project so it is gitignore-able.
_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), "civisim_runs.db"
)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS simulation_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT    NOT NULL UNIQUE,
    created_at      TEXT    NOT NULL,
    policy_text     TEXT    NOT NULL DEFAULT '',
    domain          TEXT    NOT NULL DEFAULT 'general',
    mechanism       TEXT    NOT NULL DEFAULT 'general',
    affected_groups TEXT    NOT NULL DEFAULT '[]',
    population_size INTEGER NOT NULL DEFAULT 0,
    sample_size     INTEGER NOT NULL DEFAULT 0,
    steps           INTEGER NOT NULL DEFAULT 0,
    final_happiness REAL    NOT NULL DEFAULT 0.0,
    final_support   REAL    NOT NULL DEFAULT 0.0,
    avg_income_end  REAL    NOT NULL DEFAULT 0.0,
    recommendation  TEXT    NOT NULL DEFAULT 'needs_changes',
    happiness_trend TEXT    NOT NULL DEFAULT '[]',
    support_trend   TEXT    NOT NULL DEFAULT '[]',
    income_trend    TEXT    NOT NULL DEFAULT '[]',
    diary_entries   TEXT    NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_sim_runs_created ON simulation_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sim_runs_domain  ON simulation_runs(domain);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jdumps(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=True)


def _jloads(text: Optional[str], default: Any = None) -> Any:
    if not text:
        return default if default is not None else []
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default if default is not None else []


class SimulationDB:
    """
    Lightweight SQLite wrapper for persisting CIVISIM simulation runs.

    Usage:
        db = SimulationDB()                     # default path
        db = SimulationDB("/path/to/custom.db") # custom path
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or os.getenv("CIVISIM_DB_PATH", _DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._initialize_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=15, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize_schema(self) -> None:
        try:
            with self._conn() as conn:
                conn.executescript(_CREATE_TABLE_SQL)
            logger.info("SimulationDB ready at: %s", self.db_path)
        except Exception as exc:
            logger.error("SimulationDB schema init failed: %s", exc)
            raise

    # -----------------------------------------------------------------------
    # Write
    # -----------------------------------------------------------------------

    def save_run(self, run_id: str, payload: Dict[str, Any]) -> bool:
        """
        Persist a completed simulation.

        `payload` is the full response dict from the /api/simulate endpoint.
        All fields have safe defaults — partial payloads are handled gracefully.
        """
        try:
            policy_analysis = payload.get("policy_analysis") or {}
            pop_stats       = payload.get("population_stats") or {}
            rec_summary     = payload.get("recommendation_summary") or {}
            pipeline        = payload.get("pipeline") or {}

            happiness_trend = payload.get("happiness_trend") or []
            support_trend   = payload.get("support_trend") or []
            income_trend    = payload.get("income_trend") or []

            # Diary entries — take the first 5 reaction previews
            diary_entries = [
                {
                    "citizen_id":      e.get("citizen_id"),
                    "occupation":      e.get("occupation"),
                    "location":        e.get("location"),
                    "happiness_change": e.get("happiness_change"),
                    "income_change":   e.get("income_change"),
                    "diary_entry":     e.get("diary_entry"),
                }
                for e in (payload.get("reaction_preview") or [])[:5]
            ]

            final_happiness = float(happiness_trend[-1]) if happiness_trend else 0.0
            final_support   = float(support_trend[-1])   if support_trend   else 0.0
            avg_income_end  = float(income_trend[-1])     if income_trend    else 0.0

            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO simulation_runs (
                        run_id, created_at, policy_text, domain, mechanism,
                        affected_groups, population_size, sample_size, steps,
                        final_happiness, final_support, avg_income_end,
                        recommendation, happiness_trend, support_trend,
                        income_trend, diary_entries
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?
                    )
                    """,
                    (
                        run_id,
                        _utc_now(),
                        str(payload.get("policy_text") or ""),
                        str(policy_analysis.get("domain", "general")),
                        str(policy_analysis.get("mechanism", "general")),
                        _jdumps(policy_analysis.get("affected_groups", [])),
                        int(pop_stats.get("total", 0)),
                        int(pipeline.get("sample_size", 0)),
                        int(pipeline.get("steps", 0)),
                        final_happiness,
                        final_support,
                        avg_income_end,
                        str(rec_summary.get("status", "needs_changes")),
                        _jdumps(happiness_trend),
                        _jdumps(support_trend),
                        _jdumps(income_trend),
                        _jdumps(diary_entries),
                    ),
                )
            return True
        except Exception as exc:
            logger.error("SimulationDB.save_run failed: %s", exc)
            return False

    # -----------------------------------------------------------------------
    # Read — list (sidebar)
    # -----------------------------------------------------------------------

    def list_runs(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Return summary rows ordered by most recent first.
        Used by the /api/runs GET endpoint and the frontend sidebar.
        """
        safe_limit = max(1, min(int(limit), 200))
        try:
            with self._conn() as conn:
                cur = conn.execute(
                    """
                    SELECT run_id, created_at, policy_text, domain, mechanism,
                           final_happiness, final_support, avg_income_end,
                           recommendation, population_size, sample_size, steps
                    FROM simulation_runs
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (safe_limit,),
                )
                return [dict(row) for row in cur.fetchall()]
        except Exception as exc:
            logger.error("SimulationDB.list_runs failed: %s", exc)
            return []

    # -----------------------------------------------------------------------
    # Read — full run (replay)
    # -----------------------------------------------------------------------

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the full saved run for a given run_id.
        JSON columns are parsed back to Python objects.
        Returns None if the run_id is not found.
        """
        try:
            with self._conn() as conn:
                cur = conn.execute(
                    "SELECT * FROM simulation_runs WHERE run_id = ? LIMIT 1",
                    (run_id,),
                )
                row = cur.fetchone()
            if row is None:
                return None

            data = dict(row)
            # Deserialise JSON columns
            data["affected_groups"]  = _jloads(data.get("affected_groups"),  [])
            data["happiness_trend"]  = _jloads(data.get("happiness_trend"),  [])
            data["support_trend"]    = _jloads(data.get("support_trend"),    [])
            data["income_trend"]     = _jloads(data.get("income_trend"),     [])
            data["diary_entries"]    = _jloads(data.get("diary_entries"),     [])
            return data
        except Exception as exc:
            logger.error("SimulationDB.get_run failed: %s", exc)
            return None

    # -----------------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------------

    def delete_run(self, run_id: str) -> bool:
        """Remove a run by run_id."""
        try:
            with self._conn() as conn:
                conn.execute(
                    "DELETE FROM simulation_runs WHERE run_id = ?",
                    (run_id,),
                )
            return True
        except Exception as exc:
            logger.error("SimulationDB.delete_run failed: %s", exc)
            return False

    # -----------------------------------------------------------------------
    # Utility
    # -----------------------------------------------------------------------

    def count_runs(self) -> int:
        """Return total number of stored runs."""
        try:
            with self._conn() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM simulation_runs")
                return int(cur.fetchone()[0])
        except Exception:
            return 0
