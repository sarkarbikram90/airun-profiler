"""The AI Breaker Box: Resilient Circuit Breakers for AI Model Providers.

Implements the SPECIFICATION.md requirement:
"The 'AI Breaker' Box:
Just like a circuit breaker in software prevents cascading failures,
airun detects when an LLM is hallucinating, timing out, or failing and
automatically cuts it off, routing to a cached response or a fallback model."
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal operation: requests routed to this provider
    OPEN = "open"  # Tripped: failures exceeded threshold, calls routed to fallback
    HALF_OPEN = "half_open"  # Trial canary: probe request dispatched to test recovery


class BreakerConfig(BaseModel):
    """Thresholds determining when the AI breaker trips and recovers."""

    failure_threshold: int = 3  # Consecutive errors to trip breaker
    latency_threshold_ms: float = 2500.0  # P95 response delay tripping breaker
    quality_threshold: float = 0.70  # Minimum semantic quality before trip
    recovery_timeout_sec: float = 30.0  # Cooldown period before trying canary
    half_open_success_needed: int = 2  # Successes needed to restore CLOSED state


class BreakerStatus(BaseModel):
    """Current health and telemetry status of an AI Breaker."""

    provider: str
    state: CircuitState
    consecutive_failures: int
    consecutive_successes: int
    trip_count: int
    last_trip_reason: Optional[str] = None
    last_trip_timestamp: Optional[float] = None
    avg_latency_ms: float = 0.0
    avg_quality_score: float = 1.0


class AIBreaker:
    """Circuit breaker protecting workloads from AI provider outages, latency, and drift."""

    def __init__(self, provider: str, config: Optional[BreakerConfig] = None):
        self.provider = provider.lower()
        self.config = config or BreakerConfig()
        self.state: CircuitState = CircuitState.CLOSED
        self.consecutive_failures: int = 0
        self.consecutive_successes: int = 0
        self.trip_count: int = 0
        self.last_trip_reason: Optional[str] = None
        self.last_trip_time: Optional[float] = None
        self._latencies: List[float] = []
        self._qualities: List[float] = []

    def can_execute(self) -> bool:
        """Returns True if the provider is healthy or ready for canary test."""
        now = time.time()

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery cooldown period has elapsed
            if (
                self.last_trip_time
                and (now - self.last_trip_time) >= self.config.recovery_timeout_sec
            ):
                self.state = CircuitState.HALF_OPEN
                self.consecutive_successes = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False

    def trip(self, reason: str) -> None:
        """Manually or automatically trip the circuit breaker into OPEN state."""
        self.state = CircuitState.OPEN
        self.trip_count += 1
        self.last_trip_reason = reason
        self.last_trip_time = time.time()
        self.consecutive_failures = 0
        self.consecutive_successes = 0

    def record_success(self, latency_ms: float, quality_score: Optional[float] = None) -> None:
        """Record successful completion of an inference call."""
        self._latencies.append(latency_ms)
        if len(self._latencies) > 50:
            self._latencies.pop(0)

        if quality_score is not None:
            self._qualities.append(quality_score)
            if len(self._qualities) > 50:
                self._qualities.pop(0)

            # Check if quality degraded severely below threshold
            if quality_score < self.config.quality_threshold:
                self.trip(
                    f"Semantic quality degradation: score {quality_score:.2f} < threshold {self.config.quality_threshold:.2f}"
                )
                return

        # Check if latency exceeds acceptable ceiling
        if latency_ms > self.config.latency_threshold_ms:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.config.failure_threshold:
                self.trip(
                    f"High latency spike: {latency_ms:.0f}ms > threshold {self.config.latency_threshold_ms:.0f}ms"
                )
                return
        else:
            self.consecutive_failures = 0

        if self.state == CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.config.half_open_success_needed:
                # Fully recovered
                self.state = CircuitState.CLOSED
                self.consecutive_successes = 0
                self.last_trip_reason = None

    def record_failure(self, error_message: str) -> None:
        """Record an API timeout, 5xx server error, rate limit, or tool exception."""
        self.consecutive_failures += 1
        self.consecutive_successes = 0

        if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
            if (
                self.consecutive_failures >= self.config.failure_threshold
                or self.state == CircuitState.HALF_OPEN
            ):
                self.trip(f"Provider failure: {error_message}")

    def get_status(self) -> BreakerStatus:
        """Returns structured status snapshot."""
        avg_lat = (sum(self._latencies) / len(self._latencies)) if self._latencies else 0.0
        avg_q = (sum(self._qualities) / len(self._qualities)) if self._qualities else 1.0
        return BreakerStatus(
            provider=self.provider,
            state=self.state,
            consecutive_failures=self.consecutive_failures,
            consecutive_successes=self.consecutive_successes,
            trip_count=self.trip_count,
            last_trip_reason=self.last_trip_reason,
            last_trip_timestamp=self.last_trip_time,
            avg_latency_ms=round(avg_lat, 1),
            avg_quality_score=round(avg_q, 3),
        )


class ResilienceManager:
    """Manages circuit breakers across providers and orchestrates automatic failover."""

    def __init__(self):
        self._breakers: Dict[str, AIBreaker] = {
            "openai": AIBreaker("openai"),
            "anthropic": AIBreaker("anthropic"),
            "google": AIBreaker("google"),
            "meta": AIBreaker("meta"),
            "local": AIBreaker("local"),
        }

    def get_breaker(self, provider: str) -> AIBreaker:
        prov = provider.lower()
        if prov not in self._breakers:
            self._breakers[prov] = AIBreaker(prov)
        return self._breakers[prov]

    def select_healthy_provider(
        self,
        primary: str = "openai",
        secondary: str = "anthropic",
        emergency: str = "google",
        fallback: str = "local",
    ) -> str:
        """
        Walks the priority continuity chain and returns the first healthy provider.
        Priority: Primary -> Secondary -> Emergency -> Local Fallback.
        """
        chain = [primary, secondary, emergency, fallback]
        for prov in chain:
            breaker = self.get_breaker(prov)
            if breaker.can_execute():
                return prov

        # All tripped, fallback to local
        return fallback

    def get_all_statuses(self) -> List[BreakerStatus]:
        """Returns status for all registered provider breakers."""
        return [b.get_status() for b in self._breakers.values()]


_DEFAULT_RESILIENCE: Optional[ResilienceManager] = None


def get_resilience_manager() -> ResilienceManager:
    global _DEFAULT_RESILIENCE
    if _DEFAULT_RESILIENCE is None:
        _DEFAULT_RESILIENCE = ResilienceManager()
    return _DEFAULT_RESILIENCE
