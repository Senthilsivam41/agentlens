# Agentic AI Observability & Mathematical Drift Platform
## Architecture Specification & Architecture Decision Records (ADR)

**Author:** Sendil - Principal Solution Architect  
**Version:** 1.0.0  
**Date:** July 2026  
**Target Stack:** LangGraph, CrewAI, OpenTelemetry, ClickHouse, DuckDB, FastAPI, Next.js  
**Execution Pattern:** Asynchronous Data Lake Batch Processing + In-Flight Mathematical Guardrails  

---

## 1. Architecture Decision Records (ADR)

Before finalizing the technical stack, the following key architectural decisions were evaluated and documented to ensure compliance with enterprise scalability, cost optimization, data sovereignty, and performance constraints.

---

### ADR-001: Asynchronous Vector Trajectory Analytics vs. Real-Time LLM-as-a-Judge

* **Status:** Accepted
* **Context:**
  Agentic AI workflows (built on LangGraph and CrewAI) exhibit non-deterministic multi-step execution paths. Traditional APM monitoring returns `HTTP 200 OK` even when agents fail semantically (e.g., goal drift, hallucinations, tool looping). While "LLM-as-a-judge" evaluation is a popular method for detecting quality failures, running synchronous LLM calls inline adds 1.5–3.0 seconds of latency per execution step and incurs massive SaaS/API bills ($0.03–$0.12 per eval call).
* **Decision:**
  We adopt **asynchronous mathematical trajectory analytics** over daily OpenTelemetry (OTel) trace batches. We calculate high-dimensional vector linear algebra—specifically **Mahalanobis Distance ($D_M$)**, **Shannon Context Entropy ($H_{\text{amb}}$)**, and **Trajectory Volatility ($V_{\text{traj}}$)**—inside DuckDB and Python (NumPy/SciPy).
* **Consequences:**
  * **Positive:** Zero LLM API evaluation costs for batch evaluation; sub-millisecond per-trace mathematical calculation; deterministic, reproducible metric drift scores.
  * **Negative:** Requires an initial "Golden Baseline" dataset of compliant traces to calculate baseline covariance matrices ($\mathbf{\Sigma}_g$).

---

### ADR-002: ClickHouse Columnar OLAP + DuckDB vs. Traditional APM SaaS (Datadog/Dynatrace)

* **Status:** Accepted
* **Context:**
  Standard APM tools (Datadog, Dynatrace, New Relic) are designed for low-cardinality microservice metrics (CPU, RAM, HTTP status, simple spans). Agentic trace payloads include full prompt text histories, tool inputs/outputs, state transition graphs, and high-dimensional float vector array embeddings (e.g., 384-dim or 1536-dim). Ingesting these high-cardinality payloads into commercial APM tools leads to prohibitive logging costs and lacks support for vector array linear algebra.
* **Decision:**
  Deploy **ClickHouse** as the core columnar trace data lake, paired with **DuckDB** for vectorized in-memory batch processing.
* **Consequences:**
  * **Positive:** 10x–30x data compression via ZSTD/DoubleDelta codecs; high-throughput ingestion (>25,000 spans/sec); native support for `Array(Float32)` data types; zero per-GB SaaS log fees.
  * **Negative:** Requires managing self-hosted OLAP infrastructure via Docker/Kubernetes.

---

### ADR-003: OpenTelemetry Collector (Contrib) + OpenInference Semantics vs. Proprietary SDKs

* **Status:** Accepted
* **Context:**
  Proprietary observability SDKs (e.g., LangSmith, Arize Phoenix SaaS) lock application code into specific vendor ecosystems. If the orchestration framework changes or data privacy policies prohibit external SaaS transmission, migrating codebases becomes expensive.
* **Decision:**
  Standardize telemetry collection on the **OpenTelemetry (OTel) Collector Contrib** distribution augmented with **OpenInference** semantic conventions for LangChain, LangGraph, and CrewAI.
* **Consequences:**
  * **Positive:** 100% open standard (W3C TraceContext); framework agnostic; zero vendor lock-in; allows inline PII/credential redaction via OTel Collector processors before storage.
  * **Negative:** Requires configuring OTel Collector pipeline YAML configurations manually.

---

### ADR-004: FastAPI + Instructor Text-to-SQL Prompt Gateway vs. Static Dashboard Queries

* **Status:** Accepted
* **Context:**
  Executive leadership and product owners need ad-hoc insights into agent performance, cost waste, and drift root causes without writing complex ClickHouse SQL queries or navigating intricate PromQL dashboards.
* **Decision:**
  Implement a **FastAPI backend** leveraging **Instructor / LangChain** to provide a natural-language Text-to-SQL translation gateway over the ClickHouse `agent_drift_metrics` table.
* **Consequences:**
  * **Positive:** Non-technical stakeholders can prompt the dashboard directly (e.g., *"Show me total financial waste from ambiguous user queries yesterday"*); generates automated executive summary narratives.
  * **Negative:** Requires LLM API call for prompt-to-SQL translation (cached for identical queries).

---

### ADR-005: Next.js + Tailwind Dashboard with Live Client-Side Sensitivity Tuning

* **Status:** Accepted
* **Context:**
  Fixed metric thresholds (e.g., $2.5\sigma$) are rarely one-size-fits-all across different agent deployment environments. Users need to tune sensitivity knobs live to understand false positive rates and projected cost waste without waiting for batch re-runs.
* **Decision:**
  Build an interactive **Next.js (React)** frontend with live parameter sliders for $k \cdot \sigma$ sensitivity, $H_{\text{threshold}}$ ambiguity limits, and tool retry penalty weights.
* **Consequences:**
  * **Positive:** Real-time visual feedback; instant executive decision support; interactive LaTeX formula explainers embedded directly in metric cards.
  * **Negative:** Demands reactive client-side state management for live metric recalculations.

---

## 2. System Architecture Overview

The platform utilizes a decoupled, layered microservices architecture designed for ultra-high throughput telemetry ingestion and asynchronous analytical processing.

```text
+---------------------------------------------------------------------------------------------------+
|                                  AGENTIC AI SYSTEM ARCHITECTURE                                   |
+---------------------------------------------------------------------------------------------------+
|  +---------------------------+               +---------------------------+                        |
|  |     LangGraph Workflows   |               |       CrewAI Agents       |                        |
|  +---------------------------+               +---------------------------+                        |
|               |                                            |                                      |
|               +----------------------+---------------------+                                      |
|                                      | (OTLP Spans via gRPC / Port 4317)                          |
|                                      v                                                            |
|                    +-----------------------------------+                                          |
|                    |  OpenTelemetry Collector Contrib  |                                          |
|                    +-----------------------------------+                                          |
|                                      | (Native TCP / Port 9000)                                   |
|                                      v                                                            |
|                    +-----------------------------------+                                          |
|                    |     ClickHouse OLAP Data Lake     |                                          |
|                    |  (otel_agent_spans & drift_metrics)|                                         |
|                    +-----------------------------------+                                          |
|                                      ^                                                            |
|                    +-----------------+-----------------+                                          |
|                    |                                   |                                          |
|  +-----------------------------------+   +-----------------------------------+                    |
|  |  Nightly Batch Math Engine        |   |   FastAPI Text-to-SQL Engine      |                    |
|  |  (Python + DuckDB + SciPy/NumPy)  |   |   (OpenAI / Instructor + ClickHouse) |                    |
|  +-----------------------------------+   +-----------------------------------+                    |
|                                                        ^                                          |
|                                                        | (REST API / Port 8000)                   |
|                                          +---------------------------+                            |
|                                          |  Next.js Drift Dashboard  |                            |
|                                          |  (Interactive Controls)   |                            |
|                                          +---------------------------+                            |
+---------------------------------------------------------------------------------------------------+
