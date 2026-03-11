-- Athena Queries for Bedrock Server-Side Usage Tracking
-- Database: bedrock_invocations (created by Glue crawler)

-- ============================================================================
-- Query 1: Total usage by user (last 30 days)
-- ============================================================================
SELECT
    json_extract_scalar(requestmetadata, '$.userId') AS user_id,
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    json_extract_scalar(requestmetadata, '$.department') AS department,
    COUNT(*) AS invocation_count,
    SUM(CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER)) AS input_tokens,
    SUM(CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)) AS output_tokens,
    SUM(
        CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) +
        CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)
    ) AS total_tokens
FROM invocations
WHERE accountid = '477205238526'
    AND from_iso8601_timestamp(timestamp) >= current_date - interval '30' day
    AND requestmetadata IS NOT NULL
GROUP BY
    json_extract_scalar(requestmetadata, '$.userId'),
    json_extract_scalar(requestmetadata, '$.tenant'),
    json_extract_scalar(requestmetadata, '$.department')
ORDER BY total_tokens DESC;

-- ============================================================================
-- Query 2: Usage by tenant (daily breakdown)
-- ============================================================================
SELECT
    date_trunc('day', from_iso8601_timestamp(timestamp)) AS day,
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    COUNT(*) AS invocation_count,
    SUM(
        CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) +
        CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)
    ) AS total_tokens,
    AVG(
        CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) +
        CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)
    ) AS avg_tokens_per_call
FROM invocations
WHERE accountid = '477205238526'
    AND from_iso8601_timestamp(timestamp) >= current_date - interval '7' day
    AND requestmetadata IS NOT NULL
GROUP BY
    date_trunc('day', from_iso8601_timestamp(timestamp)),
    json_extract_scalar(requestmetadata, '$.tenant')
ORDER BY day DESC, tenant;

-- ============================================================================
-- Query 3: Department-level usage (for cost allocation)
-- ============================================================================
SELECT
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    json_extract_scalar(requestmetadata, '$.department') AS department,
    COUNT(DISTINCT json_extract_scalar(requestmetadata, '$.userId')) AS unique_users,
    COUNT(*) AS invocation_count,
    SUM(CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER)) AS input_tokens,
    SUM(CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)) AS output_tokens,
    SUM(
        CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) +
        CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)
    ) AS total_tokens,
    -- Cost calculation (Claude 3.5 Sonnet pricing)
    ROUND(
        (SUM(CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER)) * 3.00 / 1000000.0) +
        (SUM(CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)) * 15.00 / 1000000.0),
        4
    ) AS estimated_cost_usd
FROM invocations
WHERE accountid = '477205238526'
    AND from_iso8601_timestamp(timestamp) >= current_date - interval '30' day
    AND requestmetadata IS NOT NULL
GROUP BY
    json_extract_scalar(requestmetadata, '$.tenant'),
    json_extract_scalar(requestmetadata, '$.department')
ORDER BY total_tokens DESC;

-- ============================================================================
-- Query 4: User quota tracking (monthly usage vs limits)
-- ============================================================================
WITH user_usage AS (
    SELECT
        json_extract_scalar(requestmetadata, '$.userId') AS user_id,
        SUM(
            CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) +
            CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)
        ) AS tokens_used
    FROM invocations
    WHERE accountid = '477205238526'
        AND date_trunc('month', from_iso8601_timestamp(timestamp)) = date_trunc('month', current_date)
        AND requestmetadata IS NOT NULL
    GROUP BY json_extract_scalar(requestmetadata, '$.userId')
)
SELECT
    user_id,
    tokens_used,
    -- These limits would typically come from DynamoDB or a JOIN with user metadata table
    CASE
        WHEN user_id LIKE '%john.doe%' THEN 500000000
        WHEN user_id LIKE '%alice.johnson%' THEN 400000000
        WHEN user_id LIKE '%david.chen%' THEN 350000000
        WHEN user_id LIKE '%jane.smith%' THEN 300000000
        WHEN user_id LIKE '%bob.wilson%' THEN 250000000
        ELSE 100000000
    END AS monthly_limit,
    ROUND(
        CAST(tokens_used AS DOUBLE) /
        CASE
            WHEN user_id LIKE '%john.doe%' THEN 500000000.0
            WHEN user_id LIKE '%alice.johnson%' THEN 400000000.0
            WHEN user_id LIKE '%david.chen%' THEN 350000000.0
            WHEN user_id LIKE '%jane.smith%' THEN 300000000.0
            WHEN user_id LIKE '%bob.wilson%' THEN 250000000.0
            ELSE 100000000.0
        END * 100,
        2
    ) AS usage_percentage
FROM user_usage
ORDER BY usage_percentage DESC;

-- ============================================================================
-- Query 5: Hourly usage pattern (peak hours)
-- ============================================================================
SELECT
    date_trunc('hour', from_iso8601_timestamp(timestamp)) AS hour,
    COUNT(*) AS invocation_count,
    SUM(
        CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) +
        CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)
    ) AS total_tokens
FROM invocations
WHERE accountid = '477205238526'
    AND from_iso8601_timestamp(timestamp) >= current_date - interval '7' day
    AND requestmetadata IS NOT NULL
GROUP BY date_trunc('hour', from_iso8601_timestamp(timestamp))
ORDER BY hour DESC;

-- ============================================================================
-- Query 6: Model usage distribution
-- ============================================================================
SELECT
    modelid,
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    COUNT(*) AS invocation_count,
    SUM(
        CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) +
        CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)
    ) AS total_tokens,
    AVG(
        CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) +
        CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)
    ) AS avg_tokens
FROM invocations
WHERE accountid = '477205238526'
    AND from_iso8601_timestamp(timestamp) >= current_date - interval '30' day
    AND requestmetadata IS NOT NULL
GROUP BY modelid, json_extract_scalar(requestmetadata, '$.tenant')
ORDER BY total_tokens DESC;

-- ============================================================================
-- Query 7: Error analysis (by user and tenant)
-- ============================================================================
SELECT
    json_extract_scalar(requestmetadata, '$.userId') AS user_id,
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    json_extract_scalar(error, '$.type') AS error_type,
    COUNT(*) AS error_count
FROM invocations
WHERE accountid = '477205238526'
    AND from_iso8601_timestamp(timestamp) >= current_date - interval '7' day
    AND error IS NOT NULL
    AND requestmetadata IS NOT NULL
GROUP BY
    json_extract_scalar(requestmetadata, '$.userId'),
    json_extract_scalar(requestmetadata, '$.tenant'),
    json_extract_scalar(error, '$.type')
ORDER BY error_count DESC;

-- ============================================================================
-- Query 8: Audit trail (recent invocations with full context)
-- ============================================================================
SELECT
    timestamp,
    json_extract_scalar(requestmetadata, '$.userId') AS user_id,
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    json_extract_scalar(requestmetadata, '$.department') AS department,
    json_extract_scalar(requestmetadata, '$.source') AS source,
    modelid,
    CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) AS input_tokens,
    CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER) AS output_tokens,
    requestid
FROM invocations
WHERE accountid = '477205238526'
    AND from_iso8601_timestamp(timestamp) >= current_timestamp - interval '1' hour
    AND requestmetadata IS NOT NULL
ORDER BY timestamp DESC
LIMIT 100;

-- ============================================================================
-- Query 9: Cost attribution by tenant (for chargeback)
-- ============================================================================
SELECT
    date_trunc('month', from_iso8601_timestamp(timestamp)) AS month,
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    COUNT(*) AS invocation_count,
    SUM(CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER)) AS input_tokens,
    SUM(CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)) AS output_tokens,
    -- Claude 3.5 Sonnet pricing: $3/MTok input, $15/MTok output
    ROUND(
        (SUM(CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER)) * 3.00 / 1000000.0) +
        (SUM(CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)) * 15.00 / 1000000.0),
        2
    ) AS total_cost_usd
FROM invocations
WHERE accountid = '477205238526'
    AND requestmetadata IS NOT NULL
GROUP BY
    date_trunc('month', from_iso8601_timestamp(timestamp)),
    json_extract_scalar(requestmetadata, '$.tenant')
ORDER BY month DESC, total_cost_usd DESC;

-- ============================================================================
-- Query 10: User activity summary (for quota management)
-- ============================================================================
SELECT
    json_extract_scalar(requestmetadata, '$.userId') AS user_id,
    json_extract_scalar(requestmetadata, '$.group') AS user_group,
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    COUNT(*) AS total_invocations,
    COUNT(DISTINCT date_trunc('day', from_iso8601_timestamp(timestamp))) AS active_days,
    MIN(from_iso8601_timestamp(timestamp)) AS first_activity,
    MAX(from_iso8601_timestamp(timestamp)) AS last_activity,
    SUM(
        CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) +
        CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)
    ) AS total_tokens
FROM invocations
WHERE accountid = '477205238526'
    AND from_iso8601_timestamp(timestamp) >= current_date - interval '30' day
    AND requestmetadata IS NOT NULL
GROUP BY
    json_extract_scalar(requestmetadata, '$.userId'),
    json_extract_scalar(requestmetadata, '$.group'),
    json_extract_scalar(requestmetadata, '$.tenant')
ORDER BY total_tokens DESC;
