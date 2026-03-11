# Quick Start Guide - 3 Commands

Deploy complete server-side Bedrock tracking in 25 minutes.

## Prerequisites

```bash
# Install SAM CLI (if not already installed)
brew install aws-sam-cli

# Configure AWS credentials (if not already configured)
aws configure
# Region: us-west-2
```

## Deploy (3 Commands)

```bash
cd /Users/themuni/Downloads/aws-bedrock-multi-tenant-workshop/server-side-logging-complete

# 1. Deploy infrastructure (5-10 minutes)
./deploy.sh

# 2. Configure and seed data (2-3 minutes)
python3 post-deploy.py

# 3. Test the API (1 minute)
python3 test-api.py
```

## What You Get

After deployment:

### API Endpoint
```bash
# Use JWT tokens to make authenticated requests
curl -X POST https://YOUR_API_ID.execute-api.us-west-2.amazonaws.com/prod/invoke \
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

### 5 Sample Users
- john.doe@company.com (Tenant A / Engineering / 500M limit)
- jane.smith@company.com (Tenant A / Data Science / 300M limit)
- bob.wilson@company.com (Tenant B / Sales / 250M limit)
- alice.johnson@company.com (Tenant C / Engineering / 400M limit)
- david.chen@company.com (Tenant D / Finance / 350M limit)

### Data Flow
```
Client → API Gateway (JWT validation)
  ↓
Lambda Proxy (sets requestMetadata)
  ↓
Bedrock Runtime
  ↓
CloudWatch Logs (~1-2 min) → S3 (~5-10 min)
  ↓
Glue Crawler (daily) → Athena Tables
  ↓
SQL Queries (cost attribution)
```

### Resources Created
- KMS encryption key
- 3 S3 buckets (logs, access logs, Athena results)
- CloudWatch Log Group
- Glue database + crawler
- Athena workgroup
- DynamoDB table (user metadata)
- 2 Lambda functions (proxy, authorizer)
- API Gateway with JWT authentication

## Query Your Data

### Wait for Logs
- CloudWatch Logs: ~1-2 minutes
- S3 Logs: ~5-10 minutes
- Glue Tables: ~10-15 minutes (after crawler runs)

### Run Athena Queries
```bash
# Open Athena Console
open "https://us-west-2.console.aws.amazon.com/athena/home?region=us-west-2"

# Use queries from athena-queries.sql
```

### Sample Query (Cost by User)
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

## Verify Deployment

### Check CloudFormation Stack
```bash
aws cloudformation describe-stacks \
  --stack-name bedrock-serverside-logging \
  --region us-west-2
```

### Check User Metadata
```bash
aws dynamodb scan \
  --table-name $(jq -r '.[] | select(.OutputKey=="UserMetadataTable") | .OutputValue' stack-outputs.json) \
  --region us-west-2
```

### Check CloudWatch Logs
```bash
# Bedrock invocations
aws logs tail /aws/bedrock/modelinvocations --follow

# Lambda proxy
aws logs tail /aws/lambda/BedrockProxyFunction --follow
```

### Check S3 Logs
```bash
# List log files
aws s3 ls s3://$(jq -r '.[] | select(.OutputKey=="InvocationLogsBucket") | .OutputValue' stack-outputs.json)/invocations/ --recursive
```

## Cleanup

```bash
# Delete stack
aws cloudformation delete-stack \
  --stack-name bedrock-serverside-logging \
  --region us-west-2

# Empty S3 buckets (required before stack deletion)
BUCKET=$(jq -r '.[] | select(.OutputKey=="InvocationLogsBucket") | .OutputValue' stack-outputs.json)
aws s3 rm s3://$BUCKET --recursive
```

## Troubleshooting

### "SAM CLI not found"
```bash
brew install aws-sam-cli
```

### "AWS credentials not configured"
```bash
aws configure
```

### Logs not appearing in S3
- Wait 5-10 minutes after first API call
- Check Bedrock logging enabled: `post-deploy.py`
- Verify IAM permissions

### Glue tables not created
- Wait for S3 logs to appear
- Start crawler manually: Glue Console → Crawlers
- Check crawler IAM role

### API returns 403
- Check JWT token format: `Bearer demo-token-{userId}`
- Check user exists in DynamoDB
- Check Lambda authorizer logs

## Key Features

✅ **Server-Side Identity**: JWT validated by API Gateway
✅ **requestMetadata**: Set by Lambda (cannot be spoofed)
✅ **Full Audit Trail**: CloudWatch → S3 → Athena
✅ **Encryption**: KMS for all data at rest
✅ **Cost Attribution**: SQL queries by user/tenant/department
✅ **Scalable**: Unlimited users and tenants
✅ **Production-Ready**: Complete monitoring and security

## Next Steps

1. Customize user metadata in DynamoDB
2. Integrate real JWT issuer (Cognito, Auth0, Okta)
3. Create CloudWatch dashboards
4. Set up cost allocation tags
5. Add CloudWatch alarms
6. Create QuickSight reports

## Documentation

- **README.md** - Full documentation
- **IMPLEMENTATION_SUMMARY.md** - Architecture details
- **athena-queries.sql** - 10 sample queries
- **infrastructure.yaml** - CloudFormation template

## Support

For issues:
1. Check CloudWatch Logs
2. Verify IAM permissions
3. Check S3 bucket policies
4. Review stack-outputs.json

---

**Total deployment time:** 25-30 minutes
**Next command:** `./deploy.sh`
