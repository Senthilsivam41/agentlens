# ADR-004: Edge Collectors and Shared Backend

**Status:** Accepted

Each Kubernetes cluster runs an edge OTel Collector. Edge collectors enrich, redact, buffer, and forward telemetry over mTLS to a shared regional Agent Lens gateway. The gateway derives tenant and cluster identity from collector credentials and overwrites untrusted workload claims.

