"""SQLite storage implementation for traces and execution spans."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from airun.analysis.analyzer import analyze_spans
from airun.events.models import SpanKind, SpanStatus, TraceRecord, TraceSpan, TraceSummary
from airun.store.base import TraceStore
from airun.utils.time_utils import now_utc_iso


class SQLiteTraceStore(TraceStore):
    """Local SQLite backend for storing and querying traces."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            with conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS traces (
                        trace_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        outcome TEXT NOT NULL,
                        duration_ms REAL NOT NULL,
                        critical_path_ms REAL NOT NULL,
                        cost_usd REAL NOT NULL,
                        total_tokens INTEGER NOT NULL,
                        span_count INTEGER NOT NULL,
                        summary_json TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS spans (
                        span_id TEXT PRIMARY KEY,
                        trace_id TEXT NOT NULL,
                        parent_id TEXT,
                        name TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        duration_ms REAL,
                        status TEXT NOT NULL,
                        provider TEXT,
                        model TEXT,
                        tokens_input INTEGER,
                        tokens_output INTEGER,
                        cost_usd REAL,
                        retry_count INTEGER DEFAULT 0,
                        error_json TEXT,
                        metadata_json TEXT,
                        span_order INTEGER NOT NULL,
                        FOREIGN KEY(trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_spans_trace_id ON spans(trace_id);
                    CREATE INDEX IF NOT EXISTS idx_traces_created_at ON traces(created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_traces_outcome ON traces(outcome);
                    """
                )
        finally:
            conn.close()

    def save_trace(self, trace_record: TraceRecord) -> None:
        if not trace_record.spans:
            return

        summary = trace_record.summary or analyze_spans(trace_record.spans)
        trace_record.summary = summary

        conn = self._get_connection()
        try:
            with conn:
                # Insert or replace trace record
                conn.execute(
                    """
                    INSERT OR REPLACE INTO traces (
                        trace_id, name, created_at, outcome, duration_ms,
                        critical_path_ms, cost_usd, total_tokens, span_count, summary_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trace_record.trace_id,
                        summary.name,
                        trace_record.created_at or now_utc_iso(),
                        summary.outcome.value,
                        summary.total_duration_ms,
                        summary.critical_path_ms,
                        summary.total_cost_usd,
                        summary.total_tokens,
                        len(trace_record.spans),
                        summary.model_dump_json(),
                    ),
                )

                # Delete old spans if re-saving trace
                conn.execute("DELETE FROM spans WHERE trace_id = ?", (trace_record.trace_id,))

                # Bulk insert all spans
                span_rows = [
                    (
                        span.span_id,
                        span.trace_id,
                        span.parent_id,
                        span.name,
                        span.kind.value if hasattr(span.kind, "value") else str(span.kind),
                        span.start_time,
                        span.end_time,
                        span.duration_ms,
                        span.status.value
                        if hasattr(span.status, "value")
                        else str(span.status),
                        span.provider,
                        span.model,
                        span.tokens_input,
                        span.tokens_output,
                        span.cost_usd,
                        span.retry_count,
                        json.dumps(span.error) if span.error else None,
                        json.dumps(span.metadata) if span.metadata else "{}",
                        order,
                    )
                    for order, span in enumerate(trace_record.spans)
                ]
                conn.executemany(
                    """
                    INSERT INTO spans (
                        span_id, trace_id, parent_id, name, kind, start_time, end_time,
                        duration_ms, status, provider, model, tokens_input, tokens_output,
                        cost_usd, retry_count, error_json, metadata_json, span_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    span_rows,
                )
        finally:
            conn.close()

    def get_trace(self, trace_id: str) -> Optional[TraceRecord]:
        conn = self._get_connection()
        try:
            trace_row = conn.execute(
                "SELECT * FROM traces WHERE trace_id = ?", (trace_id,)
            ).fetchone()

            if not trace_row and len(trace_id) < 32:
                # Support convenient prefix lookup
                trace_row = conn.execute(
                    "SELECT * FROM traces WHERE trace_id LIKE ? ORDER BY created_at DESC LIMIT 1",
                    (f"{trace_id}%",),
                ).fetchone()

            if not trace_row:
                return None

            actual_trace_id = trace_row["trace_id"]
            summary = TraceSummary.model_validate_json(trace_row["summary_json"])

            span_rows = conn.execute(
                "SELECT * FROM spans WHERE trace_id = ? ORDER BY span_order ASC",
                (actual_trace_id,),
            ).fetchall()

            spans: List[TraceSpan] = []
            for r in span_rows:
                spans.append(
                    TraceSpan(
                        trace_id=r["trace_id"],
                        span_id=r["span_id"],
                        parent_id=r["parent_id"],
                        name=r["name"],
                        kind=SpanKind(r["kind"]),
                        start_time=r["start_time"],
                        end_time=r["end_time"],
                        duration_ms=r["duration_ms"],
                        status=SpanStatus(r["status"]),
                        provider=r["provider"],
                        model=r["model"],
                        tokens_input=r["tokens_input"],
                        tokens_output=r["tokens_output"],
                        cost_usd=r["cost_usd"],
                        retry_count=r["retry_count"] or 0,
                        error=json.loads(r["error_json"]) if r["error_json"] else None,
                        metadata=json.loads(r["metadata_json"]) if r["metadata_json"] else {},
                    )
                )

            return TraceRecord(
                trace_id=actual_trace_id,
                created_at=trace_row["created_at"],
                spans=spans,
                summary=summary,
            )
        finally:
            conn.close()

    def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[SpanStatus] = None,
    ) -> List[TraceSummary]:
        conn = self._get_connection()
        try:
            if status:
                rows = conn.execute(
                    """
                    SELECT summary_json FROM traces
                    WHERE outcome = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (status.value, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT summary_json FROM traces
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()

            summaries: List[TraceSummary] = []
            for r in rows:
                summaries.append(TraceSummary.model_validate_json(r["summary_json"]))
            return summaries
        finally:
            conn.close()

    def delete_trace(self, trace_id: str) -> bool:
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute("DELETE FROM traces WHERE trace_id = ?", (trace_id,))
                conn.execute("DELETE FROM spans WHERE trace_id = ?", (trace_id,))
                return cursor.rowcount > 0
        finally:
            conn.close()

    def clear_all(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM spans")
                conn.execute("DELETE FROM traces")
        finally:
            conn.close()
