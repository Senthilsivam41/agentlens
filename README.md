
# Agentic AI Mathematical Drift Observability Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Enabled-blue.svg)](https://opentelemetry.io/)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-OLAP-brightgreen.svg)](https://clickhouse.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)

An enterprise-grade, open-source observability platform for **LangGraph** and **CrewAI** agentic AI workflows. This platform measures non-deterministic agent behavioral drift, tool loop volatility, and context ambiguity using high-dimensional vector linear algebra—**without incurring expensive real-time LLM-as-a-judge API costs**.

---

## 🌟 Key Features

- **Deterministic Mathematical Drift Detection:** Calculates Mahalanobis Distance ($D_M$), Shannon Context Entropy ($H_{\text{amb}}$), and Trajectory Volatility ($V_{\text{traj}}$) over daily OpenTelemetry traces.
- **Root Cause Isolation:** Statistically differentiates between vague user prompts (*Context Anomalies*) and actual agent/tool logic failures.
- **Zero-LLM Evaluation Costs:** Runs asynchronous batch vector matrix math in Python, DuckDB, and ClickHouse at scale.
- **Interactive Executive Dashboard:** Next.js UI featuring live parameter tuning sliders ($k \cdot \sigma$ sensitivity controls), mathematical formula explainers, and automated prescription cards.
- **Promptable Text-to-SQL Interface:** Enables non-technical executives to query telemetry data in natural language via FastAPI and Instructor.

---

## 🏗️ Architecture & Tech Stack

```text
[ LangGraph / CrewAI Agents ] 
            │ (OTLP Spans via gRPC :4317)
            ▼
[ OpenTelemetry Collector Contrib ] 
            │ (Native TCP :9000)
            ▼
[ ClickHouse OLAP Data Lake ] ◄───────────┐
            ▲                            │
            │ (Batch Analytics)          │ (Text-to-SQL Queries)
[ DuckDB / SciPy Math Engine ]    [ FastAPI Prompt Engine ]
                                         ▲
                                         │ (REST API :8000)
                              [ Next.js Drift Dashboard ]
```

- **Telemetry Ingestion:** OpenTelemetry Collector (Contrib) with OpenInference semantics.
- **Data Lake & OLAP Storage:** ClickHouse Database.
- **Batch Processing:** DuckDB + NumPy / SciPy (asynchronous vector linear algebra).
- **Backend API:** FastAPI + LangChain / Instructor (Text-to-SQL query engine).
- **Frontend Dashboard:** Next.js + Tailwind CSS + Recharts + WebSockets.

---

## 🚀 Quick Start Guide

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed.
- Python 3.10+ installed.
- An OpenAI API Key (required for the Text-to-SQL prompt feature).

### Step 1: Clone Repository & Setup Environment

```bash
git clone https://github.com/your-org/agentic-drift-dashboard.git
cd agentic-drift-dashboard

# Create .env file
echo "OPENAI_API_KEY=sk-proj-your-actual-api-key" > .env
```

### Step 2: Launch System via Docker Compose

```bash
docker compose up -d --build
```

### Step 3: Verify Container Health

| Service | Endpoint | Expected Result |
| :--- | :--- | :--- |
| **ClickHouse HTTP** | `http://localhost:8123/ping` | Returns `Ok.` |
| **OTel Collector** | `http://localhost:13133/` | Returns `{"status":"Server available"}` |
| **FastAPI Docs** | `http://localhost:8000/docs` | OpenAPI / Swagger Interface |
| **Next.js Dashboard** | `http://localhost:3000` | Interactive Drift Dashboard |

---

## 🐍 Instrumenting LangGraph & CrewAI Agents

To push live trace spans to your local OTel Collector, install the OpenInference packages:

```bash
pip install opentelemetry-sdk opentelemetry-exporter-otlp openinference-instrumentation-langchain openinference-instrumentation-crewai
```

Add the following initialization snippet to your python application startup:

```python
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation.crewai import CrewAIInstrumentor

# 1. Target local Docker OTel Collector
tracer_provider = TracerProvider()
otlp_exporter = OTLPSpanExporter(endpoint="localhost:4317", insecure=True)
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(tracer_provider)

# 2. Activate Auto-Instrumentation
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
CrewAIInstrumentor().instrument(tracer_provider=tracer_provider)
```

---

## 📊 Mathematical Formulas Reference

### 1. Trajectory Distance ($D_M$)
$$D_M(\mathbf{x}) = \sqrt{(\mathbf{x} - \boldsymbol{\mu}_g)^T \boldsymbol{\Sigma}_g^{-1} (\mathbf{x} - \boldsymbol{\mu}_g)}$$

### 2. Context Entropy ($H_{\text{amb}}$)
$$H_{\text{amb}}(Q) = -\sum_{i=1}^{N} P(x_i) \log_2 P(x_i) + \alpha \cdot \left(1 - \frac{1}{m}\sum_{j=1}^{m} \cos(\mathbf{q}, \mathbf{c}_j)\right)$$

### 3. Trajectory Volatility ($V_{\text{traj}}$)
$$V_{\text{traj}} = w_s \cdot \left(\frac{N_{\text{steps}}}{\bar{N}}\right)^2 + w_t \cdot \left(\frac{T_{\text{used}}}{\bar{T}}\right) + w_r \cdot \sum_{i=1}^{M} R_i^2$$

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.
