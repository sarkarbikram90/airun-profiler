"""Core Tracer SDK for instrumenting AI workflows, LLM calls, and agent steps."""

from __future__ import annotations

import asyncio
import functools
import inspect
import os
import sys
import traceback
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from airun.events.models import SpanKind, SpanStatus, TraceRecord, TraceSpan
from airun.pricing.engine import calculate_cost
from airun.sdk.context import (
    get_collected_spans,
    get_current_span,
    get_current_span_id,
    get_current_trace_id,
    pop_span,
    push_span,
    reset_trace_context,
    set_current_trace_id,
)
from airun.sdk.redaction import redact_data
from airun.store import get_trace_store
from airun.utils.time_utils import now_utc_iso, perf_counter_ms


class TraceContext:
    """Context manager and async context manager for profiling execution spans."""

    def __init__(
        self,
        name: str,
        kind: Union[SpanKind, str] = SpanKind.CUSTOM,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        save_on_exit: bool = True,
    ):
        self.name = name
        self.kind = SpanKind(kind) if isinstance(kind, str) else kind
        self.provider = provider
        self.model = model
        self.metadata = metadata or {}
        self.explicit_trace_id = trace_id
        self.save_on_exit = save_on_exit

        self.span: Optional[TraceSpan] = None
        self._start_perf: float = 0.0
        self._is_root: bool = False

    def __enter__(self) -> TraceSpan:
        current_trace_id = get_current_trace_id()
        if current_trace_id is None:
            self._is_root = True
            current_trace_id = self.explicit_trace_id or uuid.uuid4().hex
            set_current_trace_id(current_trace_id)

        parent_id = get_current_span_id()
        span_id = uuid.uuid4().hex

        self._start_perf = perf_counter_ms()
        self.span = TraceSpan(
            trace_id=current_trace_id,
            span_id=span_id,
            parent_id=parent_id,
            name=self.name,
            kind=self.kind,
            start_time=now_utc_iso(),
            status=SpanStatus.SUCCESS,
            provider=self.provider,
            model=self.model,
            metadata=redact_data(self.metadata),
        )

        push_span(self.span)
        return self.span

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if not self.span:
            return False

        end_perf = perf_counter_ms()
        self.span.duration_ms = round(max(0.0, end_perf - self._start_perf), 2)
        self.span.end_time = now_utc_iso()

        if exc_val is not None:
            if isinstance(exc_val, (TimeoutError, asyncio.TimeoutError)):
                self.span.status = SpanStatus.TIMEOUT
            else:
                self.span.status = SpanStatus.FAILURE

            self.span.error = {
                "type": exc_type.__name__ if exc_type else "Exception",
                "message": str(exc_val),
                "traceback": "".join(traceback.format_exception(exc_type, exc_val, exc_tb))[-1000:],
            }

        # Calculate cost if not explicitly set
        if self.span.cost_usd is None and self.span.model:
            self.span.cost_usd = calculate_cost(
                model=self.span.model,
                input_tokens=self.span.tokens_input,
                output_tokens=self.span.tokens_output,
                duration_ms=self.span.duration_ms,
            )

        pop_span()

        if self._is_root:
            if self.save_on_exit:
                self._finalize_and_save()
            else:
                reset_trace_context()

        # Do not suppress exception
        return False

    async def __aenter__(self) -> TraceSpan:
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        return self.__exit__(exc_type, exc_val, exc_tb)

    def _finalize_and_save(self) -> None:
        try:
            spans = get_collected_spans()
            if spans:
                trace_id = spans[0].trace_id
                record = TraceRecord(
                    trace_id=trace_id,
                    created_at=spans[0].start_time,
                    spans=spans,
                )
                store = get_trace_store()
                store.save_trace(record)

                trace_file_env = os.environ.get("AIRUN_TRACE_ID_FILE")
                if trace_file_env:
                    p = Path(trace_file_env)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(trace_id)

                # OTLP Streaming to Rust Real-Time Data Plane or OTLP collector
                if os.environ.get("AIRUN_OTLP_ENDPOINT") or os.environ.get("AIRUN_OTLP_ENABLED"):
                    try:
                        from airun.exporters.otlp import OTLPSpanExporter
                        exporter = OTLPSpanExporter()
                        exporter.export(record)
                    except Exception as export_err:
                        sys.stderr.write(f"[airun] OTLP export warning: {export_err}\n")
        except Exception as e:
            # Zero-crash guarantee: never fail host application
            sys.stderr.write(f"[airun] Error saving trace: {e}\n")
        finally:
            reset_trace_context()


def trace(
    name_or_func: Optional[Union[str, Callable]] = None,
    *,
    kind: Union[SpanKind, str] = SpanKind.CUSTOM,
    name: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    save_on_exit: bool = True,
) -> Any:
    """
    Universal tracing primitive.

    Can be used as:
    1. Decorator:
       @trace(kind="llm", model="gpt-4o")
       def call_llm(prompt): ...

       @trace
       def my_step(): ...

    2. Context manager:
       with trace("step_name", kind="tool"): ...
       async with trace("async_step", kind="llm"): ...
    """
    # Case 1: Bare decorator @trace without parentheses
    if callable(name_or_func):
        func = name_or_func
        span_name = func.__name__

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with TraceContext(
                    name=span_name,
                    kind=kind,
                    provider=provider,
                    model=model,
                    metadata=metadata,
                    trace_id=trace_id,
                    save_on_exit=save_on_exit,
                ):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with TraceContext(
                    name=span_name,
                    kind=kind,
                    provider=provider,
                    model=model,
                    metadata=metadata,
                    trace_id=trace_id,
                    save_on_exit=save_on_exit,
                ):
                    return func(*args, **kwargs)

            return sync_wrapper

    # Case 2: String argument for context manager with trace("name", ...)
    if isinstance(name_or_func, str):
        span_name = name_or_func
        return TraceContext(
            name=span_name,
            kind=kind,
            provider=provider,
            model=model,
            metadata=metadata,
            trace_id=trace_id,
            save_on_exit=save_on_exit,
        )

    # Case 3: Decorator with arguments @trace(kind="llm", name=...)
    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with TraceContext(
                    name=span_name,
                    kind=kind,
                    provider=provider,
                    model=model,
                    metadata=metadata,
                    trace_id=trace_id,
                    save_on_exit=save_on_exit,
                ):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with TraceContext(
                    name=span_name,
                    kind=kind,
                    provider=provider,
                    model=model,
                    metadata=metadata,
                    trace_id=trace_id,
                    save_on_exit=save_on_exit,
                ):
                    return func(*args, **kwargs)

            return sync_wrapper

    return decorator


# --- Span Enrichment Utilities ---


def set_span_tokens(
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
) -> None:
    """Set token counts on the active span."""
    span = get_current_span()
    if span:
        if input_tokens is not None:
            span.tokens_input = input_tokens
        if output_tokens is not None:
            span.tokens_output = output_tokens


def set_span_cost(cost_usd: float) -> None:
    """Explicitly set USD cost on the active span."""
    span = get_current_span()
    if span:
        span.cost_usd = cost_usd


def set_span_model(model: str, provider: Optional[str] = None) -> None:
    """Set model name and provider on the active span."""
    span = get_current_span()
    if span:
        span.model = model
        if provider:
            span.provider = provider


def set_span_status(status: Union[SpanStatus, str]) -> None:
    """Update execution status of the active span."""
    span = get_current_span()
    if span:
        span.status = SpanStatus(status) if isinstance(status, str) else status


def record_retry() -> None:
    """Increment retry counter on the active span."""
    span = get_current_span()
    if span:
        span.retry_count += 1
        span.status = SpanStatus.RETRY


def set_span_metadata(key_or_dict: Union[str, Dict[str, Any]], value: Any = None) -> None:
    """Attach custom metadata to the active span (auto-redacted)."""
    span = get_current_span()
    if not span:
        return
    if isinstance(key_or_dict, dict):
        sanitized = redact_data(key_or_dict)
        span.metadata.update(sanitized)
    elif isinstance(key_or_dict, str):
        sanitized_val = redact_data(value)
        span.metadata[key_or_dict] = sanitized_val


def set_span_quality(score: float, metrics: Optional[Dict[str, Any]] = None) -> None:
    """Attach evaluation / quality score (0.0 - 1.0) and optional metrics to the active span."""
    span = get_current_span()
    if span:
        span.quality_score = score
        if metrics:
            span.evaluation_metrics.update(redact_data(metrics))
