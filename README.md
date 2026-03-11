# CCWB Server-Side Bedrock Usage Tracking

Complete server-side tracking solution for Amazon Bedrock with real-time quota enforcement, multi-tenant monitoring, and comprehensive CloudWatch dashboards.

## 🎯 Overview

This solution provides enterprise-grade monitoring and quota enforcement for Amazon Bedrock usage across multiple tenants and users. It combines:

- **Server-Side Identity Validation** (JWT + API Gateway)
- **Real-Time Quota Enforcement** (pre-request blocking)
- **Multi-Tenant Isolation** (Application Inference Profiles)
- **Comprehensive Dashboards** (CloudWatch visualization)
- **Full Audit Trail** (CloudWatch → S3 → Athena)
- **Cost Attribution** (SQL queries for chargeback)

## 📊 Live Dashboard

<img width="2503" height="864" alt="image" src="https://github.com/user-attachments/assets/cb0ce39d-8ab2-442d-a223-8fedd78c4dd8" />


<img width="2451" height="751" alt="image" src="https://github.com/user-attachments/assets/dd3c799b-53f5-41ce-8a36-3847dc4c724f" />


**Features:**
- Real-time tenant comparison (4 tenants)
- User quota monitoring (5 users)
- Token usage trends
- Latency & error tracking
- Cost estimates
- System health status

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────┐
│   Client    │  JWT Token (user identity)
│ Application │
└──────┬──────┘
       │
       ↓ HTTPS Request
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                              │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Custom JWT Authorizer (Lambda)                        │    │
│  │  • Validates JWT signature                             │    │
│  │  • Extracts user identity (email, tenant, group)       │    │
│  │  • Returns IAM policy (Allow/Deny)                     │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ↓ Authorized Request
┌─────────────────────────────────────────────────────────────────┐
│                  Lambda Proxy Function                           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  1. Get User Metadata        ← DynamoDB                │    │
│  │  2. Get Quota Policy         ← DynamoDB                │    │
│  │  3. Check Current Usage      ← DynamoDB                │    │
│  │  4. Enforce Quota (PRE-REQUEST BLOCKING)               │    │
│  │  5. Build requestMetadata (server-side, secure)        │    │
│  │  6. Invoke Bedrock API       → Bedrock                 │    │
│  │  7. Update Usage (Atomic)    → DynamoDB                │    │
│  │  8. Publish Metrics          → CloudWatch              │    │
│  │  9. Return Response to Client                          │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ↓ Bedrock Invocation
┌─────────────────────────────────────────────────────────────────┐
│                   Amazon Bedrock                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Application Inference Profile (AIP)                   │    │
│  │  • Tenant A (Marketing):   arn:...p24qm5pye2qr         │    │
│  │  • Tenant B (Sales):       arn:...3rg09c3irrs6         │    │
│  │  • Tenant C (Engineering): arn:...iq5vx6jibn89         │    │
│  │  • Tenant D (Finance):     arn:...f8a6a2e836bz         │    │
│  │                                                         │    │
│  │  Each AIP provides:                                    │    │
│  │  ✓ Isolated CloudWatch metrics (AWS/Bedrock)           │    │
│  │  ✓ Model invocation logging with requestMetadata      │    │
│  │  ✓ Cost allocation via tags                            │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ↓ Logs & Metrics
┌─────────────────────────────────────────────────────────────────┐
│                    Observability Layer                           │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  CloudWatch  │    │  CloudWatch  │    │      S3      │      │
│  │    Metrics   │    │     Logs     │    │   (Logging)  │      │
│  │              │    │              │    │              │      │
│  │ • Invocations│───→│  Log Stream  │───→│  Invocation  │      │
│  │ • TokenCount │    │  (1-2 min)   │    │  Logs JSON   │      │
│  │ • Latency    │    │              │    │  (5-10 min)  │      │
│  │ • Errors     │    │              │    │              │      │
│  └──────────────┘    └──────────────┘    └──────┬───────┘      │
│                                                   │              │
│                                                   ↓              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │     Glue     │───→│   Athena     │───→│    SQL       │      │
│  │   Crawler    │    │   Queries    │    │  Analysis    │      │
│  │  (Daily)     │    │              │    │  (Cost/User) │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
└───────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. API Gateway Layer
**Purpose:** Entry point for all requests, enforces authentication and authorization.

**Components:**
- **REST API Endpoint:** `https://{api-id}.execute-api.us-west-2.amazonaws.com/prod/invoke`
- **Custom Authorizer Lambda:** Validates JWT tokens, extracts identity claims
- **Usage Plans:** Rate limiting (optional)
- **CloudWatch Logs:** Request/response logging

**Security:**
```json
JWT Token (decoded):
{
  "sub": "john.doe@company.com",
  "email": "john.doe@company.com",
  "tenant": "tenant_a",
  "group": "marketing",
  "exp": 1709256000
}
```

**Authorization Flow:**
1. Client sends JWT in `Authorization: Bearer <token>` header
2. API Gateway invokes Custom Authorizer Lambda
3. Authorizer validates signature using public key/secret
4. Authorizer returns IAM policy document (Allow/Deny)
5. API Gateway caches policy for 5 minutes (TTL)
6. Request forwarded to Lambda Proxy with identity context

#### 2. Lambda Proxy Function
**Purpose:** Core orchestration layer - enforces quotas, sets requestMetadata, invokes Bedrock.

**Environment Variables:**
```bash
USER_METADATA_TABLE=UserMetadataTable
QUOTA_POLICIES_TABLE=QuotaPoliciesTable
USER_QUOTA_METRICS_TABLE=UserQuotaMetricsTable
REGION=us-west-2
```

**Detailed Execution Flow:**

```python
# Step 1: Extract User Identity from Authorizer Context
user_email = event['requestContext']['authorizer']['principalId']
tenant = event['requestContext']['authorizer']['tenant']
group = event['requestContext']['authorizer']['group']

# Step 2: Get User Metadata from DynamoDB
user_metadata = dynamodb.get_item(
    TableName='UserMetadataTable',
    Key={'userId': user_email}
)
# Contains: tenant mapping, group, monthly_limit, daily_limit

# Step 3: Get Hierarchical Quota Policy
# Priority: user > group > default
quota_policy = get_quota_policy(user_email, group)
# {
#   "monthly_limit": 500000000,  # 500M tokens
#   "daily_limit": 20000000,     # 20M tokens
#   "enforcement_mode": "block"   # or "alert"
# }

# Step 4: Check Current Usage (DynamoDB)
now = datetime.utcnow()
month_key = f"monthly_{now.strftime('%Y-%m')}"
day_key = f"daily_{now.strftime('%Y-%m-%d')}"

monthly_usage = get_usage(user_email, month_key)
daily_usage = get_usage(user_email, day_key)

# Step 5: PRE-REQUEST QUOTA ENFORCEMENT
if enforcement_mode == "block":
    if monthly_usage >= monthly_limit:
        raise QuotaExceededError("Monthly quota exceeded")
    if daily_usage >= daily_limit:
        raise QuotaExceededError("Daily quota exceeded")

# Step 6: Build requestMetadata (SERVER-SIDE - CANNOT BE SPOOFED)
request_metadata = {
    "userId": user_email,
    "tenant": tenant,
    "group": group,
    "requestId": str(uuid.uuid4()),
    "timestamp": now.isoformat(),
    "quotaStatus": {
        "monthlyUsed": monthly_usage,
        "monthlyLimit": monthly_limit,
        "dailyUsed": daily_usage,
        "dailyLimit": daily_limit
    }
}

# Step 7: Invoke Bedrock with Application Inference Profile
profile_arn = get_profile_arn(tenant)  # Map tenant → AIP ARN
response = bedrock_runtime.invoke_model(
    modelId=profile_arn,  # e.g., arn:aws:bedrock:us-west-2:123456789012:application-inference-profile/p24qm5pye2qr
    body=json.dumps(bedrock_request),
    accept='application/json',
    contentType='application/json'
)

# Step 8: Parse Response & Calculate Token Usage
response_body = json.loads(response['body'].read())
input_tokens = response_body['usage']['input_tokens']
output_tokens = response_body['usage']['output_tokens']
total_tokens = input_tokens + output_tokens

# Step 9: Update Usage ATOMICALLY (DynamoDB)
# Using ADD operation for thread-safety
dynamodb.update_item(
    TableName='UserQuotaMetricsTable',
    Key={
        'user_email': user_email,
        'metric_period': month_key
    },
    UpdateExpression='ADD tokens_used :tokens SET last_updated = :now',
    ExpressionAttributeValues={
        ':tokens': total_tokens,
        ':now': now.isoformat()
    }
)

# Same for daily usage
dynamodb.update_item(
    TableName='UserQuotaMetricsTable',
    Key={
        'user_email': user_email,
        'metric_period': day_key
    },
    UpdateExpression='ADD tokens_used :tokens SET last_updated = :now',
    ExpressionAttributeValues={
        ':tokens': total_tokens,
        ':now': now.isoformat()
    }
)

# Step 10: Publish CloudWatch Metrics
cloudwatch.put_metric_data(
    Namespace='CCWB/UserQuota',
    MetricData=[
        {
            'MetricName': 'MonthlyUsagePercent',
            'Value': (monthly_usage + total_tokens) / monthly_limit * 100,
            'Unit': 'Percent',
            'Dimensions': [
                {'Name': 'UserEmail', 'Value': user_email},
                {'Name': 'Tenant', 'Value': tenant}
            ]
        },
        {
            'MetricName': 'DailyUsagePercent',
            'Value': (daily_usage + total_tokens) / daily_limit * 100,
            'Unit': 'Percent',
            'Dimensions': [
                {'Name': 'UserEmail', 'Value': user_email},
                {'Name': 'Tenant', 'Value': tenant}
            ]
        }
    ]
)

# Step 11: Return Response to Client
return {
    'statusCode': 200,
    'body': json.dumps({
        'response': response_body['content'][0]['text'],
        'usage': {
            'inputTokens': input_tokens,
            'outputTokens': output_tokens,
            'totalTokens': total_tokens
        },
        'quotaRemaining': {
            'monthly': monthly_limit - (monthly_usage + total_tokens),
            'daily': daily_limit - (daily_usage + total_tokens)
        }
    })
}
```

**Key Design Decisions:**
- **Pre-request blocking:** Checks quota BEFORE calling Bedrock (saves cost)
- **Atomic operations:** Uses DynamoDB ADD for thread-safe increments
- **Server-side metadata:** requestMetadata set by Lambda (cannot be spoofed)
- **Hierarchical policies:** User → Group → Default (flexibility)

#### 3. DynamoDB Tables

**UserMetadataTable:**
```json
{
  "userId": "john.doe@company.com",        // Partition Key
  "tenant": "tenant_a",
  "group": "marketing",
  "created_at": "2026-03-01T00:00:00Z",
  "status": "active"
}
```

**QuotaPoliciesTable:**
```json
{
  "policy_type": "user",                   // Partition Key (user|group|default)
  "identifier": "john.doe@company.com",    // Sort Key
  "monthly_limit": 500000000,              // 500M tokens
  "daily_limit": 20000000,                 // 20M tokens
  "enforcement_mode": "block",             // block|alert|log
  "created_at": "2026-03-01T00:00:00Z",
  "updated_at": "2026-03-10T15:30:00Z"
}
```

**UserQuotaMetricsTable:**
```json
{
  "user_email": "john.doe@company.com",    // Partition Key
  "metric_period": "monthly_2026-03",      // Sort Key (monthly_YYYY-MM or daily_YYYY-MM-DD)
  "tokens_used": 150000350,
  "last_updated": "2026-03-11T04:00:00Z"
}
```

**Query Patterns:**
```python
# Get user's monthly usage
get_item(pk="john.doe@company.com", sk="monthly_2026-03")

# Get user's daily usage
get_item(pk="john.doe@company.com", sk="daily_2026-03-11")

# Get all users' usage for a month
query(pk="john.doe@company.com", sk_begins_with="monthly_")
```

#### 4. Bedrock Application Inference Profiles

**Purpose:** Multi-tenant isolation at the model invocation level.

**Configuration:**
```yaml
Tenant A (Marketing):
  ProfileId: p24qm5pye2qr
  Model: anthropic.claude-3-5-sonnet-20241022-v2:0
  CloudWatch Dimension: ModelId=p24qm5pye2qr
  Use Case: Content generation, social media drafts

Tenant B (Sales):
  ProfileId: 3rg09c3irrs6
  Model: anthropic.claude-3-5-sonnet-20241022-v2:0
  CloudWatch Dimension: ModelId=3rg09c3irrs6
  Use Case: Email drafting, lead qualification

Tenant C (Engineering):
  ProfileId: iq5vx6jibn89
  Model: anthropic.claude-3-5-sonnet-20241022-v2:0
  CloudWatch Dimension: ModelId=iq5vx6jibn89
  Use Case: Code reviews, documentation

Tenant D (Finance):
  ProfileId: f8a6a2e836bz
  Model: anthropic.claude-3-5-sonnet-20241022-v2:0
  CloudWatch Dimension: ModelId=f8a6a2e836bz
  Use Case: Report generation, data analysis
```

**Benefits:**
- **Isolated Metrics:** Each tenant gets separate CloudWatch metrics
- **Cost Allocation:** Tag-based cost attribution in AWS Cost Explorer
- **Rate Limiting:** Per-tenant throttling (if needed)
- **Model Selection:** Different tenants can use different models
- **Logging:** Separate invocation logs per tenant

#### 5. CloudWatch Metrics

**AWS/Bedrock Namespace (Automatic):**
```python
Metrics:
  - Invocations (Count)
  - InputTokenCount (Count)
  - OutputTokenCount (Count)
  - InvocationLatency (Milliseconds)
  - ModelErrors (Count)

Dimensions:
  - ModelId: [AIP Profile ID]  # e.g., p24qm5pye2qr

Time Granularity: 1 minute
Retention: 15 months
```

**CCWB/UserQuota Namespace (Custom):**
```python
Metrics:
  - MonthlyUsagePercent (Percent)
  - DailyUsagePercent (Percent)

Dimensions:
  - UserEmail: [user email]
  - Tenant: [tenant identifier]

Published By: Lambda Proxy Function
Time Granularity: Per request
Retention: 15 months
```

**Dashboard Queries:**
```python
# Tenant invocations (last hour)
SELECT SUM(Invocations)
FROM "AWS/Bedrock"
WHERE ModelId = 'p24qm5pye2qr'
  AND time >= now() - 1h
GROUP BY time(5m)

# User quota percentage
SELECT AVG(MonthlyUsagePercent)
FROM "CCWB/UserQuota"
WHERE UserEmail = 'john.doe@company.com'
  AND time >= now() - 1h
```

#### 6. Logging & Audit Trail

**Flow:**
```
Bedrock Invocation
    ↓ (1-2 minutes)
CloudWatch Log Stream: /aws/bedrock/modelinvocations
    ↓ (5-10 minutes)
S3 Bucket: bedrock-invocation-logs-{account}-{region}
    ↓ (on-demand or scheduled)
Glue Crawler: bedrock-logs-crawler (discovers schema)
    ↓
Glue Data Catalog: bedrock_invocation_logs database
    ↓
Athena Workgroup: BedrockAnalytics
    ↓
SQL Queries: Cost attribution, usage analysis
```

**S3 Log Structure:**
```
s3://bedrock-invocation-logs-123456789012-us-west-2/
├── year=2026/
│   ├── month=03/
│   │   ├── day=11/
│   │   │   ├── hour=04/
│   │   │   │   ├── invocation_1234567890.json
│   │   │   │   ├── invocation_1234567891.json
│   │   │   │   └── ...
```

**Log Entry Example:**
```json
{
  "schemaType": "ModelInvocationLog",
  "schemaVersion": "1.0",
  "timestamp": "2026-03-11T04:15:23.456Z",
  "accountId": "123456789012",
  "identity": {
    "arn": "arn:aws:sts::123456789012:assumed-role/BedrockProxyRole/BedrockProxyFunction"
  },
  "region": "us-west-2",
  "requestId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "operation": "InvokeModel",
  "modelId": "arn:aws:bedrock:us-west-2:123456789012:application-inference-profile/p24qm5pye2qr",
  "input": {
    "inputContentType": "application/json",
    "inputBodyJson": {
      "anthropic_version": "bedrock-2023-05-31",
      "messages": [{"role": "user", "content": "What is AI?"}],
      "max_tokens": 1024
    }
  },
  "output": {
    "outputContentType": "application/json",
    "outputBodyJson": {
      "id": "msg_abc123",
      "type": "message",
      "role": "assistant",
      "content": [{"type": "text", "text": "AI is..."}],
      "usage": {
        "input_tokens": 12,
        "output_tokens": 56
      }
    }
  },
  "requestMetadata": {
    "userId": "john.doe@company.com",
    "tenant": "tenant_a",
    "group": "marketing",
    "requestId": "req-12345",
    "timestamp": "2026-03-11T04:15:23.123Z",
    "quotaStatus": {
      "monthlyUsed": 150000000,
      "monthlyLimit": 500000000,
      "dailyUsed": 5000000,
      "dailyLimit": 20000000
    }
  }
}
```

**Athena SQL Queries:**
```sql
-- Cost per user (last 30 days)
SELECT
    json_extract_scalar(requestmetadata, '$.userId') AS user_email,
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    COUNT(*) AS invocations,
    SUM(CAST(json_extract_scalar(output, '$.outputBodyJson.usage.input_tokens') AS INTEGER)) AS input_tokens,
    SUM(CAST(json_extract_scalar(output, '$.outputBodyJson.usage.output_tokens') AS INTEGER)) AS output_tokens,
    ROUND(
        (SUM(CAST(json_extract_scalar(output, '$.outputBodyJson.usage.input_tokens') AS INTEGER)) * 3.00 / 1000000.0) +
        (SUM(CAST(json_extract_scalar(output, '$.outputBodyJson.usage.output_tokens') AS INTEGER)) * 15.00 / 1000000.0),
        4
    ) AS estimated_cost_usd
FROM invocations
WHERE from_iso8601_timestamp(timestamp) >= current_date - interval '30' day
GROUP BY
    json_extract_scalar(requestmetadata, '$.userId'),
    json_extract_scalar(requestmetadata, '$.tenant')
ORDER BY estimated_cost_usd DESC;
```

#### 7. Security Architecture

**Defense in Depth:**

```
Layer 1: Network Security
├─ API Gateway: HTTPS only
├─ Private VPC endpoints (optional)
└─ WAF rules (optional)

Layer 2: Authentication & Authorization
├─ JWT signature validation
├─ Token expiration checks
├─ IAM policy generation
└─ Least-privilege roles

Layer 3: Application Security
├─ Server-side requestMetadata (cannot be spoofed)
├─ Input validation
├─ Rate limiting
└─ Error handling (no sensitive data in errors)

Layer 4: Data Security
├─ KMS encryption at rest (S3, DynamoDB, CloudWatch)
├─ Encryption in transit (TLS 1.2+)
├─ S3 bucket policies (deny unencrypted uploads)
└─ DynamoDB point-in-time recovery

Layer 5: Audit & Compliance
├─ CloudTrail API logging
├─ CloudWatch Logs (all requests)
├─ S3 invocation logs (immutable)
└─ Athena queries (compliance reports)
```

**Trust Model:**
```
TRUSTED:
✓ API Gateway (AWS managed)
✓ Lambda Authorizer (validates JWT)
✓ Lambda Proxy (sets requestMetadata)
✓ DynamoDB (atomic operations)
✓ Bedrock (AWS managed)

UNTRUSTED:
✗ Client application (can send arbitrary JWT)
✗ User input (validated at Lambda)
✗ Client-provided metadata (ignored - server sets it)
```

#### 8. Cost Attribution Data Flow

**Real-Time (DynamoDB):**
```
Lambda Proxy
    ↓ (immediate)
DynamoDB Update (ADD tokens_used)
    ↓ (immediate)
CloudWatch Metric (MonthlyUsagePercent)
    ↓ (immediate)
Dashboard Widget (Quota Gauge)
    ↓
Alert (if > 80%)
```

**Historical (Athena):**
```
Bedrock Invocation
    ↓ (1-2 min)
CloudWatch Log
    ↓ (5-10 min)
S3 JSON Log
    ↓ (on-demand)
Glue Crawler (schema discovery)
    ↓
Athena Table (queryable)
    ↓
SQL Query (cost per user/tenant/group)
    ↓
Chargeback Report
```

**Example Workflow:**
```bash
# 1. User makes API call
curl -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{"prompt":"What is AI?"}' \
     https://api.example.com/invoke

# 2. Lambda updates DynamoDB (atomic)
tokens_used: 150000000 → 150000350 (+350)

# 3. CloudWatch metric published
MonthlyUsagePercent: 30.0%

# 4. Dashboard shows updated gauge
[████████░░░░] 30% (150M/500M)

# 5. Athena query (end of month)
john.doe@company.com | tenant_a | 150,000,350 tokens | $562.50
```

### Architectural Decisions

#### Why Pre-Request Quota Enforcement?
**Decision:** Check quota BEFORE calling Bedrock, not after.

**Rationale:**
- Saves cost (blocked requests don't consume Bedrock tokens)
- Faster response to user (immediate quota error)
- Prevents quota "overage" race conditions

**Trade-off:** Adds 50-100ms latency for DynamoDB lookup.

#### Why Server-Side requestMetadata?
**Decision:** Lambda sets requestMetadata, not client.

**Rationale:**
- Cannot be spoofed by malicious clients
- Ensures audit trail integrity
- Compliance requirement (immutable logs)

**Trade-off:** Requires Lambda proxy (cannot call Bedrock directly from client).

#### Why Application Inference Profiles?
**Decision:** Use AIPs for multi-tenant isolation.

**Rationale:**
- Automatic CloudWatch metrics per tenant
- Cost allocation via AWS Cost Explorer tags
- Rate limiting per tenant (if needed)
- Model selection flexibility per tenant

**Trade-off:** Requires creating/managing AIPs (AWS quota: 10 per region by default).

#### Why DynamoDB Over RDS?
**Decision:** Use DynamoDB for quota tracking.

**Rationale:**
- Atomic ADD operations (thread-safe)
- Millisecond latency (50-100ms)
- On-demand pricing (no idle costs)
- Serverless (no patching/maintenance)

**Trade-off:** Limited query capabilities (no complex JOINs).

#### Why CloudWatch + Athena?
**Decision:** Use CloudWatch for real-time, Athena for historical.

**Rationale:**
- CloudWatch: 1-2 min latency, great for dashboards
- Athena: Cheap ($5/TB), great for monthly reports
- Best of both worlds

**Trade-off:** Two data sources to manage (but automated via Glue crawler).

## ✨ Key Features

### 1. Multi-Tenant Isolation
- **4 Application Inference Profiles** (Marketing, Sales, Engineering, Finance)
- Separate CloudWatch metrics per tenant
- Cost allocation via tags
- Independent quota policies

### 2. User-Level Quota Enforcement
- **Pre-request blocking** (saves cost!)
- Monthly and daily limits
- Hierarchical policies (user → group → default)
- Real-time DynamoDB tracking
- CloudWatch alerts at 80% usage

### 3. Real-Time Monitoring
- **Comprehensive CloudWatch dashboard** (14 widgets)
- Tenant invocation comparison
- Token usage trends
- User quota gauges
- Latency and error rates
- Cost estimates

### 4. Full Audit Trail
- CloudWatch Logs (~1-2 min)
- S3 invocation logs (~5-10 min)
- Glue schema discovery (daily)
- Athena SQL queries
- requestMetadata in every log

### 5. Security
- ✅ Server-validated JWT tokens
- ✅ API Gateway custom authorizer
- ✅ Server-side requestMetadata (cannot be spoofed)
- ✅ KMS encryption at rest
- ✅ DynamoDB atomic operations
- ✅ IAM least-privilege roles

## 🚀 Quick Start

### Prerequisites

```bash
# Install AWS SAM CLI
brew install aws-sam-cli

# Install AWS CLI
brew install awscli

# Configure AWS credentials
aws configure
# Region: us-west-2
# Access Key ID: [your key]
# Secret Access Key: [your secret]
```

### Option 1: Use Existing Infrastructure (Recommended)

If you already have Application Inference Profiles and DynamoDB tables:

```bash
# 1. Create the comprehensive dashboard
python3 create-comprehensive-dashboard.py

# 2. Generate test traffic
python3 generate-test-traffic.py

# 3. View real usage data
python3 show-real-usage.py
```

**Dashboard URL:** https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards/dashboard/Bedrock-Comprehensive-Monitoring

### Option 2: Deploy Full Solution

Deploy the complete hybrid solution with quota enforcement:

```bash
# 1. Build and deploy infrastructure
./deploy-hybrid.sh

# 2. Configure and seed user data
python3 post-deploy-hybrid.py

# 3. Test quota enforcement
python3 test-quota-enforcement.py

# 4. Create dashboard
python3 create-comprehensive-dashboard.py
```

## 📦 What's Included

### Infrastructure (CloudFormation/SAM)

**Files:**
- `infrastructure.yaml` - Basic server-side logging
- `infrastructure-with-quotas.yaml` - Hybrid solution with quotas

**Resources Created:**
- KMS encryption key
- 3 S3 buckets (logs, access logs, Athena results)
- CloudWatch Log Group
- Glue database + crawler
- Athena workgroup
- 3 DynamoDB tables (UserMetadata, QuotaPolicies, QuotaMetrics)
- 2 Lambda functions (proxy, authorizer)
- API Gateway with JWT auth
- CloudWatch alarms
- SNS topic for alerts

### Deployment Scripts

- `deploy.sh` - Deploy basic solution
- `deploy-hybrid.sh` - Deploy hybrid solution with quotas
- `post-deploy.py` - Basic configuration
- `post-deploy-hybrid.py` - Hybrid configuration with users

### Testing & Monitoring

- `test-api.py` - Test basic API
- `test-quota-enforcement.py` - Test quota blocking
- `generate-test-traffic.py` - Generate real Bedrock API calls
- `show-real-usage.py` - Query DynamoDB and CloudWatch

### Dashboard Creation

- `create-dashboard.py` - Create quota dashboard (if using hybrid)
- `create-comprehensive-dashboard.py` - Create comprehensive multi-tenant dashboard

### SQL Queries

- `athena-queries.sql` - 10 production-ready queries for cost attribution

### Documentation

- `START_HERE.md` - Quick navigation guide
- `README.md` - Solution overview
- `QUICKSTART.md` - 3-command quick start
- `HYBRID_SOLUTION_README.md` - Hybrid solution deep dive
- `HYBRID_DEPLOYMENT_SUMMARY.md` - Deployment walkthrough
- `IMPLEMENTATION_SUMMARY.md` - Architecture details
- `AIP_VS_SERVERSIDE_COMPARISON.md` - Comparison with AIPs

## 📊 Dashboard Widgets

The comprehensive dashboard includes:

### Row 1: Header (1 widget)
- System overview with 4 tenants, 5 users

### Row 2: Tenant Metrics (2 widgets)
- Hourly invocations by tenant
- Token usage trends (input + output)

### Row 3: User Quotas (5 widgets)
- Quota percentage gauges per user
- 80% warning, 95% critical thresholds

### Row 4: Comparisons (2 widgets)
- 24-hour tenant comparison bar chart
- Cost estimate information

### Row 5: Performance (2 widgets)
- Invocation latency (avg/p99)
- Error rates by tenant

### Row 6: Distribution (2 widgets)
- Token distribution pie chart
- System health status

**Total: 14 widgets, all using real live data!**

## 🔍 Data Sources (Real, Not Sample)

### 1. AWS/Bedrock CloudWatch Metrics
```python
Namespace: AWS/Bedrock
Metrics:
  - Invocations (by ModelId)
  - InputTokenCount (by ModelId)
  - OutputTokenCount (by ModelId)
  - InvocationLatency (by ModelId)
  - ModelErrors (by ModelId)

Dimensions:
  - ModelId: [profile ARNs]
```

### 2. CCWB/UserQuota Metrics
```python
Namespace: CCWB/UserQuota
Metrics:
  - MonthlyUsagePercent
  - DailyUsagePercent

Dimensions:
  - UserEmail
  - Tenant
```

### 3. DynamoDB Tables

**UserQuotaMetrics:**
```json
{
  "user_email": "john.doe@company.com",
  "metric_period": "monthly_2026-03",
  "tokens_used": 150000350,
  "last_updated": "2026-03-11T04:00:00"
}
```

**QuotaPolicies:**
```json
{
  "policy_type": "user",
  "identifier": "john.doe@company.com",
  "monthly_limit": 500000000,
  "daily_limit": 20000000,
  "enforcement_mode": "block"
}
```

## 💰 Cost Attribution

### Real-Time (DynamoDB)

```bash
# Get current monthly usage
aws dynamodb get-item \
  --table-name UserQuotaMetrics \
  --key '{"user_email":{"S":"john.doe@company.com"},"metric_period":{"S":"monthly_2026-03"}}'
```

### Historical (Athena)

```sql
-- Cost by user (last 30 days)
SELECT
    json_extract_scalar(requestmetadata, '$.userId') AS user,
    SUM(usage.inputTokens + usage.outputTokens) AS total_tokens,
    ROUND(
        (SUM(usage.inputTokens) * 3.00 / 1000000.0) +
        (SUM(usage.outputTokens) * 15.00 / 1000000.0),
        4
    ) AS cost_usd
FROM invocations
WHERE from_iso8601_timestamp(timestamp) >= current_date - interval '30' day
GROUP BY user
ORDER BY cost_usd DESC;
```

## 🧪 Testing

### Generate Real Traffic

```bash
python3 generate-test-traffic.py
```

**What it does:**
- Makes real Bedrock API calls through all 4 tenant profiles
- Generates actual CloudWatch metrics
- Updates DynamoDB usage tracking
- Creates real cost data

**Output:**
```
Total API Calls: 12
Total Tokens: 1,361
Avg Tokens/Call: 113

✅ Real metrics generated!
```

### Verify Real Data

```bash
python3 show-real-usage.py
```

**Shows:**
- Current user usage from DynamoDB
- Quota policies
- CloudWatch metrics (last hour)
- All data sources verified

## 📈 Sample Users & Tenants

### Tenants (Application Inference Profiles)

| Tenant | Profile ID | Department | Use Case |
|--------|-----------|------------|----------|
| Tenant A | p24qm5pye2qr | Marketing | Content generation |
| Tenant B | 3rg09c3irrs6 | Sales | Email drafting |
| Tenant C | iq5vx6jibn89 | Engineering | Code reviews |
| Tenant D | f8a6a2e836bz | Finance | Report generation |

### Users (with Quotas)

| User | Tenant | Monthly Limit | Daily Limit | Status |
|------|--------|---------------|-------------|---------|
| john.doe@company.com | Tenant A | 500M | 20M | Active |
| jane.smith@company.com | Tenant A | 300M | 12M | Active |
| bob.wilson@company.com | Tenant B | 250M | 10M | Active |
| alice.johnson@company.com | Tenant C | 400M | 15M | Active |
| david.chen@company.com | Tenant D | 350M | 12M | Active |

## 🔒 Security Features

### Server-Side Validation
- JWT tokens validated by API Gateway
- Cannot be spoofed by clients
- Signature verification required

### Quota Enforcement
- Pre-request blocking (before Bedrock call)
- Atomic DynamoDB updates
- Thread-safe counters
- No race conditions

### Request Metadata
- Set by Lambda (server-side)
- Cannot be modified by clients
- Full audit trail
- Compliance-ready

### Encryption
- KMS encryption for all data at rest
- S3 buckets encrypted
- DynamoDB encryption
- CloudWatch Logs encrypted
- Athena results encrypted

## 📚 Documentation Index

### Getting Started
1. **START_HERE.md** - Navigation guide
2. **QUICKSTART.md** - 3-command setup
3. **HYBRID_DEPLOYMENT_SUMMARY.md** - Detailed walkthrough

### Technical Guides
4. **README.md** - This file
5. **HYBRID_SOLUTION_README.md** - Hybrid architecture
6. **IMPLEMENTATION_SUMMARY.md** - Deep dive

### Comparisons
7. **AIP_VS_SERVERSIDE_COMPARISON.md** - AIPs vs server-side

### SQL Reference
8. **athena-queries.sql** - 10 cost attribution queries

## 🛠️ Configuration

### Add New User

```bash
# Add to DynamoDB
aws dynamodb put-item \
  --table-name UserMetadataTable \
  --item '{
    "userId": {"S": "new.user@company.com"},
    "group": {"S": "engineering"},
    "tenant": {"S": "tenant_a"},
    "monthlyLimit": {"N": "400000000"},
    "dailyLimit": {"N": "15000000"}
  }'
```

### Update Quota

```bash
# Increase monthly limit
aws dynamodb update-item \
  --table-name QuotaPoliciesTable \
  --key '{"policy_type":{"S":"user"},"identifier":{"S":"john.doe@company.com"}}' \
  --update-expression "SET monthly_limit = :limit" \
  --expression-attribute-values '{":limit":{"N":"600000000"}}'
```

### Change Enforcement Mode

```bash
# Switch from "block" to "alert"
aws dynamodb update-item \
  --table-name QuotaPoliciesTable \
  --key '{"policy_type":{"S":"user"},"identifier":{"S":"john.doe@company.com"}}' \
  --update-expression "SET enforcement_mode = :mode" \
  --expression-attribute-values '{":mode":{"S":"alert"}}'
```

## 🔗 Useful Links

### AWS Console
- **CloudWatch Dashboard:** https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards/dashboard/Bedrock-Comprehensive-Monitoring
- **DynamoDB Tables:** https://us-west-2.console.aws.amazon.com/dynamodbv2/home?region=us-west-2#tables
- **CloudWatch Logs:** https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#logsV2:log-groups
- **Athena:** https://us-west-2.console.aws.amazon.com/athena/home?region=us-west-2
- **Cost Explorer:** https://console.aws.amazon.com/cost-management/home#/dashboard

### Documentation
- [Bedrock Model Invocation Logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html)
- [Application Inference Profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/application-inference-profiles.html)
- [AWS SAM](https://docs.aws.amazon.com/serverless-application-model/)
- [CloudWatch Dashboards](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html)

## 🆘 Troubleshooting

### Dashboard Shows No Data

**Problem:** Dashboard widgets show "No data"

**Solution:**
1. Generate test traffic: `python3 generate-test-traffic.py`
2. Wait 2-3 minutes for metrics to propagate
3. Refresh dashboard
4. Verify Application Inference Profiles exist

### Quota Not Enforcing

**Problem:** Users exceed quota without getting blocked

**Solution:**
1. Check `enforcement_mode` is "block" not "alert"
2. Verify Lambda has DynamoDB permissions
3. Check CloudWatch Logs: `/aws/lambda/BedrockProxyFunction`
4. Ensure table names match in environment variables

### Metrics Not Updating

**Problem:** Real-time metrics not appearing

**Solution:**
1. Check Bedrock API calls are using correct profile ARNs
2. Verify CloudWatch metrics namespace: `AWS/Bedrock`
3. Check dimension: `ModelId` matches profile IDs
4. Wait 5 minutes for first data points

## 💡 Best Practices

### 1. Quota Management
- Set daily limits to 5-10% of monthly limit
- Use "alert" mode initially to observe patterns
- Switch to "block" mode after baseline established
- Review quota usage weekly

### 2. Cost Optimization
- Pre-request quota blocking saves money
- Use Athena for detailed cost analysis
- Tag Application Inference Profiles for AWS Cost Explorer
- Set up budget alerts

### 3. Monitoring
- Review dashboard daily
- Set up CloudWatch alarms at 80% quota
- Enable SNS notifications
- Query Athena weekly for trends

### 4. Security
- Rotate JWT signing keys regularly
- Use Cognito or Auth0 for production JWT
- Enable CloudTrail for API Gateway
- Review IAM policies quarterly

## 📊 Performance

### Latency
- API Gateway: ~10-20ms
- Lambda (quota check): ~50-100ms
- Bedrock (actual inference): ~500-2000ms
- DynamoDB (update): ~10-20ms

**Total overhead:** ~70-140ms (5-10% of total latency)

### Throughput
- Concurrent Lambda executions: 1000 (default)
- DynamoDB read/write capacity: On-demand (unlimited)
- API Gateway: 10,000 RPS (default)

### Cost
- Lambda: $0.20 per 1M requests
- DynamoDB: $1.25 per 1M reads/writes
- CloudWatch: $0.30 per custom metric
- S3: $0.023 per GB stored

**Example:** 1M Bedrock calls/month = ~$3-5 infrastructure overhead

## 🎯 Use Cases

### 1. Enterprise Multi-Tenant SaaS
- Isolate customers by tenant
- Enforce per-customer quotas
- Chargeback based on actual usage
- Compliance audit trail

### 2. Internal IT Cost Allocation
- Track usage by department
- Allocate costs to cost centers
- Monitor per-user consumption
- Identify high-usage teams

### 3. AI Application Development
- Monitor model performance
- Track token usage trends
- Identify optimization opportunities
- A/B test different prompts

### 4. Compliance & Security
- Full audit trail required
- Server-validated identity
- Cannot be spoofed by clients
- Immutable logs in S3

## 🚀 Roadmap

### Planned Features
- [ ] Real-time streaming dashboard updates
- [ ] QuickSight integration for advanced analytics
- [ ] Automated cost optimization recommendations
- [ ] Multi-region support
- [ ] Model performance benchmarking
- [ ] Prompt template management
- [ ] User self-service quota portal

## 📄 License

This solution is provided as-is for educational and reference purposes.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request
4. Include tests and documentation

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review CloudWatch Logs for errors
3. Verify IAM permissions
4. Check AWS service quotas

## 🎊 Summary

This solution provides **enterprise-grade** monitoring and quota enforcement for Amazon Bedrock with:

✅ **Real-time tracking** (not sample data)
✅ **Pre-request quota blocking** (saves cost)
✅ **Multi-tenant isolation** (4 tenants)
✅ **User-level quotas** (5 users)
✅ **Comprehensive dashboard** (14 widgets)
✅ **Full audit trail** (CloudWatch → S3 → Athena)
✅ **Cost attribution** (SQL queries)
✅ **Server-validated** (cannot be spoofed)
✅ **Production-ready** (encryption, monitoring, alarms)

**Deploy in minutes, monitor in real-time, control costs effectively!** 🚀
