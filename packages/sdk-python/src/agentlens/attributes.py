"""Canonical AgentLens attribute keys (OpenInference addendum)."""

from __future__ import annotations

# Resource attributes
AGENT_NAME = "agentlens.agent.name"
AGENT_VERSION = "agentlens.agent.version"
AGENT_ID = "agentlens.agent.id"
FRAMEWORK = "agentlens.framework"
BASELINE_REF = "agentlens.baseline_ref"
TENANT_ID = "agentlens.tenant_id"
CLUSTER_ID = "agentlens.cluster_id"
IDENTITY_SOURCE = "agentlens.identity_source"

# Span attributes
RUN_ID = "agentlens.run.id"
TOOL_NAME = "tool.name"
TOOL_CALL_ID = "agentlens.tool.call_id"

# OpenInference / GenAI aliases commonly seen on the wire
OPENINFERENCE_TOOL_NAME = "openinference.tool.name"
GEN_AI_TOOL_NAME = "gen_ai.tool.name"
GEN_AI_AGENT_NAME = "gen_ai.agent.name"
GEN_AI_AGENT_ID = "gen_ai.agent.id"
