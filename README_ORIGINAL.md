# Server-Side Bedrock Usage Tracking (Fresh Implementation)

Complete server-side tracking solution for Amazon Bedrock without Application Inference Profiles.

## Architecture

This implementation provides:
- Server-side identity validation via JWT tokens
- requestMetadata set server-side (cannot be spoofed)
- Full audit trail in CloudWatch Logs and S3
- Athena queries for cost attribution
- KMS encryption at rest
- Daily Glue crawler for schema discovery

### Key Components

```
┌─────────────┐
│   Client    │ (sends JWT token)
└──────┬──────┘
       │
       ↓
┌─────────────────┐
│  API Gateway    │ ← Custom JWT Authorizer
└──────┬──────────┘
       │
       ↓
┌─────────────────┐
│ Lambda Proxy    │ ← Sets requestMetadata server-side
└──────┬──────────┘
       │
       ↓
┌─────────────────┐
│ Bedrock Runtime │ → CloudWatch Logs → S3
└─────────────────┘         ↓             ↓
                      (1-2 min)     (5-10 min)
                            ↓             ↓
                     ┌────────────────────┘
                     │
                     ↓
              ┌─────────────┐
              │ Glue Crawler│ → Creates tables
              └──────┬──────┘
                     ↓
              ┌─────────────┐
              │   Athena    │ → Cost queries
              └─────────────┘
```

## Features

### Server-Side Identity Validation
- JWT tokens validated by API Gateway custom authorizer
- User metadata stored in DynamoDB
- requestMetadata set by Lambda proxy function (server-side, high trust)
- Cannot be spoofed by clients

### Encryption
- KMS key for all data at rest
- CloudWatch Logs encrypted
- S3 buckets encrypted
- Athena results encrypted

### Cost Attribution
- Per-user tracking via requestMetadata
- Per-tenant tracking via requestMetadata
- Per-department tracking via requestMetadata
- Athena queries for chargeback reports

### Audit Trail
- CloudWatch Logs: real-time streaming (~1-2 minutes)
- S3: durable storage with lifecycle policies (~5-10 minutes)
- Glue: automated schema discovery (daily)
- Athena: SQL queries for compliance and cost analysis

## Deployment

### Prerequisites

```bash
# Install AWS SAM CLI
brew install aws-sam-cli

# Configure AWS credentials
aws configure
```

### Step 1: Deploy Infrastructure

```bash
cd /Users/themuni/Downloads/aws-bedrock-multi-tenant-workshop/server-side-logging-complete

# Make scripts executable
chmod +x deploy.sh

# Deploy CloudFormation stack
./deploy.sh
```

This will create:
- KMS encryption key
- S3 buckets (invocation logs, access logs, Athena results)
- CloudWatch Log Group
- Glue database and crawler
- Athena workgroup
- DynamoDB table for user metadata
- Lambda functions (Bedrock proxy, JWT authorizer)
- API Gateway with custom authorizer

### Step 2: Post-Deployment Configuration

```bash
# Enable Bedrock logging and seed user data
python3 post-deploy.py
```

This will:
- Enable Bedrock model invocation logging
- Seed sample user metadata in DynamoDB
- Start Glue crawler for initial run
- Test Athena setup

### Step 3: Test the API

```bash
# Test API Gateway endpoint
python3 test-api.py
```

This will:
- Make test API calls with different user identities
- Verify CloudWatch Logs
- Check S3 log files
- Check Glue tables

### Step 4: Query Logs with Athena

```bash
# Open Athena Console
open "https://us-west-2.console.aws.amazon.com/athena/home?region=us-west-2"

# Run queries from athena-queries.sql
```

## API Usage

### Authentication

Use JWT tokens in the Authorization header:

```bash
# Demo token format: Bearer demo-token-{userId}
curl -X POST https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/invoke \
  -H "Authorization: Bearer demo-token-john.doe@company.com" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": [{"type": "text", "text": "Hello"}]
    }],
    "max_tokens": 100,
    "anthropic_version": "bedrock-2023-05-31"
  }'
```

### requestMetadata (Server-Side)

The Lambda proxy function automatically sets requestMetadata:

```python
request_metadata = {
    'userId': 'john.doe@company.com',      # From JWT
    'group': 'engineering',                 # From DynamoDB
    'tenant': 'tenant_a',                   # From DynamoDB
    'department': 'platform',               # From DynamoDB
    'source': 'server-side-gateway',        # Server identifier
    'timestamp': '2026-03-11T03:30:00'      # Server timestamp
}

response = bedrock_runtime.invoke_model(
    modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
    body=body,
    requestMetadata=request_metadata
)
```

## Data Flow Timeline

| Time | Layer | Location | Use Case |
|------|-------|----------|----------|
| ~1 min | CloudWatch Logs | `/aws/bedrock/modelinvocations` | Real-time monitoring |
| ~5 min | S3 | `s3://bucket/invocations/` | Durable storage |
| ~10 min | Glue Tables | Athena database | SQL queries |
| Daily | Glue Crawler | Automated | Schema updates |

## Cost Attribution Queries

### By User

```sql
SELECT
    json_extract_scalar(requestmetadata, '$.userId') AS user_id,
    SUM(tokens) AS total_tokens,
    SUM(tokens) * 0.009 / 1000 AS cost_usd
FROM invocations
WHERE month = '2026-03'
GROUP BY user_id;
```

### By Tenant

```sql
SELECT
    json_extract_scalar(requestmetadata, '$.tenant') AS tenant,
    SUM(tokens) AS total_tokens,
    SUM(tokens) * 0.009 / 1000 AS cost_usd
FROM invocations
WHERE month = '2026-03'
GROUP BY tenant;
```

### By Department

```sql
SELECT
    json_extract_scalar(requestmetadata, '$.department') AS department,
    SUM(tokens) AS total_tokens,
    SUM(tokens) * 0.009 / 1000 AS cost_usd
FROM invocations
WHERE month = '2026-03'
GROUP BY department;
```

## Security

### Trust Model

| Component | Trust Level | Why |
|-----------|-------------|-----|
| JWT Authorizer | ✅ High | AWS Lambda validates tokens |
| requestMetadata | ✅ High | Set by Lambda (server-side) |
| CloudWatch Logs | ✅ High | AWS service, immutable |
| S3 Logs | ✅ High | KMS encrypted, versioned |

### Cannot Be Spoofed

- Client cannot modify JWT token (signature validation fails)
- Client cannot modify requestMetadata (set server-side after auth)
- Client cannot modify CloudWatch Logs (AWS service)
- Client cannot modify S3 logs (write-only permissions)

## Monitoring

### CloudWatch Alarms

```bash
# High token usage alert
aws cloudwatch put-metric-alarm \
  --alarm-name HighTokenUsage \
  --metric-name InputTokenCount \
  --namespace AWS/Bedrock \
  --statistic Sum \
  --period 3600 \
  --evaluation-periods 1 \
  --threshold 1000000 \
  --comparison-operator GreaterThanThreshold
```

### Lambda Logs

```bash
# Bedrock Proxy Function logs
aws logs tail /aws/lambda/BedrockProxyFunction --follow

# JWT Authorizer logs
aws logs tail /aws/lambda/JWTAuthorizerFunction --follow
```

## Lifecycle Policies

S3 bucket lifecycle:
- 0-30 days: Standard storage
- 30-90 days: Infrequent Access
- 90+ days: Glacier

## Cleanup

```bash
# Delete the stack
aws cloudformation delete-stack \
  --stack-name bedrock-serverside-logging \
  --region us-west-2

# Empty S3 buckets first (versioned buckets require special handling)
aws s3 rm s3://your-bucket-name --recursive
```

## Troubleshooting

### Logs not appearing in S3

- Wait 5-10 minutes after invocation
- Check Bedrock logging is enabled: Bedrock Console → Settings
- Verify IAM role has S3 write permissions

### Glue crawler not creating tables

- Check crawler status: Glue Console → Crawlers
- Verify S3 bucket has log files
- Check crawler IAM role permissions

### Athena queries failing

- Wait for Glue crawler to complete
- Verify database name in query
- Check Athena workgroup configuration

## Architecture Benefits

### vs Application Inference Profiles (AIPs)

| Feature | AIP | Server-Side Logging |
|---------|-----|---------------------|
| Tenant isolation | ✅ Yes | ⚠️ Via requestMetadata |
| User-level tracking | ❌ No | ✅ Yes |
| CloudWatch metrics | ✅ Yes | ✅ Yes |
| requestMetadata | ⚠️ Optional | ✅ Required |
| Cost attribution | ✅ Native | ✅ Via Athena |
| Trust level | ✅ High | ✅ High |

### When to Use Each

**Use AIPs when:**
- You need strict tenant isolation
- You want native CloudWatch metrics by profile
- You have a small number of tenants (<10)

**Use Server-Side Logging when:**
- You need user-level tracking
- You need flexible metadata (department, group, etc.)
- You need SQL queries for cost analysis
- You have many users or complex hierarchies

## Files

```
server-side-logging-complete/
├── infrastructure.yaml      # CloudFormation/SAM template
├── deploy.sh               # Deployment script
├── post-deploy.py          # Post-deployment configuration
├── test-api.py             # API testing script
├── athena-queries.sql      # Sample Athena queries
├── README.md               # This file
└── stack-outputs.json      # Generated after deployment
```

## Support

For issues or questions:
1. Check CloudWatch Logs for errors
2. Review IAM permissions
3. Verify Bedrock logging is enabled
4. Check S3 bucket policies

## Next Steps

1. Deploy to production
2. Set up CloudWatch alarms
3. Create cost allocation tags
4. Integrate with billing system
5. Add custom user attributes to DynamoDB
6. Create Athena views for common queries
7. Set up automated reports with QuickSight
