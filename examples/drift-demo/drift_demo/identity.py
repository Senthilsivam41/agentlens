"""Identity stamped on every demo trace and the imported baseline.

The executions list and the baselines table both render agent name and
environment, so these two values are the customer-visible demo label.
"""

AGENT_NAME = "demo-support-agent"
AGENT_VERSION = "1.0.0"
ENVIRONMENT = "demo"
TENANT_ID = "local"
SERVICE_NAME = "demo-support-agent"

DASHBOARD_FILTER = (
    f"/executions?agent_name={AGENT_NAME}&environment={ENVIRONMENT}"
)
