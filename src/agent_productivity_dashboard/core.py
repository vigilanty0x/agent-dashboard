from __future__ import annotations
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any

PROJECT = "agent-productivity-dashboard"
REQUIRED_FIELDS = ["agent","completed","failed","retries","elapsed_ms"]

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def _string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)

def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)

def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def calculate_metrics(record: dict[str, Any]) -> dict[str, Any]:
    if not _text(record["agent"]):
        raise ValueError("agent is required")
    for key in ("completed", "failed", "retries", "elapsed_ms"):
        if not _integer(record[key]) or record[key] < 0:
            raise ValueError("metrics must be non-negative integers")
    total = record["completed"] + record["failed"]
    if total <= 0 or record["elapsed_ms"] <= 0:
        raise ValueError("a measured workload is required")
    reliability = round(record["completed"] / total, 6)
    throughput_per_hour = round(record["completed"] * 3_600_000 / record["elapsed_ms"], 6)
    return {"agent": record["agent"], "total": total, "reliability": reliability, "throughput_per_hour": throughput_per_hour, "retries": record["retries"]}

def evaluate(record: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    artifact: Any = None
    if missing:
        status = "blocked"
        reason = "missing required fields: " + ", ".join(missing)
    else:
        try:
            artifact = calculate_metrics(record)
            status = "passed"
            reason = "calculate_metrics completed"
        except (TypeError, ValueError, KeyError) as exc:
            status = "failed"
            reason = str(exc)
    receipt = {"project": PROJECT, "status": status, "reason": reason, "record": record, "metrics": artifact}
    receipt["evidence_sha256"] = sha256(_canonical(receipt).encode()).hexdigest()
    return receipt

