# ADR-007: Adaptive Semantic Sampling

**Status:** Accepted

Structural scoring covers every eligible execution. The sampler supports
error/timeout, high-volatility, unknown-path, new-version, and deterministic
normal-traffic triggers. In the current alpha worker, only error/timeout,
high-volatility, and deterministic normal inputs are wired because known-path
and known-version sets are not yet sourced by the assembly loop. Every score
stores sampling policy and reason; the API reports aggregate semantic coverage
until a future versioned schema adds per-score coverage.

