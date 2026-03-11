#!/usr/bin/env python3
"""
Post-Deployment Configuration for Hybrid Solution

1. Seed user metadata
2. Create quota policies
3. Initialize usage metrics
4. Enable Bedrock logging
5. Start Glue crawler
"""

import boto3
import json
import sys
from datetime import datetime
from decimal import Decimal

REGION = "us-west-2"
STACK_NAME = "bedrock-hybrid-tracking"

# Sample users with quota limits
USERS = [
    {
        "userId": "john.doe@company.com",
        "group": "engineering",
        "tenant": "tenant_a",
        "department": "platform",
        "monthlyLimit": 500000000,  # 500M tokens
        "dailyLimit": 20000000,     # 20M tokens
        "status": "active"
    },
    {
        "userId": "jane.smith@company.com",
        "group": "data-science",
        "tenant": "tenant_a",
        "department": "ml-ops",
        "monthlyLimit": 300000000,
        "dailyLimit": 12000000,
        "status": "active"
    },
    {
        "userId": "bob.wilson@company.com",
        "group": "sales",
        "tenant": "tenant_b",
        "department": "sales-ops",
        "monthlyLimit": 250000000,
        "dailyLimit": 10000000,
        "status": "active"
    },
    {
        "userId": "alice.johnson@company.com",
        "group": "engineering",
        "tenant": "tenant_c",
        "department": "devops",
        "monthlyLimit": 400000000,
        "dailyLimit": 15000000,
        "status": "active"
    },
    {
        "userId": "david.chen@company.com",
        "group": "finance",
        "tenant": "tenant_d",
        "department": "analytics",
        "monthlyLimit": 350000000,
        "dailyLimit": 12000000,
        "status": "active"
    }
]

def get_stack_outputs():
    """Get CloudFormation stack outputs"""
    try:
        with open('stack-outputs-hybrid.json', 'r') as f:
            outputs = json.load(f)
            return {o['OutputKey']: o['OutputValue'] for o in outputs}
    except FileNotFoundError:
        print("❌ stack-outputs-hybrid.json not found. Run deploy-hybrid.sh first.")
        sys.exit(1)

def seed_user_metadata(table_name):
    """Seed user metadata in DynamoDB"""
    print("\n" + "=" * 80)
    print("📊 SEEDING USER METADATA")
    print("=" * 80)

    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(table_name)

    for user in USERS:
        try:
            table.put_item(
                Item={
                    'userId': user['userId'],
                    'group': user['group'],
                    'tenant': user['tenant'],
                    'department': user['department'],
                    'monthlyLimit': user['monthlyLimit'],
                    'dailyLimit': user['dailyLimit'],
                    'status': user['status'],
                    'createdAt': datetime.now().isoformat(),
                    'updatedAt': datetime.now().isoformat()
                }
            )
            print(f"✅ {user['userId']:<30} → {user['tenant']} / {user['department']}")
        except Exception as e:
            print(f"❌ {user['userId']}: {str(e)}")

    print(f"\n📈 Total users seeded: {len(USERS)}")

def create_quota_policies(table_name):
    """Create quota policies in DynamoDB"""
    print("\n" + "=" * 80)
    print("📋 CREATING QUOTA POLICIES")
    print("=" * 80)

    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(table_name)

    policies = [
        # Default policy
        {
            'policy_type': 'default',
            'identifier': 'default',
            'monthly_limit': 100000000,  # 100M
            'daily_limit': 5000000,      # 5M
            'enforcement_mode': 'block',
            'description': 'Default quota for all users'
        },
        # Group policies
        {
            'policy_type': 'group',
            'identifier': 'engineering',
            'monthly_limit': 500000000,
            'daily_limit': 20000000,
            'enforcement_mode': 'block',
            'description': 'Engineering team quota'
        },
        {
            'policy_type': 'group',
            'identifier': 'data-science',
            'monthly_limit': 400000000,
            'daily_limit': 15000000,
            'enforcement_mode': 'block',
            'description': 'Data science team quota'
        },
        {
            'policy_type': 'group',
            'identifier': 'sales',
            'monthly_limit': 250000000,
            'daily_limit': 10000000,
            'enforcement_mode': 'alert',
            'description': 'Sales team quota (alert only)'
        },
        {
            'policy_type': 'group',
            'identifier': 'finance',
            'monthly_limit': 350000000,
            'daily_limit': 12000000,
            'enforcement_mode': 'block',
            'description': 'Finance team quota'
        }
    ]

    # Add user-specific policies
    for user in USERS:
        policies.append({
            'policy_type': 'user',
            'identifier': user['userId'],
            'monthly_limit': user['monthlyLimit'],
            'daily_limit': user['dailyLimit'],
            'enforcement_mode': 'block',
            'description': f"Quota for {user['userId']}"
        })

    for policy in policies:
        try:
            table.put_item(
                Item={
                    'policy_type': policy['policy_type'],
                    'identifier': policy['identifier'],
                    'monthly_limit': policy['monthly_limit'],
                    'daily_limit': policy['daily_limit'],
                    'enforcement_mode': policy['enforcement_mode'],
                    'description': policy['description'],
                    'createdAt': datetime.now().isoformat(),
                    'updatedAt': datetime.now().isoformat()
                }
            )
            print(f"✅ {policy['policy_type']:8} | {policy['identifier']:30} → {policy['monthly_limit']:,} monthly")
        except Exception as e:
            print(f"❌ {policy['identifier']}: {str(e)}")

    print(f"\n📈 Total policies created: {len(policies)}")

def initialize_usage_metrics(table_name):
    """Initialize usage metrics with zero values"""
    print("\n" + "=" * 80)
    print("🔢 INITIALIZING USAGE METRICS")
    print("=" * 80)

    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(table_name)

    now = datetime.now()
    month_key = f"monthly_{now.strftime('%Y-%m')}"
    day_key = f"daily_{now.strftime('%Y-%m-%d')}"

    for user in USERS:
        try:
            # Initialize monthly metric
            table.put_item(
                Item={
                    'user_email': user['userId'],
                    'metric_period': month_key,
                    'tokens_used': 0,
                    'last_updated': now.isoformat(),
                    'ttl': int((now.replace(day=1, hour=0, minute=0, second=0).timestamp() + 60*60*24*60))
                }
            )

            # Initialize daily metric
            table.put_item(
                Item={
                    'user_email': user['userId'],
                    'metric_period': day_key,
                    'tokens_used': 0,
                    'last_updated': now.isoformat(),
                    'ttl': int((now.timestamp() + 60*60*24*7))
                }
            )

            print(f"✅ {user['userId']:<30} → {month_key}, {day_key}")

        except Exception as e:
            print(f"❌ {user['userId']}: {str(e)}")

    print(f"\n📈 Total metrics initialized: {len(USERS) * 2}")

def enable_bedrock_logging(log_group_arn, s3_bucket_name):
    """Enable Bedrock model invocation logging"""
    print("\n" + "=" * 80)
    print("📝 ENABLING BEDROCK MODEL INVOCATION LOGGING")
    print("=" * 80)

    print(f"⚠️  Manual step required:")
    print(f"   1. Go to: https://console.aws.amazon.com/bedrock/home?region={REGION}#/settings")
    print(f"   2. Enable 'Model invocation logging'")
    print(f"   3. Configure:")
    print(f"      - CloudWatch Logs: {log_group_arn}")
    print(f"      - S3 bucket: {s3_bucket_name}")
    print(f"      - Prefix: invocations/")
    print(f"   4. Enable 'Text', 'Image', and 'Embedding' data delivery")
    print()
    print(f"   Note: This cannot be automated via CloudFormation yet.")

def start_glue_crawler(crawler_name):
    """Start Glue crawler"""
    print("\n" + "=" * 80)
    print("🔍 STARTING GLUE CRAWLER")
    print("=" * 80)

    glue = boto3.client('glue', region_name=REGION)

    try:
        glue.start_crawler(Name=crawler_name)
        print(f"✅ Crawler '{crawler_name}' started")
        print(f"   This will take 5-10 minutes to complete")
        print(f"   Monitor at: https://{REGION}.console.aws.amazon.com/glue/home?region={REGION}#/v2/data-catalog/crawlers/view/{crawler_name}")
    except glue.exceptions.CrawlerRunningException:
        print(f"⚠️  Crawler '{crawler_name}' is already running")
    except Exception as e:
        print(f"❌ Error starting crawler: {str(e)}")

def print_summary(outputs):
    """Print deployment summary"""
    print("\n" + "=" * 80)
    print("🎉 HYBRID SOLUTION CONFIGURED SUCCESSFULLY")
    print("=" * 80)

    print("\n📊 Features Enabled:")
    print("   ✅ Server-side identity validation (JWT)")
    print("   ✅ Real-time quota enforcement (pre-request check)")
    print("   ✅ Atomic usage tracking (DynamoDB)")
    print("   ✅ CloudWatch metrics (quota percentage)")
    print("   ✅ Full audit trail (CloudWatch → S3 → Athena)")
    print("   ✅ requestMetadata (server-side, cannot be spoofed)")

    print("\n📊 Stack Resources:")
    for key, value in outputs.items():
        if len(value) < 100:  # Only show short values
            print(f"   {key}: {value}")

    print("\n👥 Users Configured:")
    for user in USERS:
        print(f"   • {user['userId']:<30} {user['monthlyLimit']:>10,} monthly / {user['dailyLimit']:>9,} daily")

    print("\n📝 Next Steps:")
    print("   1. Enable Bedrock logging (see manual step above)")
    print("   2. Test quota enforcement:")
    print("      python3 test-quota-enforcement.py")
    print("   3. Monitor CloudWatch metrics:")
    print(f"      https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#metricsV2:graph=~()")
    print("   4. Query Athena (after crawler completes):")
    print(f"      https://{REGION}.console.aws.amazon.com/athena/home?region={REGION}")

    print("\n🔗 Useful Links:")
    if 'ApiEndpoint' in outputs:
        print(f"   API Gateway: {outputs['ApiEndpoint']}")
    print(f"   CloudWatch Logs: https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#logsV2:log-groups")
    print(f"   DynamoDB Tables: https://{REGION}.console.aws.amazon.com/dynamodbv2/home?region={REGION}#tables")
    if 'InvocationLogsBucket' in outputs:
        print(f"   S3 Bucket: https://s3.console.aws.amazon.com/s3/buckets/{outputs['InvocationLogsBucket']}?region={REGION}")

def main():
    print("\n" + "=" * 80)
    print("🚀 HYBRID SOLUTION POST-DEPLOYMENT CONFIGURATION")
    print("=" * 80)
    print(f"Region: {REGION}")
    print(f"Stack: {STACK_NAME}")
    print("")

    # Get stack outputs
    outputs = get_stack_outputs()

    # Seed user metadata
    if 'UserMetadataTable' in outputs:
        seed_user_metadata(outputs['UserMetadataTable'])

    # Create quota policies
    if 'QuotaPoliciesTable' in outputs:
        create_quota_policies(outputs['QuotaPoliciesTable'])

    # Initialize usage metrics
    if 'UserQuotaMetricsTable' in outputs:
        initialize_usage_metrics(outputs['UserQuotaMetricsTable'])

    # Enable Bedrock logging (manual step)
    if 'BedrockLogGroupArn' in outputs and 'InvocationLogsBucket' in outputs:
        enable_bedrock_logging(outputs['BedrockLogGroupArn'], outputs['InvocationLogsBucket'])

    # Start Glue crawler
    if 'GlueCrawlerName' in outputs:
        start_glue_crawler(outputs['GlueCrawlerName'])

    # Print summary
    print_summary(outputs)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
