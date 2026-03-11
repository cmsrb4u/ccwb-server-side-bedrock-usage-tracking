# Application Inference Profiles vs Server-Side Logging

Comprehensive comparison of two approaches to Bedrock multi-tenant tracking.

## Architecture Comparison

### Application Inference Profiles (AIPs)

```
┌──────────────┐
│   Tenant A   │ → Profile: p24qm5pye2qr
├──────────────┤   ↓
│ - john.doe   │   Bedrock Runtime
│ - jane.smith │   ↓
└──────────────┘   CloudWatch Metrics (by ProfileId)
                   ↓
┌──────────────┐   Dashboard (4 tenant columns)
│   Tenant B   │
├──────────────┤   Limitations:
│ - bob.wilson │   - No user-level attribution
└──────────────┘   - Limited to ~20 profiles
                   - No custom metadata in metrics
```

### Server-Side Logging (This Solution)

```
┌──────────────┐
│   Any User   │ → JWT Token
└──────┬───────┘
       ↓
┌─────────────────┐
│  API Gateway    │ → Custom Authorizer validates JWT
└──────┬──────────┘
       ↓
┌─────────────────┐
│ Lambda Proxy    │ → Sets requestMetadata server-side:
└──────┬──────────┘   {userId, tenant, dept, group, ...}
       ↓
┌─────────────────┐
│ Bedrock Runtime │ → Invokes model with metadata
└──────┬──────────┘
       ↓
┌─────────────────┐
│ CloudWatch Logs │ → Real-time (~1-2 min)
└──────┬──────────┘
       ↓
┌─────────────────┐
│  S3 Logs        │ → Durable storage (~5-10 min)
└──────┬──────────┘
       ↓
┌─────────────────┐
│  Glue Crawler   │ → Schema discovery (daily)
└──────┬──────────┘
       ↓
┌─────────────────┐
│  Athena         │ → SQL queries (unlimited flexibility)
└─────────────────┘

Benefits:
✅ Unlimited users/tenants
✅ User-level attribution
✅ Custom metadata (any JSON)
✅ SQL-based cost analysis
✅ Full audit trail
```

## Feature Comparison

| Feature | AIPs | Server-Side Logging |
|---------|------|---------------------|
| **Tenant Isolation** | ✅ Native (separate profiles) | ⚠️ Via requestMetadata |
| **User-Level Tracking** | ❌ No | ✅ Yes |
| **Custom Metadata** | ❌ No | ✅ Unlimited (JSON) |
| **CloudWatch Metrics** | ✅ By ProfileId | ✅ By ModelId |
| **Cost Attribution** | ✅ Native tags | ✅ SQL queries |
| **Scalability** | ⚠️ ~20 profiles | ✅ Unlimited |
| **Setup Complexity** | ⚠️ Medium | ⚠️ Medium |
| **Trust Level** | ✅ High | ✅ High |
| **Query Flexibility** | ❌ Limited | ✅ SQL (Athena) |
| **Real-time Metrics** | ✅ ~1 min | ✅ ~1-2 min |
| **Audit Trail** | ⚠️ CloudWatch only | ✅ CloudWatch + S3 |
| **Compliance** | ⚠️ Basic | ✅ Full (S3 retention) |

## Use Case Matrix

### When to Use AIPs

✅ **Perfect for:**
- Small number of tenants (<10)
- Strict tenant isolation required
- Native CloudWatch metrics desired
- No user-level attribution needed
- Simple deployment preferred

❌ **Not suitable for:**
- Large number of tenants (>20)
- User-level cost attribution
- Complex organizational hierarchies
- Custom metadata requirements
- SQL-based reporting needs

### When to Use Server-Side Logging

✅ **Perfect for:**
- Large number of users/tenants
- User-level cost attribution
- Department/project tracking
- Complex organizational structures
- SQL-based cost analysis
- Compliance requirements (audit logs)
- Custom metadata needs

❌ **Not suitable for:**
- Hard tenant isolation requirements
- No infrastructure management desired
- Simple 2-3 tenant setup
- No SQL query needs

## Cost Comparison

### AIPs

```
Infrastructure:
- Application Inference Profiles: FREE
- CloudWatch Metrics: ~$0.30/metric/month × 4 tenants = $1.20/month
- CloudWatch Dashboards: $3/dashboard/month

Total Infrastructure: ~$5/month

Bedrock Usage:
- Standard Bedrock pricing
- No additional costs
```

### Server-Side Logging

```
Infrastructure:
- S3 Storage: ~$0.023/GB (Standard)
- CloudWatch Logs: $0.50/GB ingested + $0.03/GB stored
- Glue Crawler: ~$1.50/month (daily runs)
- Athena: $5/TB scanned
- Lambda: Free tier (1M requests)
- API Gateway: $1/million requests
- KMS: $1/month
- DynamoDB: Free tier

Total Infrastructure: ~$10-30/month (depending on volume)

Bedrock Usage:
- Standard Bedrock pricing
- No additional costs
```

**Cost Difference:** ~$5-25/month for infrastructure

**Note:** For typical usage (1M Bedrock calls/month = ~$9K), infrastructure cost is <0.3% of total.

## Implementation Comparison

### AIPs Setup Steps

```bash
# 1. Create Application Inference Profiles (per tenant)
aws bedrock create-application-inference-profile \
  --inference-profile-name "Tenant-A-Profile" \
  --model-source '{
    "copyFrom": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
  }'

# 2. Update application to use profile ARNs
model_id = tenant_profiles[tenant_id]
response = bedrock.invoke_model(modelId=model_id, body=body)

# 3. Create CloudWatch dashboard (per tenant)
# Manual or via script
```

**Time:** 1-2 hours for initial setup

### Server-Side Logging Setup Steps

```bash
# 1. Deploy infrastructure
./deploy.sh          # 5-10 minutes

# 2. Configure and seed users
python3 post-deploy.py    # 2-3 minutes

# 3. Test
python3 test-api.py       # 1 minute
```

**Time:** 25-30 minutes total

**Winner:** Server-Side (fully automated)

## Data Access Comparison

### AIPs - CloudWatch Metrics

```python
# Get tenant usage
cloudwatch = boto3.client('cloudwatch')
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/Bedrock',
    MetricName='InputTokenCount',
    Dimensions=[
        {'Name': 'ModelId', 'Value': 'p24qm5pye2qr'}
    ],
    StartTime=start_time,
    EndTime=end_time,
    Period=3600,
    Statistics=['Sum']
)

# Limitation: Cannot filter by user within tenant
```

### Server-Side - Athena SQL

```sql
-- Get user usage within tenant
SELECT
    json_extract_scalar(requestmetadata, '$.userId') AS user,
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    json_extract_scalar(requestmetadata, '$.department') AS dept,
    SUM(usage.inputTokens + usage.outputTokens) AS tokens,
    COUNT(*) AS calls
FROM invocations
WHERE tenant = 'tenant_a'
    AND month = '2026-03'
GROUP BY user, tenant, dept
ORDER BY tokens DESC;

-- Advantage: Filter by any metadata field
```

## Security Comparison

### AIPs

| Layer | Trust Level | Spoofable? |
|-------|-------------|------------|
| Profile ARN | ✅ High | ❌ No (server selects) |
| CloudWatch Metrics | ✅ High | ❌ No (AWS service) |
| requestMetadata | ⚠️ Medium | ⚠️ If client-set |

**Trust Model:**
- Profile selection happens server-side ✅
- Metrics generated by AWS ✅
- requestMetadata optional (if used, client can spoof) ⚠️

### Server-Side Logging

| Layer | Trust Level | Spoofable? |
|-------|-------------|------------|
| JWT Token | ✅ High | ❌ No (signature validated) |
| API Gateway Auth | ✅ High | ❌ No (AWS service) |
| requestMetadata | ✅ High | ❌ No (Lambda sets) |
| CloudWatch Logs | ✅ High | ❌ No (AWS service) |
| S3 Logs | ✅ High | ❌ No (write-only) |

**Trust Model:**
- JWT validated by API Gateway ✅
- requestMetadata set by Lambda (after auth) ✅
- Logs immutable (AWS services) ✅
- Full audit trail ✅

**Winner:** Server-Side (higher trust, no client control)

## Scalability Comparison

### AIPs

```
Tenant 1 → Profile 1 → CloudWatch Metrics
Tenant 2 → Profile 2 → CloudWatch Metrics
...
Tenant N → Profile N → CloudWatch Metrics

Limits:
- Soft limit: ~20 profiles per account
- Hard limit: Account quotas
- Dashboard: 500 widgets max (125 tenants × 4 widgets)
```

### Server-Side Logging

```
User 1 ─┐
User 2 ─┤
User 3 ─┼→ API Gateway → Lambda → Bedrock
User N ─┘            ↓
                requestMetadata (any user)
                     ↓
                CloudWatch → S3 → Athena

Limits:
- Users: Unlimited
- Tenants: Unlimited
- Metadata: Unlimited (JSON)
- Queries: Unlimited (SQL)
```

**Winner:** Server-Side (no limits)

## Monitoring Comparison

### AIPs - CloudWatch Dashboard

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Bedrock", "InputTokenCount", {"ModelId": "p24qm5pye2qr"}],
          ["AWS/Bedrock", "InputTokenCount", {"ModelId": "3rg09c3irrs6"}],
          ["AWS/Bedrock", "InputTokenCount", {"ModelId": "iq5vx6jibn89"}],
          ["AWS/Bedrock", "InputTokenCount", {"ModelId": "f8a6a2e836bz"}]
        ]
      }
    }
  ]
}
```

**Features:**
- Real-time metrics (~1 minute)
- Visual dashboards
- CloudWatch Alarms
- Side-by-side tenant comparison

**Limitations:**
- No user-level breakdown
- Fixed dimensions (ModelId only)
- 500 widget limit
- No historical SQL queries

### Server-Side - Athena + CloudWatch

```sql
-- Real-time monitoring (CloudWatch Logs Insights)
SELECT
    requestMetadata.userId,
    requestMetadata.tenant,
    COUNT(*) as calls
FROM '/aws/bedrock/modelinvocations'
WHERE @timestamp > ago(1h)
GROUP BY requestMetadata.userId, requestMetadata.tenant

-- Historical analysis (Athena)
SELECT
    date_trunc('day', timestamp) as day,
    json_extract_scalar(requestmetadata, '$.userId') as user,
    SUM(usage.inputTokens + usage.outputTokens) as tokens
FROM invocations
WHERE month = '2026-03'
GROUP BY day, user
ORDER BY day DESC
```

**Features:**
- Real-time logs (~1-2 minutes)
- SQL queries (unlimited flexibility)
- Historical analysis (years)
- Custom aggregations
- User/tenant/department breakdown

**Limitations:**
- Requires SQL knowledge
- Slower than CloudWatch Metrics (for historical)
- Query costs ($5/TB scanned)

## Cost Attribution Comparison

### AIPs - Tags

```python
# Tag profiles
bedrock.tag_resource(
    ResourceARN=profile_arn,
    Tags=[
        {'Key': 'tenant', 'Value': 'tenant_a'},
        {'Key': 'costcenter', 'Value': 'CC-001'}
    ]
)

# Query costs (Cost Explorer)
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-03-31 \
  --granularity MONTHLY \
  --filter '{"Tags": {"Key": "tenant", "Values": ["tenant_a"]}}'
```

**Granularity:** Tenant-level only

### Server-Side - Athena

```sql
-- By user
SELECT
    json_extract_scalar(requestmetadata, '$.userId') as user,
    SUM((usage.inputTokens * 3 + usage.outputTokens * 15) / 1000000.0) as cost_usd
FROM invocations
WHERE month = '2026-03'
GROUP BY user;

-- By tenant
SELECT
    json_extract_scalar(requestmetadata, '$.tenant') as tenant,
    SUM((usage.inputTokens * 3 + usage.outputTokens * 15) / 1000000.0) as cost_usd
FROM invocations
WHERE month = '2026-03'
GROUP BY tenant;

-- By department (for chargeback)
SELECT
    json_extract_scalar(requestmetadata, '$.department') as dept,
    SUM((usage.inputTokens * 3 + usage.outputTokens * 15) / 1000000.0) as cost_usd
FROM invocations
WHERE month = '2026-03'
GROUP BY dept;

-- By project, region, costcenter, or ANY custom field
SELECT
    json_extract_scalar(requestmetadata, '$.project') as project,
    SUM((usage.inputTokens * 3 + usage.outputTokens * 15) / 1000000.0) as cost_usd
FROM invocations
WHERE month = '2026-03'
GROUP BY project;
```

**Granularity:** Any level (user, tenant, dept, project, custom)

**Winner:** Server-Side (unlimited dimensions)

## Compliance & Audit Comparison

### AIPs

```
Audit Trail:
- CloudWatch Metrics: 15 months retention
- CloudWatch Logs: Optional (if enabled)
- S3 Logs: Optional (if configured)

Compliance Features:
- Tags for cost allocation ✅
- Native AWS metrics ✅
- Encryption at rest ⚠️ (depends on config)
- Immutable logs ⚠️ (if S3 configured)
```

### Server-Side Logging

```
Audit Trail:
- CloudWatch Logs: 30 days retention (configurable)
- S3 Logs: Unlimited (with lifecycle policies)
- Athena: Query logs up to 7 years (or more)

Compliance Features:
- KMS encryption ✅
- S3 versioning ✅
- S3 Object Lock (optional) ✅
- Immutable logs ✅
- Full requestMetadata in logs ✅
- Identity validation (JWT) ✅
- Access logging ✅
```

**Winner:** Server-Side (complete audit trail)

## Migration Path

### From AIPs to Server-Side

```bash
# Keep AIPs running (no downtime)
# Deploy server-side solution in parallel
./deploy.sh

# Gradually migrate applications to use API Gateway
# Switch by tenant or by application

# Once migrated, optionally delete AIPs
aws bedrock delete-application-inference-profile \
  --inference-profile-id "profile-id"
```

**Downtime:** Zero (run in parallel)

### From Server-Side to AIPs

```bash
# Create AIPs for each tenant
for tenant in tenants:
    create_profile(tenant)

# Update applications to use profile ARNs
# Remove API Gateway dependency

# Delete server-side infrastructure
aws cloudformation delete-stack \
  --stack-name bedrock-serverside-logging
```

**Downtime:** Depends on deployment strategy

## Recommendation Matrix

| Scenario | Recommendation |
|----------|----------------|
| 2-5 tenants, no user tracking | **AIPs** |
| 10+ tenants | **Server-Side** |
| User-level cost attribution required | **Server-Side** |
| Complex org structure (dept/project) | **Server-Side** |
| Simple deployment preferred | **AIPs** |
| SQL queries required | **Server-Side** |
| Compliance/audit requirements | **Server-Side** |
| Budget <$10/month infrastructure | **AIPs** |
| Need unlimited metadata | **Server-Side** |
| Real-time metrics critical | **AIPs** |
| Historical analysis critical | **Server-Side** |

## Hybrid Approach

You can use **both** simultaneously:

```python
# Use AIPs for tenant isolation
profile_arn = tenant_profiles[tenant_id]

# AND set requestMetadata for user tracking
response = bedrock.invoke_model(
    modelId=profile_arn,
    body=body,
    requestMetadata={
        'userId': user_id,
        'tenant': tenant_id,
        'department': department
    }
)
```

**Benefits:**
- Tenant isolation (AIPs) ✅
- User tracking (requestMetadata) ✅
- CloudWatch metrics by tenant ✅
- Athena queries by user ✅

**Drawbacks:**
- More complex ⚠️
- Higher cost ⚠️
- Still limited to ~20 profiles ⚠️

## Summary

### AIPs
**Best for:** Simple multi-tenant setups with tenant-level attribution

✅ Pros:
- Native AWS feature
- Simple setup
- Real-time metrics
- Low cost ($5/month)

❌ Cons:
- No user-level tracking
- Limited to ~20 tenants
- No custom metadata
- No SQL queries

### Server-Side Logging
**Best for:** Complex organizations needing user-level attribution

✅ Pros:
- Unlimited users/tenants
- User-level attribution
- Custom metadata (unlimited)
- SQL queries (Athena)
- Full audit trail
- High trust (JWT + server-side)

❌ Cons:
- More complex setup
- Higher cost ($10-30/month)
- Requires SQL knowledge
- Slower historical queries

## Decision Tree

```
Start
  ↓
Do you need user-level tracking?
  ├─ No → Do you have <10 tenants?
  │         ├─ Yes → Use AIPs ✅
  │         └─ No  → Use Server-Side ✅
  │
  └─ Yes → Do you need SQL queries?
            ├─ Yes → Use Server-Side ✅
            └─ No  → Do you need <20 tenants AND no custom metadata?
                     ├─ Yes → Use AIPs + requestMetadata ✅
                     └─ No  → Use Server-Side ✅
```

---

**Bottom Line:**
- **Simple tenant isolation:** Use AIPs
- **Complex user/dept tracking:** Use Server-Side Logging
- **Best of both:** Hybrid (AIPs + requestMetadata)

Both solutions provide **high-trust, server-validated** tracking. Choose based on your specific requirements for granularity and flexibility.
