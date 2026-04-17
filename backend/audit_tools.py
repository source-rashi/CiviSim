import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from meta_agent import MetaAgent


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload if payload is not None else {}, ensure_ascii=True)


def _empty_run_record() -> Dict[str, Any]:
    return {
        "status": "running",
        "started_at": None,
        "ended_at": None,
        "request": {},
        "summary": {},
        "events": [],
        "governance_issues": [],
        "anomaly_flags": [],
    }


def _infer_governance_or_anomaly(event: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    details = event.get("details") or {}
    code = details.get("code")
    if not code:
        return {}, {}

    has_anomaly_fields = (details.get("value") is not None) or (details.get("threshold") is not None)
    timestamp = event.get("timestamp") or _utc_now_iso()
    severity = event.get("severity", "warning")
    stage = event.get("stage", "unknown")
    message = event.get("message", "")

    if has_anomaly_fields:
        return (
            {},
            {
                "code": str(code),
                "stage": str(stage),
                "severity": str(severity),
                "message": str(message),
                "value": details.get("value"),
                "threshold": details.get("threshold"),
                "timestamp": str(timestamp),
            },
        )

    gov_details = dict(details)
    gov_details.pop("code", None)
    return (
        {
            "code": str(code),
            "stage": str(stage),
            "severity": str(severity),
            "message": str(message),
            "details": gov_details,
            "timestamp": str(timestamp),
        },
        {},
    )


def load_legacy_jsonl(path: str) -> Dict[str, Dict[str, Any]]:
    runs: Dict[str, Dict[str, Any]] = {}

    with open(path, "r", encoding="utf-8") as fp:
        for line_number, raw in enumerate(fp, start=1):
            line = raw.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping malformed JSON at line {line_number}.")
                continue

            event_type = item.get("type")

            if event_type == "run_started":
                run_id = str(item.get("run_id", "")).strip()
                if not run_id:
                    continue
                record = runs.setdefault(run_id, _empty_run_record())
                record["started_at"] = item.get("timestamp") or record["started_at"] or _utc_now_iso()
                record["request"] = item.get("request") or record["request"]
                record["status"] = "running"
                continue

            if event_type == "event":
                run_id = str(item.get("run_id", "")).strip()
                if not run_id:
                    continue

                record = runs.setdefault(run_id, _empty_run_record())
                event = item.get("event") or {}
                event_record = {
                    "timestamp": str(event.get("timestamp") or _utc_now_iso()),
                    "stage": str(event.get("stage", "unknown")),
                    "status": str(event.get("status", "ok")),
                    "severity": str(event.get("severity", "info")),
                    "message": str(event.get("message", "")),
                    "duration_ms": event.get("duration_ms"),
                    "details": event.get("details") or {},
                }

                if record["started_at"] is None:
                    record["started_at"] = event_record["timestamp"]

                record["events"].append(event_record)

                governance_issue, anomaly_flag = _infer_governance_or_anomaly(event_record)
                if governance_issue:
                    record["governance_issues"].append(governance_issue)
                if anomaly_flag:
                    record["anomaly_flags"].append(anomaly_flag)
                continue

            if event_type == "run_finalized":
                run_info = item.get("run") or {}
                run_id = str(run_info.get("run_id", "")).strip()
                if not run_id:
                    continue

                record = runs.setdefault(run_id, _empty_run_record())
                record["status"] = str(run_info.get("status") or record["status"] or "completed")
                record["started_at"] = run_info.get("started_at") or record["started_at"] or _utc_now_iso()
                record["ended_at"] = run_info.get("ended_at") or record["ended_at"]
                record["summary"] = run_info.get("summary") or record["summary"]

    for run in runs.values():
        if not run["started_at"]:
            run["started_at"] = _utc_now_iso()

    return runs


def migrate_legacy_jsonl(agent: MetaAgent, source: str, skip_existing: bool = True) -> Dict[str, int]:
    if not os.path.exists(source):
        return {
            "runs_found": 0,
            "runs_imported": 0,
            "runs_skipped": 0,
            "events_imported": 0,
            "governance_imported": 0,
            "anomaly_imported": 0,
        }

    runs = load_legacy_jsonl(source)

    existing = set()
    existing_rows = agent._fetch_all(
        sqlite_sql="SELECT run_id FROM meta_runs",
        postgres_sql="SELECT run_id FROM meta_runs",
        params=(),
    )
    for row in existing_rows:
        run_id = row.get("run_id")
        if run_id:
            existing.add(str(run_id))

    stats = {
        "runs_found": len(runs),
        "runs_imported": 0,
        "runs_skipped": 0,
        "events_imported": 0,
        "governance_imported": 0,
        "anomaly_imported": 0,
    }

    for run_id, run in runs.items():
        if skip_existing and run_id in existing:
            stats["runs_skipped"] += 1
            continue

        upsert_ok = agent._execute_write(
            sqlite_sql=(
                """
                INSERT INTO meta_runs (run_id, status, started_at, ended_at, request_json, summary_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status = excluded.status,
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    request_json = excluded.request_json,
                    summary_json = excluded.summary_json
                """
            ),
            postgres_sql=(
                """
                INSERT INTO meta_runs (run_id, status, started_at, ended_at, request_json, summary_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    started_at = EXCLUDED.started_at,
                    ended_at = EXCLUDED.ended_at,
                    request_json = EXCLUDED.request_json,
                    summary_json = EXCLUDED.summary_json
                """
            ),
            params=(
                run_id,
                run.get("status", "completed"),
                run.get("started_at") or _utc_now_iso(),
                run.get("ended_at"),
                _json_dumps(run.get("request") or {}),
                _json_dumps(run.get("summary") or {}),
            ),
        )

        if not upsert_ok:
            continue

        stats["runs_imported"] += 1

        for event in run.get("events", []):
            inserted = agent._execute_write(
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
                    event.get("timestamp") or _utc_now_iso(),
                    event.get("stage", "unknown"),
                    event.get("status", "ok"),
                    event.get("severity", "info"),
                    event.get("message", ""),
                    event.get("duration_ms"),
                    _json_dumps(event.get("details") or {}),
                ),
            )
            if inserted:
                stats["events_imported"] += 1

        for issue in run.get("governance_issues", []):
            inserted = agent._execute_write(
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
                params=(
                    run_id,
                    issue.get("code", "legacy_issue"),
                    issue.get("stage", "unknown"),
                    issue.get("severity", "warning"),
                    issue.get("message", ""),
                    _json_dumps(issue.get("details") or {}),
                    issue.get("timestamp") or _utc_now_iso(),
                ),
            )
            if inserted:
                stats["governance_imported"] += 1

        for flag in run.get("anomaly_flags", []):
            inserted = agent._execute_write(
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
                params=(
                    run_id,
                    flag.get("code", "legacy_anomaly"),
                    flag.get("stage", "unknown"),
                    flag.get("severity", "warning"),
                    flag.get("message", ""),
                    flag.get("value"),
                    flag.get("threshold"),
                    flag.get("timestamp") or _utc_now_iso(),
                ),
            )
            if inserted:
                stats["anomaly_imported"] += 1

    return stats


def export_runs(agent: MetaAgent, output: str, limit: int, output_format: str) -> Dict[str, Any]:
    summaries = agent.list_runs(limit=limit)
    run_ids = [item.get("run_id") for item in summaries if item.get("run_id")]

    runs: List[Dict[str, Any]] = []
    for run_id in run_ids:
        details = agent.get_run(str(run_id))
        if details is not None:
            runs.append(details)

    output_dir = os.path.dirname(output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    if output_format == "jsonl":
        with open(output, "w", encoding="utf-8") as fp:
            for run in runs:
                fp.write(json.dumps(run, ensure_ascii=True))
                fp.write("\n")
    else:
        with open(output, "w", encoding="utf-8") as fp:
            json.dump(
                {
                    "exported_at": _utc_now_iso(),
                    "storage_backend": agent.storage_backend(),
                    "storage_target": agent.storage_target_safe(),
                    "run_count": len(runs),
                    "runs": runs,
                },
                fp,
                ensure_ascii=True,
                indent=2,
            )

    return {
        "run_count": len(runs),
        "output": output,
        "format": output_format,
    }


def build_parser() -> argparse.ArgumentParser:
    default_legacy = os.path.join(SCRIPT_DIR, "logs", "audit_events.jsonl")
    default_export = os.path.join(SCRIPT_DIR, "data", "audit_export.json")

    parser = argparse.ArgumentParser(description="Meta-agent audit migration and export utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    migrate_parser = subparsers.add_parser("migrate", help="Migrate legacy JSONL logs into database tables")
    migrate_parser.add_argument("--source", default=default_legacy, help="Path to legacy JSONL file")
    migrate_parser.add_argument(
        "--force-reimport",
        action="store_true",
        help="Re-import runs even if run_id already exists in database",
    )

    export_parser = subparsers.add_parser("export", help="Export audit runs from database")
    export_parser.add_argument("--output", default=default_export, help="Output file path")
    export_parser.add_argument("--limit", type=int, default=200, help="Maximum number of runs to export")
    export_parser.add_argument("--format", choices=["json", "jsonl"], default="json", help="Export file format")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    agent = MetaAgent()
    print(f"Storage backend: {agent.storage_backend()} ({agent.storage_target_safe()})")

    if args.command == "migrate":
        stats = migrate_legacy_jsonl(
            agent=agent,
            source=args.source,
            skip_existing=not args.force_reimport,
        )
        print("Migration complete.")
        print(json.dumps(stats, ensure_ascii=True, indent=2))
        if stats["runs_found"] == 0:
            print("No legacy log file or no legacy records found. Nothing to migrate.")
        return 0

    if args.command == "export":
        result = export_runs(
            agent=agent,
            output=args.output,
            limit=max(1, int(args.limit)),
            output_format=args.format,
        )
        print("Export complete.")
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
