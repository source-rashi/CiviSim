import hashlib
import json
import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlsplit


logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload if payload is not None else {}, ensure_ascii=True)


def _json_loads(text: Optional[str], default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


class MetaAgent:
    """Governance and security observer with persistent storage and query APIs."""

    def __init__(self) -> None:
        self.backend, self.target = self._resolve_backend()
        self._pg = None

        if self.backend == "postgres":
            try:
                import psycopg2

                self._pg = psycopg2
            except ImportError:
                logger.warning(
                    "PostgreSQL backend requested but psycopg2 is not installed. "
                    "Falling back to SQLite."
                )
                self.backend = "sqlite"
                self.target = self._default_sqlite_path()

        if self.backend == "sqlite" and self.target != ":memory:":
            data_dir = os.path.dirname(self.target)
            if data_dir:
                os.makedirs(data_dir, exist_ok=True)

        if not self._initialize_schema() and self.backend == "postgres":
            logger.warning("Falling back to SQLite due to PostgreSQL initialization failure.")
            self.backend = "sqlite"
            self.target = self._default_sqlite_path()
            self._pg = None
            data_dir = os.path.dirname(self.target)
            if data_dir:
                os.makedirs(data_dir, exist_ok=True)
            self._initialize_schema()

    @staticmethod
    def _default_sqlite_path() -> str:
        return os.path.join(
            os.path.dirname(__file__),
            "data",
            "meta_agent_audit.db",
        )

    def _resolve_backend(self) -> Tuple[str, str]:
        configured = os.getenv("META_AGENT_DATABASE_URL", "").strip()
        if not configured:
            return "sqlite", self._default_sqlite_path()

        lowered = configured.lower()
        if lowered.startswith("postgresql://") or lowered.startswith("postgres://"):
            return "postgres", configured

        if lowered.startswith("sqlite:///"):
            sqlite_path = unquote(configured[10:])
            if os.name == "nt" and sqlite_path.startswith("/") and len(sqlite_path) > 2 and sqlite_path[2] == ":":
                sqlite_path = sqlite_path[1:]
            return "sqlite", sqlite_path or self._default_sqlite_path()

        # Allow direct file path usage for SQLite, including relative paths.
        return "sqlite", configured

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        if self.backend == "sqlite":
            conn = sqlite3.connect(self.target, timeout=30, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
            conn.close()
            return

        if self._pg is None:
            raise RuntimeError("PostgreSQL backend requested without psycopg2 support.")

        conn = self._pg.connect(self.target)
        try:
            yield conn
        finally:
            conn.close()

    def _initialize_schema(self) -> bool:
        try:
            if self.backend == "sqlite":
                with self._connection() as conn:
                    conn.executescript(
                        """
                        CREATE TABLE IF NOT EXISTS meta_runs (
                            run_id TEXT PRIMARY KEY,
                            status TEXT NOT NULL,
                            started_at TEXT NOT NULL,
                            ended_at TEXT,
                            request_json TEXT NOT NULL,
                            summary_json TEXT NOT NULL DEFAULT '{}'
                        );

                        CREATE TABLE IF NOT EXISTS meta_events (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            run_id TEXT NOT NULL,
                            event_ts TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            status TEXT NOT NULL,
                            severity TEXT NOT NULL,
                            message TEXT NOT NULL,
                            duration_ms REAL,
                            details_json TEXT NOT NULL DEFAULT '{}',
                            FOREIGN KEY(run_id) REFERENCES meta_runs(run_id) ON DELETE CASCADE
                        );

                        CREATE TABLE IF NOT EXISTS meta_governance_issues (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            run_id TEXT NOT NULL,
                            code TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            severity TEXT NOT NULL,
                            message TEXT NOT NULL,
                            details_json TEXT NOT NULL DEFAULT '{}',
                            issue_ts TEXT NOT NULL,
                            FOREIGN KEY(run_id) REFERENCES meta_runs(run_id) ON DELETE CASCADE
                        );

                        CREATE TABLE IF NOT EXISTS meta_anomaly_flags (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            run_id TEXT NOT NULL,
                            code TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            severity TEXT NOT NULL,
                            message TEXT NOT NULL,
                            value REAL,
                            threshold REAL,
                            flag_ts TEXT NOT NULL,
                            FOREIGN KEY(run_id) REFERENCES meta_runs(run_id) ON DELETE CASCADE
                        );

                        CREATE INDEX IF NOT EXISTS idx_meta_runs_started_at ON meta_runs(started_at);
                        CREATE INDEX IF NOT EXISTS idx_meta_events_run_ts ON meta_events(run_id, event_ts);
                        CREATE INDEX IF NOT EXISTS idx_meta_gov_run_ts ON meta_governance_issues(run_id, issue_ts);
                        CREATE INDEX IF NOT EXISTS idx_meta_anom_run_ts ON meta_anomaly_flags(run_id, flag_ts);
                        """
                    )
                    conn.commit()
                return True

            with self._connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS meta_runs (
                            run_id TEXT PRIMARY KEY,
                            status TEXT NOT NULL,
                            started_at TEXT NOT NULL,
                            ended_at TEXT,
                            request_json TEXT NOT NULL,
                            summary_json TEXT NOT NULL DEFAULT '{}'
                        );
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS meta_events (
                            id BIGSERIAL PRIMARY KEY,
                            run_id TEXT NOT NULL REFERENCES meta_runs(run_id) ON DELETE CASCADE,
                            event_ts TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            status TEXT NOT NULL,
                            severity TEXT NOT NULL,
                            message TEXT NOT NULL,
                            duration_ms DOUBLE PRECISION,
                            details_json TEXT NOT NULL DEFAULT '{}'
                        );
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS meta_governance_issues (
                            id BIGSERIAL PRIMARY KEY,
                            run_id TEXT NOT NULL REFERENCES meta_runs(run_id) ON DELETE CASCADE,
                            code TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            severity TEXT NOT NULL,
                            message TEXT NOT NULL,
                            details_json TEXT NOT NULL DEFAULT '{}',
                            issue_ts TEXT NOT NULL
                        );
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS meta_anomaly_flags (
                            id BIGSERIAL PRIMARY KEY,
                            run_id TEXT NOT NULL REFERENCES meta_runs(run_id) ON DELETE CASCADE,
                            code TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            severity TEXT NOT NULL,
                            message TEXT NOT NULL,
                            value DOUBLE PRECISION,
                            threshold DOUBLE PRECISION,
                            flag_ts TEXT NOT NULL
                        );
                        """
                    )
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_meta_runs_started_at ON meta_runs(started_at);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_meta_events_run_ts ON meta_events(run_id, event_ts);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_meta_gov_run_ts ON meta_governance_issues(run_id, issue_ts);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_meta_anom_run_ts ON meta_anomaly_flags(run_id, flag_ts);")
                conn.commit()
            return True

        except Exception as exc:
            logger.warning("Meta-agent schema initialization failed: %s", exc)
            return False

    def storage_backend(self) -> str:
        return self.backend

    def storage_target(self) -> str:
        return self.target

    def storage_target_safe(self) -> str:
        if self.backend == "sqlite":
            if self.target == ":memory:":
                return "sqlite:///:memory:"
            return os.path.basename(self.target) or "sqlite"

        parsed = urlsplit(self.target)
        host = parsed.hostname or "localhost"
        db_name = parsed.path.lstrip("/") or "database"
        return f"{parsed.scheme}://{host}/{db_name}"

    def _execute_write(self, sqlite_sql: str, postgres_sql: str, params: Sequence[Any]) -> bool:
        try:
            with self._connection() as conn:
                if self.backend == "sqlite":
                    conn.execute(sqlite_sql, tuple(params))
                else:
                    with conn.cursor() as cur:
                        cur.execute(postgres_sql, tuple(params))
                conn.commit()
            return True
        except Exception as exc:
            logger.warning("Meta-agent write failed: %s", exc)
            return False

    def _fetch_all(self, sqlite_sql: str, postgres_sql: str, params: Sequence[Any]) -> List[Dict[str, Any]]:
        try:
            with self._connection() as conn:
                if self.backend == "sqlite":
                    cur = conn.execute(sqlite_sql, tuple(params))
                    return [dict(row) for row in cur.fetchall()]

                with conn.cursor() as cur:
                    cur.execute(postgres_sql, tuple(params))
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as exc:
            logger.warning("Meta-agent query failed: %s", exc)
            return []

    def start_run(self, policy_text: str, request_payload: Dict[str, Any]) -> str:
        run_id = str(uuid.uuid4())
        policy_hash = hashlib.sha256(policy_text.encode("utf-8")).hexdigest()
        started_at = _utc_now_iso()

        request_data = {
            "policy_sha256": policy_hash,
            "policy_length": len(policy_text),
            "population_size": int(request_payload.get("population_size", 0)),
            "sample_size": int(request_payload.get("sample_size", 0)),
            "steps": int(request_payload.get("steps", 0)),
            "training_epochs": int(request_payload.get("training_epochs", 0)),
        }

        self._execute_write(
            sqlite_sql=(
                """
                INSERT INTO meta_runs (run_id, status, started_at, ended_at, request_json, summary_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """
            ),
            postgres_sql=(
                """
                INSERT INTO meta_runs (run_id, status, started_at, ended_at, request_json, summary_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
            ),
            params=(run_id, "running", started_at, None, _json_dumps(request_data), _json_dumps({})),
        )

        self.record_event(
            run_id=run_id,
            stage="meta_agent",
            status="ok",
            severity="info",
            message="Persistent audit run initialized.",
            details={"storage_backend": self.backend},
        )

        return run_id

    def record_event(
        self,
        run_id: str,
        stage: str,
        status: str,
        message: str,
        severity: str = "info",
        duration_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        event_ts = _utc_now_iso()
        event = {
            "timestamp": event_ts,
            "stage": stage,
            "status": status,
            "severity": severity,
            "message": message,
            "duration_ms": round(float(duration_ms), 2) if duration_ms is not None else None,
            "details": details or {},
        }

        self._execute_write(
            sqlite_sql=(
                """
                INSERT INTO meta_events (
                    run_id, event_ts, stage, status, severity, message, duration_ms, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
            ),
            postgres_sql=(
                """
                INSERT INTO meta_events (
                    run_id, event_ts, stage, status, severity, message, duration_ms, details_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
            ),
            params=(
                run_id,
                event_ts,
                stage,
                status,
                severity,
                message,
                event["duration_ms"],
                _json_dumps(event["details"]),
            ),
        )

        return event

    def add_governance_issue(
        self,
        run_id: str,
        code: str,
        stage: str,
        message: str,
        severity: str = "warning",
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        issue_ts = _utc_now_iso()
        issue = {
            "code": code,
            "stage": stage,
            "severity": severity,
            "message": message,
            "details": details or {},
            "timestamp": issue_ts,
        }

        self._execute_write(
            sqlite_sql=(
                """
                INSERT INTO meta_governance_issues (
                    run_id, code, stage, severity, message, details_json, issue_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """
            ),
            postgres_sql=(
                """
                INSERT INTO meta_governance_issues (
                    run_id, code, stage, severity, message, details_json, issue_ts
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
            ),
            params=(run_id, code, stage, severity, message, _json_dumps(issue["details"]), issue_ts),
        )

        self.record_event(
            run_id=run_id,
            stage=stage,
            status="warning" if severity != "critical" else "error",
            severity=severity,
            message=message,
            details={"code": code, **(details or {})},
        )
        return issue

    def add_anomaly_flag(
        self,
        run_id: str,
        code: str,
        stage: str,
        message: str,
        severity: str = "warning",
        value: Optional[float] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        flag_ts = _utc_now_iso()
        flag = {
            "code": code,
            "stage": stage,
            "severity": severity,
            "message": message,
            "value": value,
            "threshold": threshold,
            "timestamp": flag_ts,
        }

        self._execute_write(
            sqlite_sql=(
                """
                INSERT INTO meta_anomaly_flags (
                    run_id, code, stage, severity, message, value, threshold, flag_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
            ),
            postgres_sql=(
                """
                INSERT INTO meta_anomaly_flags (
                    run_id, code, stage, severity, message, value, threshold, flag_ts
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
            ),
            params=(run_id, code, stage, severity, message, value, threshold, flag_ts),
        )

        self.record_event(
            run_id=run_id,
            stage=stage,
            status="warning" if severity != "critical" else "error",
            severity=severity,
            message=message,
            details={
                "code": code,
                "value": value,
                "threshold": threshold,
            },
        )
        return flag

    def evaluate_policy_text(self, run_id: str, policy_text: str) -> None:
        if len(policy_text.strip()) < 40:
            self.add_governance_issue(
                run_id=run_id,
                code="short_policy_text",
                stage="request_validation",
                severity="warning",
                message="Policy text is short; parsing and recommendation quality may degrade.",
                details={"policy_length": len(policy_text.strip())},
            )

    def evaluate_parsed_policy(self, run_id: str, parsed_policy: Dict[str, Any]) -> None:
        parsed_by = str(parsed_policy.get("parsed_by", "keyword_fallback"))
        domain = str(parsed_policy.get("domain", "general"))
        mechanism = str(parsed_policy.get("mechanism", "general"))

        if parsed_by == "keyword_fallback":
            self.add_governance_issue(
                run_id=run_id,
                code="parser_fallback_mode",
                stage="parse_policy",
                severity="warning",
                message="Policy parser used keyword fallback mode; semantic precision may be limited.",
                details={"parsed_by": parsed_by},
            )

        if domain == "general" and mechanism == "general":
            self.add_governance_issue(
                run_id=run_id,
                code="low_policy_specificity",
                stage="parse_policy",
                severity="warning",
                message="Policy analysis remained generic. Consider a more specific policy description.",
                details={"domain": domain, "mechanism": mechanism},
            )

    def evaluate_sampling(
        self,
        run_id: str,
        population_size: int,
        sample_size: int,
        llm_mode: str,
    ) -> None:
        if population_size <= 0:
            return

        ratio = sample_size / float(population_size)
        min_ratio = float(os.getenv("META_AGENT_MIN_SAMPLE_RATIO", "0.03"))
        if ratio < min_ratio:
            self.add_anomaly_flag(
                run_id=run_id,
                code="low_sampling_ratio",
                stage="llm_sampling",
                severity="warning",
                message="Sample ratio is low and may reduce generalization quality.",
                value=round(ratio, 5),
                threshold=min_ratio,
            )

        if llm_mode != "groq":
            self.add_governance_issue(
                run_id=run_id,
                code="mock_llm_mode",
                stage="llm_sampling",
                severity="warning",
                message="Simulation used mock LLM mode. Use GROQ_API_KEY for higher-fidelity reactions.",
                details={"llm_mode": llm_mode},
            )

    def evaluate_training(self, run_id: str, diagnostics: Dict[str, Any]) -> None:
        if not diagnostics:
            self.add_anomaly_flag(
                run_id=run_id,
                code="missing_training_diagnostics",
                stage="model_training",
                severity="warning",
                message="Training diagnostics are unavailable.",
            )
            return

        validation_mae = diagnostics.get("validation_mae")
        threshold = float(os.getenv("META_AGENT_MAX_VALIDATION_MAE", "0.35"))
        if validation_mae is not None:
            mae = _to_float(validation_mae, default=0.0)
            if mae > threshold:
                self.add_anomaly_flag(
                    run_id=run_id,
                    code="high_validation_mae",
                    stage="model_training",
                    severity="warning",
                    message="Validation MAE is above threshold; predictions may be unstable.",
                    value=round(mae, 6),
                    threshold=threshold,
                )

        samples_validation = int(diagnostics.get("samples_validation", 0) or 0)
        if samples_validation <= 0:
            self.add_governance_issue(
                run_id=run_id,
                code="no_validation_split",
                stage="model_training",
                severity="warning",
                message="No validation split detected. Model quality checks are weaker.",
                details={"samples_validation": samples_validation},
            )

    def evaluate_trends(
        self,
        run_id: str,
        happiness_trend: List[float],
        support_trend: List[float],
        income_trend: List[float],
    ) -> None:
        if len(happiness_trend) >= 2:
            happiness_delta = _to_float(happiness_trend[-1]) - _to_float(happiness_trend[0])
            if happiness_delta < -0.2:
                self.add_anomaly_flag(
                    run_id=run_id,
                    code="happiness_drop",
                    stage="simulation",
                    severity="warning",
                    message="Happiness trend decreased notably across simulation steps.",
                    value=round(happiness_delta, 6),
                    threshold=-0.2,
                )

        if len(support_trend) >= 2:
            support_delta = _to_float(support_trend[-1]) - _to_float(support_trend[0])
            if support_delta < -0.2:
                self.add_anomaly_flag(
                    run_id=run_id,
                    code="support_drop",
                    stage="simulation",
                    severity="warning",
                    message="Policy support declined notably over time.",
                    value=round(support_delta, 6),
                    threshold=-0.2,
                )

        if len(income_trend) >= 2:
            income_start = max(_to_float(income_trend[0], default=1.0), 1.0)
            income_end = _to_float(income_trend[-1])
            income_ratio = (income_end - income_start) / income_start
            if income_ratio < -0.08:
                self.add_anomaly_flag(
                    run_id=run_id,
                    code="income_drop",
                    stage="simulation",
                    severity="warning",
                    message="Average income dropped significantly during simulation.",
                    value=round(income_ratio, 6),
                    threshold=-0.08,
                )

    def finalize_run(self, run_id: str, status: str, summary: Optional[Dict[str, Any]] = None) -> None:
        self._execute_write(
            sqlite_sql=(
                """
                UPDATE meta_runs
                SET status = ?, ended_at = ?, summary_json = ?
                WHERE run_id = ?
                """
            ),
            postgres_sql=(
                """
                UPDATE meta_runs
                SET status = %s, ended_at = %s, summary_json = %s
                WHERE run_id = %s
                """
            ),
            params=(status, _utc_now_iso(), _json_dumps(summary or {}), run_id),
        )

    def build_response_summary(self, run_id: str, preview_events: int = 10) -> Dict[str, Any]:
        run = self.get_run(run_id)
        if run is None:
            return {
                "run_id": run_id,
                "status": "unknown",
                "event_count": 0,
                "governance_issues": [],
                "anomaly_flags": [],
                "audit_trail_preview": [],
            }

        audit_events = run.get("events", [])[-preview_events:]
        compact_events = []
        for event in audit_events:
            compact_events.append(
                {
                    "timestamp": event.get("timestamp"),
                    "stage": event.get("stage"),
                    "status": event.get("status"),
                    "severity": event.get("severity"),
                    "message": event.get("message"),
                    "duration_ms": event.get("duration_ms"),
                }
            )

        return {
            "run_id": run_id,
            "status": run.get("status", "unknown"),
            "event_count": len(run.get("events", [])),
            "governance_issues": run.get("governance_issues", []),
            "anomaly_flags": run.get("anomaly_flags", []),
            "audit_trail_preview": compact_events,
        }

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        runs = self._fetch_all(
            sqlite_sql=(
                """
                SELECT run_id, status, started_at, ended_at, request_json, summary_json
                FROM meta_runs
                WHERE run_id = ?
                LIMIT 1
                """
            ),
            postgres_sql=(
                """
                SELECT run_id, status, started_at, ended_at, request_json, summary_json
                FROM meta_runs
                WHERE run_id = %s
                LIMIT 1
                """
            ),
            params=(run_id,),
        )
        if not runs:
            return None

        run = runs[0]
        events = self._fetch_all(
            sqlite_sql=(
                """
                SELECT event_ts, stage, status, severity, message, duration_ms, details_json
                FROM meta_events
                WHERE run_id = ?
                ORDER BY id ASC
                """
            ),
            postgres_sql=(
                """
                SELECT event_ts, stage, status, severity, message, duration_ms, details_json
                FROM meta_events
                WHERE run_id = %s
                ORDER BY id ASC
                """
            ),
            params=(run_id,),
        )
        governance = self._fetch_all(
            sqlite_sql=(
                """
                SELECT code, stage, severity, message, details_json, issue_ts
                FROM meta_governance_issues
                WHERE run_id = ?
                ORDER BY id ASC
                """
            ),
            postgres_sql=(
                """
                SELECT code, stage, severity, message, details_json, issue_ts
                FROM meta_governance_issues
                WHERE run_id = %s
                ORDER BY id ASC
                """
            ),
            params=(run_id,),
        )
        anomalies = self._fetch_all(
            sqlite_sql=(
                """
                SELECT code, stage, severity, message, value, threshold, flag_ts
                FROM meta_anomaly_flags
                WHERE run_id = ?
                ORDER BY id ASC
                """
            ),
            postgres_sql=(
                """
                SELECT code, stage, severity, message, value, threshold, flag_ts
                FROM meta_anomaly_flags
                WHERE run_id = %s
                ORDER BY id ASC
                """
            ),
            params=(run_id,),
        )

        event_items: List[Dict[str, Any]] = []
        for row in events:
            event_items.append(
                {
                    "timestamp": row.get("event_ts"),
                    "stage": row.get("stage"),
                    "status": row.get("status"),
                    "severity": row.get("severity"),
                    "message": row.get("message"),
                    "duration_ms": row.get("duration_ms"),
                    "details": _json_loads(row.get("details_json"), {}),
                }
            )

        governance_items: List[Dict[str, Any]] = []
        for row in governance:
            governance_items.append(
                {
                    "code": row.get("code"),
                    "stage": row.get("stage"),
                    "severity": row.get("severity"),
                    "message": row.get("message"),
                    "details": _json_loads(row.get("details_json"), {}),
                    "timestamp": row.get("issue_ts"),
                }
            )

        anomaly_items: List[Dict[str, Any]] = []
        for row in anomalies:
            anomaly_items.append(
                {
                    "code": row.get("code"),
                    "stage": row.get("stage"),
                    "severity": row.get("severity"),
                    "message": row.get("message"),
                    "value": row.get("value"),
                    "threshold": row.get("threshold"),
                    "timestamp": row.get("flag_ts"),
                }
            )

        return {
            "run_id": run.get("run_id"),
            "status": run.get("status"),
            "started_at": run.get("started_at"),
            "ended_at": run.get("ended_at"),
            "request": _json_loads(run.get("request_json"), {}),
            "summary": _json_loads(run.get("summary_json"), {}),
            "governance_issues": governance_items,
            "anomaly_flags": anomaly_items,
            "events": event_items,
        }

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        rows = self._fetch_all(
            sqlite_sql=(
                """
                SELECT
                    r.run_id,
                    r.status,
                    r.started_at,
                    r.ended_at,
                    r.summary_json,
                    (SELECT COUNT(*) FROM meta_events e WHERE e.run_id = r.run_id) AS event_count,
                    (SELECT COUNT(*) FROM meta_governance_issues g WHERE g.run_id = r.run_id) AS governance_issue_count,
                    (SELECT COUNT(*) FROM meta_anomaly_flags a WHERE a.run_id = r.run_id) AS anomaly_count
                FROM meta_runs r
                ORDER BY r.started_at DESC
                LIMIT ?
                """
            ),
            postgres_sql=(
                """
                SELECT
                    r.run_id,
                    r.status,
                    r.started_at,
                    r.ended_at,
                    r.summary_json,
                    (SELECT COUNT(*) FROM meta_events e WHERE e.run_id = r.run_id) AS event_count,
                    (SELECT COUNT(*) FROM meta_governance_issues g WHERE g.run_id = r.run_id) AS governance_issue_count,
                    (SELECT COUNT(*) FROM meta_anomaly_flags a WHERE a.run_id = r.run_id) AS anomaly_count
                FROM meta_runs r
                ORDER BY r.started_at DESC
                LIMIT %s
                """
            ),
            params=(safe_limit,),
        )

        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "run_id": row.get("run_id"),
                    "status": row.get("status"),
                    "started_at": row.get("started_at"),
                    "ended_at": row.get("ended_at"),
                    "event_count": int(row.get("event_count", 0) or 0),
                    "governance_issue_count": int(row.get("governance_issue_count", 0) or 0),
                    "anomaly_count": int(row.get("anomaly_count", 0) or 0),
                    "summary": _json_loads(row.get("summary_json"), {}),
                }
            )

        return results


meta_agent = MetaAgent()
