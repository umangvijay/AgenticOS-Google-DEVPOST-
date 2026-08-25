"""
AgentOS — Circuit Breaker

State machine per MCP/tool to prevent cascading failures
when upstream APIs go down.

States:
    CLOSED    → Normal operation. Failures counted.
    OPEN      → Upstream is down. All requests fail-fast.
    HALF_OPEN → Testing recovery. One request allowed through.

CLOSED ──(N consecutive failures)──▶ OPEN
   ▲                                    │
   │                           (timeout expires)
   │                                    ▼
   └──────(test succeeds)────── HALF_OPEN
                                     │
                              (test fails)
                                     ▼
                                   OPEN
"""

import time
import logging
from enum import Enum
from typing import Dict, Optional, Any
from threading import Lock
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class BreakerState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class BreakerConfig:
    """Per-tool circuit breaker configuration."""
    failure_threshold: int = 5          # Consecutive failures to trip
    failure_window_seconds: int = 60    # Window for counting failures
    recovery_timeout_seconds: int = 300  # 5 min in OPEN before testing
    half_open_max_requests: int = 1     # Test requests allowed in HALF_OPEN


@dataclass
class BreakerRecord:
    """State for a single circuit breaker."""
    state: BreakerState = BreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    opened_at: float = 0.0
    half_open_requests: int = 0
    config: BreakerConfig = field(default_factory=BreakerConfig)

    # Stats
    total_successes: int = 0
    total_failures: int = 0
    total_rejected: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is OPEN."""
    def __init__(self, mcp_id: str, message: str):
        self.mcp_id = mcp_id
        super().__init__(message)


class CircuitBreaker:
    """
    Thread-safe circuit breaker registry.

    Usage:
        breaker = CircuitBreaker()

        # Before calling an MCP tool:
        if not breaker.allow_request(mcp_id):
            raise CircuitBreakerError(mcp_id, "upstream down")

        # After a successful call:
        breaker.record_success(mcp_id)

        # After a failed call:
        breaker.record_failure(mcp_id)
    """

    def __init__(self):
        self._lock = Lock()
        self._breakers: Dict[str, BreakerRecord] = {}

    def _get_or_create(self, mcp_id: str) -> BreakerRecord:
        """Get or create a breaker record for an MCP."""
        if mcp_id not in self._breakers:
            self._breakers[mcp_id] = BreakerRecord()
        return self._breakers[mcp_id]

    def allow_request(self, mcp_id: str) -> bool:
        """
        Check if a request is allowed through the breaker.

        Returns True if allowed, False if rejected (OPEN state).
        Handles automatic OPEN → HALF_OPEN transition on timeout.
        """
        with self._lock:
            breaker = self._get_or_create(mcp_id)
            now = time.time()

            if breaker.state == BreakerState.CLOSED:
                return True

            elif breaker.state == BreakerState.OPEN:
                # Check if recovery timeout has elapsed
                elapsed = now - breaker.opened_at
                if elapsed >= breaker.config.recovery_timeout_seconds:
                    # Transition to HALF_OPEN
                    breaker.state = BreakerState.HALF_OPEN
                    breaker.half_open_requests = 0
                    logger.info(
                        f"[CIRCUIT_BREAKER] {mcp_id}: OPEN → HALF_OPEN "
                        f"(after {int(elapsed)}s)"
                    )
                    return True
                else:
                    # Still OPEN — reject
                    breaker.total_rejected += 1
                    remaining = int(breaker.config.recovery_timeout_seconds - elapsed)
                    logger.debug(
                        f"[CIRCUIT_BREAKER] {mcp_id}: OPEN — rejected "
                        f"(retry in {remaining}s)"
                    )
                    return False

            elif breaker.state == BreakerState.HALF_OPEN:
                # Allow limited test requests
                if breaker.half_open_requests < breaker.config.half_open_max_requests:
                    breaker.half_open_requests += 1
                    return True
                else:
                    breaker.total_rejected += 1
                    return False

            return True

    def record_success(self, mcp_id: str) -> None:
        """Record a successful request. Resets failure count."""
        with self._lock:
            breaker = self._get_or_create(mcp_id)
            breaker.total_successes += 1

            if breaker.state == BreakerState.HALF_OPEN:
                # Test passed — close the breaker
                breaker.state = BreakerState.CLOSED
                breaker.failure_count = 0
                breaker.half_open_requests = 0
                logger.info(f"[CIRCUIT_BREAKER] {mcp_id}: HALF_OPEN → CLOSED (recovered)")

            elif breaker.state == BreakerState.CLOSED:
                # Reset failure count on success
                breaker.failure_count = 0

    def record_failure(self, mcp_id: str) -> None:
        """Record a failed request. May trip the breaker."""
        with self._lock:
            breaker = self._get_or_create(mcp_id)
            now = time.time()
            breaker.total_failures += 1

            if breaker.state == BreakerState.HALF_OPEN:
                # Test failed — back to OPEN
                breaker.state = BreakerState.OPEN
                breaker.opened_at = now
                breaker.half_open_requests = 0
                logger.warning(
                    f"[CIRCUIT_BREAKER] {mcp_id}: HALF_OPEN → OPEN "
                    f"(recovery test failed)"
                )

            elif breaker.state == BreakerState.CLOSED:
                # Check if failures are within the window
                if now - breaker.last_failure_time > breaker.config.failure_window_seconds:
                    # Outside window — reset count
                    breaker.failure_count = 1
                else:
                    breaker.failure_count += 1

                breaker.last_failure_time = now

                if breaker.failure_count >= breaker.config.failure_threshold:
                    # Trip the breaker
                    breaker.state = BreakerState.OPEN
                    breaker.opened_at = now
                    logger.warning(
                        f"[CIRCUIT_BREAKER] {mcp_id}: CLOSED → OPEN "
                        f"({breaker.failure_count} consecutive failures)"
                    )

    def get_status(self, mcp_id: str) -> Dict[str, Any]:
        """Get the current status of a breaker."""
        with self._lock:
            breaker = self._get_or_create(mcp_id)
            now = time.time()

            result = {
                "mcp_id": mcp_id,
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "total_successes": breaker.total_successes,
                "total_failures": breaker.total_failures,
                "total_rejected": breaker.total_rejected,
            }

            if breaker.state == BreakerState.OPEN:
                elapsed = now - breaker.opened_at
                remaining = max(0, breaker.config.recovery_timeout_seconds - elapsed)
                result["retry_in_seconds"] = int(remaining)

            return result

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all breakers."""
        with self._lock:
            return {
                mcp_id: self.get_status(mcp_id)
                for mcp_id in self._breakers
            }

    def reset(self, mcp_id: str) -> None:
        """Manually reset a breaker (admin action)."""
        with self._lock:
            if mcp_id in self._breakers:
                old_state = self._breakers[mcp_id].state
                self._breakers[mcp_id] = BreakerRecord()
                logger.info(
                    f"[CIRCUIT_BREAKER] {mcp_id}: {old_state.value} → CLOSED (manual reset)"
                )

    def configure(self, mcp_id: str, config: BreakerConfig) -> None:
        """Set custom configuration for a specific MCP breaker."""
        with self._lock:
            breaker = self._get_or_create(mcp_id)
            breaker.config = config


# ── Singleton ─────────────────────────────────────────────────────
circuit_breaker = CircuitBreaker()
