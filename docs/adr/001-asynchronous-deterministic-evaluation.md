# ADR-001: Asynchronous Deterministic Evaluation

**Status:** Accepted

Agent Lens calculates deterministic trajectory, ambiguity, and volatility signals outside the agent request path. LLM-as-a-judge is excluded from pilot scoring. This avoids added request latency and makes scores reproducible. Semantic embeddings remain an asynchronous, metered dependency.

