//! High-throughput Tri-State Circuit Breaker State Machine Runtime.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, RwLock};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum BreakerState {
    Closed,
    Open,
    HalfOpen,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BreakerConfig {
    pub failure_threshold: u32,
    pub latency_threshold_ms: f32,
    pub recovery_timeout_secs: i64,
}

impl Default for BreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 3,
            latency_threshold_ms: 2500.0,
            recovery_timeout_secs: 30,
        }
    }
}

#[allow(dead_code)]
pub struct CircuitBreaker {
    pub provider: String,
    config: BreakerConfig,
    state: Arc<RwLock<BreakerState>>,
    consecutive_failures: Arc<RwLock<u32>>,
    last_state_change: Arc<RwLock<DateTime<Utc>>>,
}

impl CircuitBreaker {
    pub fn new(provider: String, config: Option<BreakerConfig>) -> Self {
        Self {
            provider,
            config: config.unwrap_or_default(),
            state: Arc::new(RwLock::new(BreakerState::Closed)),
            consecutive_failures: Arc::new(RwLock::new(0)),
            last_state_change: Arc::new(RwLock::new(Utc::now())),
        }
    }

    pub fn state(&self) -> BreakerState {
        let mut state = self.state.write().unwrap();
        if *state == BreakerState::Open {
            let last_change = *self.last_state_change.read().unwrap();
            let elapsed = Utc::now().signed_duration_since(last_change).num_seconds();
            if elapsed >= self.config.recovery_timeout_secs {
                *state = BreakerState::HalfOpen;
                *self.last_state_change.write().unwrap() = Utc::now();
            }
        }
        *state
    }

    #[allow(dead_code)]
    pub fn record_success(&self) {
        let mut state = self.state.write().unwrap();
        let mut failures = self.consecutive_failures.write().unwrap();
        *failures = 0;
        if *state == BreakerState::HalfOpen {
            *state = BreakerState::Closed;
            *self.last_state_change.write().unwrap() = Utc::now();
        }
    }

    pub fn record_failure(&self, latency_ms: f32) -> BreakerState {
        let mut failures = self.consecutive_failures.write().unwrap();
        let mut state = self.state.write().unwrap();

        *failures += 1;
        let should_trip = *failures >= self.config.failure_threshold || latency_ms > self.config.latency_threshold_ms;

        if should_trip {
            *state = BreakerState::Open;
            *self.last_state_change.write().unwrap() = Utc::now();
        }

        *state
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_circuit_breaker_transitions() {
        let breaker = CircuitBreaker::new("openai".into(), Some(BreakerConfig {
            failure_threshold: 2,
            latency_threshold_ms: 1000.0,
            recovery_timeout_secs: 1,
        }));

        assert_eq!(breaker.state(), BreakerState::Closed);
        breaker.record_failure(100.0);
        assert_eq!(breaker.state(), BreakerState::Closed);

        // Trips on second failure
        let state = breaker.record_failure(150.0);
        assert_eq!(state, BreakerState::Open);
        assert_eq!(breaker.state(), BreakerState::Open);
    }
}
