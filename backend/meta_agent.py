import hashlib
import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class MetaAgent:
    """Lightweight governance and security observer for simulation runs."""

    def __init__(self) -> None:
        default_log_path = os.path.join(
            os.path.dirname(__file__),
            "logs",
            "audit_events.jsonl",
        )
        self.log_path = os.getenv("META_AGENT_LOG_PATH", default_log_path)
        self.max_cached_runs = max(20, int(os.getenv("META_AGENT_MAX_CACHED_RUNS", "200")))
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._run_order: List[str] = []
        self._lock = threading.Lock()

        log_dir = os.path.dirname(self.log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    def start_run(self, policy_text: str, request_payload: Dict[str, Any]) -> str:
        run_id = str(uuid.uuid4())
        policy_hash = hashlib.sha256(policy_text.encode("utf-8")).hexdigest()

        record = {
            "run_id": run_id,
            "status": "running",
            "started_at": _utc_now_iso(),
            "ended_at": None,
            "request": {
                "policy_sha256": policy_hash,
                "policy_length": len(policy_text),
                "population_size": int(request_payload.get("population_size", 0)),
                "sample_size": int(request_payload.get("sample_size", 0)),
                "steps": int(request_payload.get("steps", 0)),
                "training_epochs": int(request_payload.get("training_epochs", 0)),
            },
            "governance_issues": [],
            "anomaly_flags": [],
            "events": [],
            "summary": {},
        }

        with self._lock:
            self._runs[run_id] = record
            self._run_order.append(run_id)
            self._trim_cache_locked()

        self._append_jsonl(
            {
                "type": "run_started",
                "run_id": run_id,
                "timestamp": _utc_now_iso(),
                "request": record["request"],
            }
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
        event = {
            "timestamp": _utc_now_iso(),
            "stage": stage,
            "status": status,
            "severity": severity,
            "message": message,
            "duration_ms": round(float(duration_ms), 2) if duration_ms is not None else None,
            "details": details or {},
        }

        with self._lock:
            run = self._runs.get(run_id)
            if run is not None:
                run["events"].append(event)

        self._append_jsonl(
            {
                "type": "event",
                "run_id": run_id,
                "event": event,
            }
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
        issue = {
            "code": code,
            "stage": stage,
            "severity": severity,
            "message": message,
            "details": details or {},
            "timestamp": _utc_now_iso(),
        }

        with self._lock:
            run = self._runs.get(run_id)
            if run is not None:
                run["governance_issues"].append(issue)

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
        flag = {
            "code": code,
            "stage": stage,
            "severity": severity,
            "message": message,
            "value": value,
            "threshold": threshold,
            "timestamp": _utc_now_iso(),
        }

        with self._lock:
            run = self._runs.get(run_id)
            if run is not None:
                run["anomaly_flags"].append(flag)

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
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return

            run["status"] = status
            run["ended_at"] = _utc_now_iso()
            if summary:
                run["summary"] = summary

            snapshot = {
                "run_id": run_id,
                "status": run["status"],
                "started_at": run["started_at"],
                "ended_at": run["ended_at"],
                "event_count": len(run["events"]),
                "governance_issue_count": len(run["governance_issues"]),
                "anomaly_count": len(run["anomaly_flags"]),
                "summary": run.get("summary", {}),
            }

        self._append_jsonl(
            {
                "type": "run_finalized",
                "timestamp": _utc_now_iso(),
                "run": snapshot,
            }
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
        with self._lock:
            run = self._runs.get(run_id)
            return deepcopy(run) if run is not None else None

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        with self._lock:
            selected_ids = list(reversed(self._run_order[-safe_limit:]))
            results: List[Dict[str, Any]] = []
            for run_id in selected_ids:
                run = self._runs.get(run_id)
                if run is None:
                    continue
                results.append(
                    {
                        "run_id": run_id,
                        "status": run.get("status"),
                        "started_at": run.get("started_at"),
                        "ended_at": run.get("ended_at"),
                        "event_count": len(run.get("events", [])),
                        "governance_issue_count": len(run.get("governance_issues", [])),
                        "anomaly_count": len(run.get("anomaly_flags", [])),
                        "summary": run.get("summary", {}),
                    }
                )
            return results

    def _trim_cache_locked(self) -> None:
        overflow = len(self._run_order) - self.max_cached_runs
        if overflow <= 0:
            return

        for run_id in self._run_order[:overflow]:
            self._runs.pop(run_id, None)
        self._run_order = self._run_order[overflow:]

    def _append_jsonl(self, payload: Dict[str, Any]) -> None:
        try:
            with open(self.log_path, "a", encoding="utf-8") as fp:
                fp.write(json.dumps(payload, ensure_ascii=True))
                fp.write("\n")
        except OSError:
            # Logging failures should not crash simulation requests.
            return


meta_agent = MetaAgent()
