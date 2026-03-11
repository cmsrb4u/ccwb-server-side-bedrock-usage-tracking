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

![Dashboard Screenshot](https://via.placeholder.com/800x400?text=Bedrock+Multi-Tenant+Dashboard)

**Features:**
- Real-time tenant comparison (4 tenants)
- User quota monitoring (5 users)
- Token usage trends
- Latency & error tracking
- Cost estimates
- System health status

## 🏗️ Architecture

```
Client (JWT Token)
    ↓
API Gateway (JWT Validation)
    ↓
Lambda Proxy
    ├─ Check Quota (DynamoDB)
    ├─ Invoke Bedrock (with requestMetadata)
    ├─ Update Usage (Atomic)
    └─ Publish Metrics (CloudWatch)
    ↓
CloudWatch → S3 → Glue → Athena
```

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
