CREATE DATABASE IF NOT EXISTS default;

-- 1. Table for computed mathematical metrics from DuckDB/Python
CREATE TABLE IF NOT EXISTS default.agent_drift_metrics
(
    ExecutionDate Date,
    TraceId String,
    UserPrompt String,
    MahalanobisDistance Float64,
    InputAmbiguityScore Float64,
    TrajectoryVolatility Float64,
    IsDrifted UInt8,
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
ORDER BY (ExecutionDate, RootCauseCategory, TraceId);
