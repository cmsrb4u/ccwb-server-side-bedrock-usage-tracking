# Hybrid Solution: Server-Side Logging + Quota Enforcement

Complete solution combining server-side identity validation, real-time quota enforcement, and full audit trail.

## 🎯 What This Solution Provides

### 1. Server-Side Identity Validation
- JWT tokens validated by API Gateway custom authorizer
- User metadata stored in DynamoDB
- requestMetadata set by Lambda proxy (server-side, cannot be spoofed)

### 2. Real-Time Quota Enforcement
- **Pre-request quota check** - blocks before calling Bedrock
- **Atomic usage tracking** - DynamoDB counters
- **CloudWatch metrics** - quota percentage monitoring
- **429 errors** - quota exceeded responses
- **Per-user and per-group** limits

### 3. Full Audit Trail
- CloudWatch Logs (~1-2 minutes)
- S3 invocation logs (~5-10 minutes)
- Glue crawler (schema discovery)
- Athena queries (SQL-based cost attribution)

### 4. Cost Attribution
- Per-user tracking
- Per-tenant tracking
- Per-department tracking
- Custom metadata (any JSON fields)

## 🏗️ Architecture

```
┌──────────────┐
│   Client     │ (sends JWT token)
└──────┬───────┘
       │
       ↓
┌─────────────────────────┐
│  API Gateway            │ ← JWT Authorizer validates token
└──────┬──────────────────┘
       │
       ↓
┌─────────────────────────┐
│  Lambda Proxy           │
│  ┌──────────────────┐   │
│  │ 1. Get user info │   │ ← DynamoDB (UserMetadata)
│  │ 2. Get quota     │   │ ← DynamoDB (QuotaPolicies)
│  │ 3. Check quota   │   │ ← DynamoDB (UserQuotaMetrics)
│  │ 4. Block if over │   │ → Return 429 if exceeded
│  │ 5. Invoke Bedrock│   │ → With server-side requestMetadata
│  │ 6. Update usage  │   │ → DynamoDB atomic increment
│  │ 7. Publish metrics│  │ → CloudWatch
│  └──────────────────┘   │
└──────┬──────────────────┘
       │
       ↓
┌─────────────────────────┐
│  Bedrock Runtime        │ → Invokes model
└──────┬──────────────────┘
       │
       ↓
┌─────────────────────────┐
│  CloudWatch Logs        │ → Real-time logs (1-2 min)
└──────┬──────────────────┘
       │
       ↓
┌─────────────────────────┐
│  S3 Bucket              │ → Durable storage (5-10 min)
└──────┬──────────────────┘
       │
       ↓
┌─────────────────────────┐
│  Glue Crawler           │ → Schema discovery (daily)
└──────┬──────────────────┘
       │
       ↓
┌─────────────────────────┐
│  Athena                 │ → SQL queries (cost attribution)
└─────────────────────────┘
```

## 🚀 Deployment

### Prerequisites

```bash
# Install SAM CLI
brew install aws-sam-cli

# Configure AWS credentials
aws configure
# Region: us-west-2
```

### Deploy in 3 Commands

```bash
cd /Users/themuni/Downloads/aws-bedrock-multi-tenant-workshop/server-side-logging-complete

# 1. Deploy infrastructure (5-10 minutes)
./deploy-hybrid.sh

# 2. Configure and seed data (2-3 minutes)
python3 post-deploy-hybrid.py

# 3. Test quota enforcement (1 minute)
python3 test-quota-enforcement.py
```

## 📊 What Gets Created

### DynamoDB Tables (3)

1. **UserMetadata** - User information
   ```json
   {
     "userId": "john.doe@company.com",
     "group": "engineering",
     "tenant": "tenant_a",
     "department": "platform",
     "monthlyLimit": 500000000,
     "dailyLimit": 20000000,
     "status": "active"
   }
   ```

2. **QuotaPolicies** - Quota limits (user, group, default)
   ```json
   {
     "policy_type": "user",
     "identifier": "john.doe@company.com",
     "monthly_limit": 500000000,
     "daily_limit": 20000000,
     "enforcement_mode": "block"
   }
   ```

3. **UserQuotaMetrics** - Real-time usage tracking
   ```json
   {
     "user_email": "john.doe@company.com",
     "metric_period": "monthly_2026-03",
     "tokens_used": 1234567,
     "last_updated": "2026-03-11T15:30:00",
     "ttl": 1742515200
   }
   ```

### Infrastructure

- KMS encryption key
- 3 S3 buckets (logs, access logs, Athena results)
- CloudWatch Log Group
- Glue database + crawler
- Athena workgroup
- 2 Lambda functions (proxy, authorizer)
- API Gateway with JWT authentication
- CloudWatch alarms (quota usage, Lambda errors)
- SNS topic for alerts

## 🔐 Quota Enforcement Flow

### Step-by-Step

1. **Client sends request** with JWT token
   ```bash
   curl -X POST https://api.execute-api.us-west-2.amazonaws.com/prod/invoke \
     -H "Authorization: Bearer demo-token-john.doe@company.com" \
     -H "Content-Type: application/json" \
     -d '{"messages": [...]}'
   ```

2. **API Gateway validates JWT**
   - Calls Lambda authorizer
   - Authorizer extracts userId from token
   - Returns IAM policy if valid

3. **Lambda Proxy checks quota** (before Bedrock call)
   ```python
   # Get current usage
   monthly_usage = get_usage(user_id, "monthly_2026-03")
   daily_usage = get_usage(user_id, "daily_2026-03-11")

   # Get limits
   quota_policy = get_quota_policy(user_id)
   monthly_limit = quota_policy['monthly_limit']
   daily_limit = quota_policy['daily_limit']

   # Check if exceeded
   if monthly_usage >= monthly_limit:
       return 429_error("Monthly quota exceeded")

   if daily_usage >= daily_limit:
       return 429_error("Daily quota exceeded")
   ```

4. **If quota OK, invoke Bedrock** with server-side metadata
   ```python
   request_metadata = {
       'userId': user_id,
       'tenant': user_metadata['tenant'],
       'department': user_metadata['department'],
       'quotaEnabled': True,
       'monthlyLimit': monthly_limit
   }

   response = bedrock.invoke_model(
       modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
       body=body,
       requestMetadata=request_metadata  # SERVER-SIDE
   )
   ```

5. **Update usage atomically** (after success)
   ```python
   tokens_used = response['usage']['input_tokens'] + response['usage']['output_tokens']

   # Atomic increment in DynamoDB
   table.update_item(
       Key={'user_email': user_id, 'metric_period': 'monthly_2026-03'},
       UpdateExpression='ADD tokens_used :tokens',
       ExpressionAttributeValues={':tokens': tokens_used}
   )
   ```

6. **Publish CloudWatch metrics**
   ```python
   cloudwatch.put_metric_data(
       Namespace='Bedrock/Quota',
       MetricData=[{
           'MetricName': 'MonthlyUsagePercent',
           'Value': (monthly_usage / monthly_limit) * 100,
           'Dimensions': [
               {'Name': 'UserId', 'Value': user_id},
               {'Name': 'Tenant', 'Value': tenant}
           ]
       }]
   )
   ```

7. **Return response** with quota info
   ```json
   {
     "content": [...],
     "usage": {
       "total_tokens": 234
     },
     "quota": {
       "monthly_limit": 500000000,
       "monthly_used": 1234567,
       "monthly_remaining": 498765433,
       "daily_limit": 20000000,
       "daily_used": 12345,
       "daily_remaining": 19987655
     },
     "metadata": {
       "userId": "john.doe@company.com",
       "tenant": "tenant_a",
       "quotaEnabled": true
     }
   }
   ```

## 🚫 Quota Exceeded Response

When quota is exceeded, the API returns 429:

```json
{
  "statusCode": 429,
  "headers": {
    "Retry-After": "3600"
  },
  "body": {
    "error": "Quota exceeded",
    "message": "Monthly quota exceeded (500000234/500000000 tokens)",
    "quota": {
      "monthly_used": 500000234,
      "monthly_limit": 500000000,
      "daily_used": 12345,
      "daily_limit": 20000000
    }
  }
}
```

**Key points:**
- ❌ Bedrock is **NOT called** (saves cost)
- ❌ No tokens consumed
- ✅ User gets clear error message
- ✅ Quota info in response
- ✅ Retry-After header (1 hour)

## 📊 Quota Policies

### Hierarchy (checked in order)

1. **User-specific policy** (highest priority)
   ```
   policy_type: "user"
   identifier: "john.doe@company.com"
   ```

2. **Group policy**
   ```
   policy_type: "group"
   identifier: "engineering"
   ```

3. **Default policy** (fallback)
   ```
   policy_type: "default"
   identifier: "default"
   ```

### Enforcement Modes

- **block** - Return 429 error when exceeded
- **alert** - Allow but publish CloudWatch alarm

### Example Policies

```python
# User-specific (overrides group)
{
  'policy_type': 'user',
  'identifier': 'john.doe@company.com',
  'monthly_limit': 500000000,  # 500M tokens
  'daily_limit': 20000000,     # 20M tokens
  'enforcement_mode': 'block'
}

# Group policy (for all engineering)
{
  'policy_type': 'group',
  'identifier': 'engineering',
  'monthly_limit': 400000000,
  'daily_limit': 15000000,
  'enforcement_mode': 'block'
}

# Default (fallback)
{
  'policy_type': 'default',
  'identifier': 'default',
  'monthly_limit': 100000000,
  'daily_limit': 5000000,
  'enforcement_mode': 'alert'  # Warn but allow
}
```

## 📈 CloudWatch Metrics

### Published Metrics

Namespace: `Bedrock/Quota`

1. **MonthlyUsagePercent**
   - Dimensions: UserId, Tenant
   - Unit: Percent
   - Use: Monitor quota utilization

2. **DailyUsagePercent**
   - Dimensions: UserId, Tenant
   - Unit: Percent
   - Use: Track daily consumption

3. **TokensUsed**
   - Dimensions: UserId, Tenant
   - Unit: Count
   - Use: Track actual usage

### CloudWatch Alarms

1. **High Quota Usage** - Triggers at 80% monthly usage
2. **Lambda Errors** - Triggers on 5+ errors in 5 minutes

## 🔍 Monitoring

### Real-Time (CloudWatch Logs)

```bash
# Watch Lambda proxy logs
aws logs tail /aws/lambda/bedrock-hybrid-tracking-bedrock-proxy --follow

# Watch Bedrock invocation logs
aws logs tail /aws/bedrock/modelinvocations --follow
```

### Usage Tracking (DynamoDB)

```bash
# Get user's monthly usage
aws dynamodb get-item \
  --table-name bedrock-hybrid-tracking-UserQuotaMetrics \
  --key '{"user_email":{"S":"john.doe@company.com"},"metric_period":{"S":"monthly_2026-03"}}' \
  --region us-west-2
```

### Quota Metrics (CloudWatch)

```bash
# Get user's quota percentage
aws cloudwatch get-metric-statistics \
  --namespace Bedrock/Quota \
  --metric-name MonthlyUsagePercent \
  --dimensions Name=UserId,Value=john.doe@company.com \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Maximum \
  --region us-west-2
```

## 💰 Cost Attribution

### By User (Athena Query)

```sql
SELECT
    json_extract_scalar(requestmetadata, '$.userId') AS user,
    SUM(CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER)) AS input_tokens,
    SUM(CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)) AS output_tokens,
    ROUND(
        (SUM(CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER)) * 3.00 / 1000000.0) +
        (SUM(CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)) * 15.00 / 1000000.0),
        4
    ) AS cost_usd
FROM invocations
WHERE from_iso8601_timestamp(timestamp) >= current_date - interval '30' day
GROUP BY json_extract_scalar(requestmetadata, '$.userId')
ORDER BY cost_usd DESC;
```

### By Tenant

```sql
SELECT
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    COUNT(*) AS invocation_count,
    SUM(
        CAST(json_extract_scalar(usage, '$.inputTokens') AS INTEGER) +
        CAST(json_extract_scalar(usage, '$.outputTokens') AS INTEGER)
    ) AS total_tokens,
    ROUND((SUM(...) * 9.00 / 1000000.0), 2) AS cost_usd
FROM invocations
WHERE month = '2026-03'
GROUP BY tenant
ORDER BY cost_usd DESC;
```

## 🔒 Security Features

### Trust Model

| Component | Trust Level | Why |
|-----------|-------------|-----|
| JWT Token | ✅ High | Signature validated by API Gateway |
| User Identity | ✅ High | Extracted by authorizer (server-side) |
| Quota Check | ✅ High | Lambda checks before Bedrock call |
| requestMetadata | ✅ High | Set by Lambda (after auth) |
| Usage Tracking | ✅ High | DynamoDB atomic operations |
| CloudWatch Logs | ✅ High | AWS service, immutable |
| S3 Logs | ✅ High | KMS encrypted, versioned |

### Cannot Be Spoofed

- ❌ Client cannot modify JWT (signature validation)
- ❌ Client cannot bypass quota (checked server-side)
- ❌ Client cannot modify requestMetadata (set by Lambda)
- ❌ Client cannot fake usage (DynamoDB atomic)
- ❌ Client cannot modify logs (AWS services)

## 🎛️ Configuration

### Add New User

```bash
# Add to UserMetadata table
aws dynamodb put-item \
  --table-name bedrock-hybrid-tracking-UserMetadata \
  --item '{
    "userId": {"S": "new.user@company.com"},
    "group": {"S": "engineering"},
    "tenant": {"S": "tenant_a"},
    "department": {"S": "backend"},
    "monthlyLimit": {"N": "400000000"},
    "dailyLimit": {"N": "15000000"},
    "status": {"S": "active"}
  }' \
  --region us-west-2

# Add quota policy
aws dynamodb put-item \
  --table-name bedrock-hybrid-tracking-QuotaPolicies \
  --item '{
    "policy_type": {"S": "user"},
    "identifier": {"S": "new.user@company.com"},
    "monthly_limit": {"N": "400000000"},
    "daily_limit": {"N": "15000000"},
    "enforcement_mode": {"S": "block"}
  }' \
  --region us-west-2
```

### Update Quota

```bash
aws dynamodb update-item \
  --table-name bedrock-hybrid-tracking-QuotaPolicies \
  --key '{"policy_type":{"S":"user"},"identifier":{"S":"john.doe@company.com"}}' \
  --update-expression "SET monthly_limit = :limit" \
  --expression-attribute-values '{":limit":{"N":"600000000"}}' \
  --region us-west-2
```

### Change Enforcement Mode

```bash
# Switch from "block" to "alert" (allow but warn)
aws dynamodb update-item \
  --table-name bedrock-hybrid-tracking-QuotaPolicies \
  --key '{"policy_type":{"S":"user"},"identifier":{"S":"john.doe@company.com"}}' \
  --update-expression "SET enforcement_mode = :mode" \
  --expression-attribute-values '{":mode":{"S":"alert"}}' \
  --region us-west-2
```

## 🧪 Testing

### Test Normal Call

```bash
python3 test-quota-enforcement.py
```

### Manual API Test

```bash
# Get API endpoint
API_ENDPOINT=$(jq -r '.[] | select(.OutputKey=="ApiEndpoint") | .OutputValue' stack-outputs-hybrid.json)

# Make request
curl -X POST "${API_ENDPOINT}/invoke" \
  -H "Authorization: Bearer demo-token-john.doe@company.com" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": [{"type": "text", "text": "Hello"}]
    }],
    "max_tokens": 100
  }'
```

### Test Quota Exceeded

```bash
# Temporarily lower quota, then make multiple calls
# See test-quota-enforcement.py for details
```

## 🆘 Troubleshooting

### "429 Quota Exceeded" but usage seems low

- Check both monthly AND daily limits
- Verify DynamoDB tables have correct data
- Check Lambda logs for quota calculation

### Quota not enforcing

- Verify `enforcement_mode` is "block" not "alert"
- Check Lambda has DynamoDB permissions
- Verify table names in Lambda environment variables

### Metrics not appearing in CloudWatch

- Wait 2-5 minutes after first call
- Check Lambda has cloudwatch:PutMetricData permission
- Verify namespace is "Bedrock/Quota"

### Usage not tracking

- Check DynamoDB table exists
- Verify atomic updates are working (no errors in Lambda logs)
- Check TTL is set correctly

## 📚 Additional Resources

- **infrastructure-with-quotas.yaml** - Complete CloudFormation template
- **deploy-hybrid.sh** - Deployment script
- **post-deploy-hybrid.py** - Configuration script
- **test-quota-enforcement.py** - Testing script
- **athena-queries.sql** - SQL queries for cost analysis

## 🎯 Key Advantages

### vs Basic Server-Side Logging

| Feature | Basic | Hybrid |
|---------|-------|--------|
| Identity validation | ✅ | ✅ |
| Audit trail | ✅ | ✅ |
| Real-time quota enforcement | ❌ | ✅ |
| Pre-request blocking | ❌ | ✅ |
| Usage tracking | ⚠️ Post-hoc | ✅ Real-time |
| CloudWatch quota metrics | ❌ | ✅ |
| 429 errors | ❌ | ✅ |

### vs CCWB Only

| Feature | CCWB | Hybrid |
|---------|------|--------|
| Quota enforcement | ✅ | ✅ |
| Usage tracking | ✅ | ✅ |
| Server-side identity | ⚠️ Optional | ✅ Required |
| Full audit trail | ⚠️ Limited | ✅ Complete |
| S3 logs | ❌ | ✅ |
| Athena queries | ❌ | ✅ |
| requestMetadata | ⚠️ Optional | ✅ Always |

## 🎊 Summary

This hybrid solution provides:

✅ **Server-validated identity** (JWT + API Gateway)
✅ **Real-time quota enforcement** (pre-request blocking)
✅ **Atomic usage tracking** (DynamoDB)
✅ **CloudWatch metrics** (quota percentage)
✅ **Full audit trail** (CloudWatch → S3 → Athena)
✅ **Cost attribution** (SQL queries)
✅ **High security** (cannot be spoofed)
✅ **Production-ready** (encryption, monitoring, alarms)

**Best of both worlds: CCWB quota enforcement + server-side audit trail!**
