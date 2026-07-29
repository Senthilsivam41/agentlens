# Agentic AI Observability & Mathematical Drift Platform
## Architecture Specification & Architecture Decision Records (ADR)

**Author:** Principal Solution Architect  
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
```

### 2.1 Component Layer Responsibilities

| Layer | Technology | Primary Responsibility |
| :--- | :--- | :--- |
| **Agent Orchestration** | LangGraph, CrewAI, Python | Executes multi-step agent graphs, tool calling, and RAG retrieval auto-instrumented with OpenInference OTel SDKs. |
| **Telemetry Ingestion** | OTel Collector Contrib | Receives OTLP gRPC/HTTP span streams, batches records, and executes high-speed bulk inserts into ClickHouse. |
| **OLAP Data Lake** | ClickHouse DB | Stores high-cardinality raw trace spans, vector embeddings, token counts, and computed daily drift metrics in MergeTree tables. |
| **Batch Math Engine** | DuckDB, NumPy, SciPy | Executes nightly vector linear algebra jobs ($D_M$, $H_{\text{amb}}$, $V_{\text{traj}}$) across daily trace datasets. |
| **API & Prompt Engine** | FastAPI, LangChain/Instructor | Translates natural language queries into ClickHouse SQL, computes executive narrative summaries, and handles metric tuning requests. |
| **Presentation Layer** | Next.js, Tailwind, Recharts | Serves executive dashboards, live parameter tuning sliders, LaTeX math explainers, and daily automated prescription cards. |

---

## 3. Mathematical Drift Formulations

To evaluate agent executions deterministically without incurring LLM API costs, the system computes three mathematical indices per execution trace:

### 3.1 Trajectory Vector Distance ($D_M$)
Measures structural and semantic deviation from a "Golden Baseline" cluster of successful executions. The trajectory vector $\mathbf{x} = [\mathbf{e}_{\text{out}} \,\|\, \mathbf{w}_{\text{path}}]$ concatenates the response text embedding $\mathbf{e}_{\text{out}} \in \mathbb{R}^d$ and normalized tool call weights $\mathbf{w}_{\text{path}} \in \mathbb{R}^m$.

$$D_M(\mathbf{x}) = \sqrt{(\mathbf{x} - \boldsymbol{\mu}_g)^T \boldsymbol{\Sigma}_g^{-1} (\mathbf{x} - \boldsymbol{\mu}_g)}$$

*   Where $\boldsymbol{\mu}_g$ is the mean vector of the Golden Baseline cluster and $\boldsymbol{\Sigma}_g^{-1}$ is the inverse covariance matrix with pseudo-inverse regularization ($+ 10^{-6}\mathbf{I}$) to handle singularity.
*   **Drift Flag Rule:** An execution is flagged as drifted if $D_M(\mathbf{x}) > \mu_D + k \cdot \sigma_D$.

### 3.2 User Input Ambiguity & Context Entropy ($H_{\text{amb}}$)
Isolates whether an execution drift was caused by user prompt ambiguity or internal agent logic errors:

$$H_{\text{amb}}(Q) = -\sum_{i=1}^{N} P(x_i) \log_2 P(x_i) + \alpha \cdot \left(1 - \frac{1}{m}\sum_{j=1}^{m} \cos(\mathbf{q}, \mathbf{c}_j)\right)$$

*   Where $P(x_i)$ is token frequency distribution over input query $Q$, $\mathbf{q}$ is the query vector embedding, $\mathbf{c}_j$ are centroid vectors of standard intent clusters, and $\alpha$ is a scaling factor.
*   **Root Cause Rule:** If $D_M(\mathbf{x})$ is high **AND** $H_{\text{amb}}(Q) > H_{\text{threshold}}$, the root cause is tagged as **User Prompt Ambiguity**. If $H_{\text{amb}}(Q)$ is low, it is tagged as an **Agent Model Failure**.

### 3.3 Trajectory Volatility Index ($V_{\text{traj}}$)
Quantifies resource churn, infinite tool loops, and retry penalties across the execution graph lifecycle:

$$V_{\text{traj}} = w_s \cdot \left(\frac{N_{\text{steps}}}{\bar{N}}\right)^2 + w_t \cdot \left(\frac{T_{\text{used}}}{\bar{T}}\right) + w_r \cdot \sum_{i=1}^{M} R_i^2$$

*   Where $N_{\text{steps}}$ is the executed node count, $T_{\text{used}}$ is total token consumption, $\bar{N}$ and $\bar{T}$ are baseline averages, and $R_i$ is the retry count for tool $i$.

---

## 4. ClickHouse Data Lake Schema Specification

The database implementation utilizes ClickHouse's `MergeTree` engine optimized for time-series range scans and bulk vector array processing.

```sql
-- 1. Raw OpenTelemetry Spans Table (Ingested via OTel Collector)
CREATE TABLE IF NOT EXISTS default.otel_agent_spans
(
    Timestamp DateTime64(6) CODEC(DoubleDelta, ZSTD),
    TraceId String CODEC(ZSTD),
    SpanId String CODEC(ZSTD),
    ParentSpanId String CODEC(ZSTD),
    SpanName LowCardinality(String),
    ServiceLowCardinality LowCardinality(String),
    
    -- OpenInference Agent Attributes
    GraphNodeName String,
    AgentRole LowCardinality(String),
    ToolName LowCardinality(String),
    InputPrompt String,
    OutputText String,
    
    -- Token & Execution Metrics
    PromptTokens UInt32,
    CompletionTokens UInt32,
    TotalTokens UInt32,
    ExecutionDurationMs Float64,
    RetryCount UInt8,
    
    -- Output Vector Embedding Array (384-dim or 1536-dim)
    ResponseEmbedding Array(Float32)
)
ENGINE = MergeTree()
PRIMARY KEY (ServiceLowCardinality, SpanName)
ORDER BY (ServiceLowCardinality, SpanName, Timestamp, TraceId);

-- 2. Computed Mathematical Drift Metrics Table
CREATE TABLE IF NOT EXISTS default.agent_drift_metrics
(
    ExecutionDate Date,
    TraceId String,
    UserPrompt String,
    
    -- Calculated Metrics
    MahalanobisDistance Float64,  -- D_M
    InputAmbiguityScore Float64,  -- H_amb
    TrajectoryVolatility Float64,  -- V_traj
    
    -- Classification & Waste Tracking
    IsDrifted UInt8,              -- 1 if drifted, 0 if compliant
    RootCauseCategory Enum8(
        'Compliant' = 0, 
        'UserPromptAmbiguity' = 1, 
        'AgentLogicFailure' = 2, 
        'ToolTimeout' = 3
    ),
    EstimatedTokenWaste UInt32,
    CalculatedAt DateTime DEFAULT now()
)
ENGINE = MergeTree()
PRIMARY KEY (ExecutionDate)
RootCauseCategory, TraceId);
```

---

## 5. Non-Functional Requirements & Security Considerations

*   **Ingestion Throughput:** The OTel Collector and ClickHouse setup supports over 25,000 span writes/second with batch processing enabled.
*   **PII & Payload Redaction:** Regex and Named Entity Recognition (NER) processors run in the OTel Collector pipeline to redact sensitive credentials, credit card numbers, and PII before writing spans to ClickHouse.
*   **Data Retention & Lifecycle:** Raw span payloads are retained for 30 days via ClickHouse TTL rules (`TTL Timestamp + INTERVAL 30 DAY`), while aggregated mathematical drift metrics are retained indefinitely for long-term trend analysis.
