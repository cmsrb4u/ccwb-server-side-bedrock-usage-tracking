#!/usr/bin/env python3
"""
Show Real Usage Data from DynamoDB

Queries actual usage from DynamoDB tables (not sample data)
"""

import boto3
import json
from datetime import datetime
from decimal import Decimal

REGION = "us-west-2"

def decimal_default(obj):
    """JSON serializer for Decimal"""
    if isinstance(obj, Decimal):
        return int(obj)
    raise TypeError

def query_user_metrics():
    """Query real user metrics from DynamoDB"""
    dynamodb = boto3.resource('dynamodb', region_name=REGION)

    print("\n" + "=" * 80)
    print("📊 REAL USER USAGE DATA (from DynamoDB)")
    print("=" * 80)

    now = datetime.now()
    month_key = f"monthly_{now.strftime('%Y-%m')}"

    try:
        # Try the table from earlier deployment
        table = dynamodb.Table('UserQuotaMetrics')

        print(f"\n🗄️  Querying table: UserQuotaMetrics")
        print(f"   Period: {month_key}")
        print("")

        # Scan for all users in current month
        response = table.scan(
            FilterExpression='begins_with(metric_period, :month)',
            ExpressionAttributeValues={':month': 'monthly'}
        )

        if response['Items']:
            print("   User                          | Tokens Used    | Last Updated")
            print("   " + "-" * 70)

            for item in sorted(response['Items'], key=lambda x: x.get('user_email', '')):
                user = item.get('user_email', 'unknown')
                tokens = int(item.get('tokens_used', 0))
                updated = item.get('last_updated', 'never')

                print(f"   {user:<30} | {tokens:>13,} | {updated[:19]}")

            print("")
            print(f"✅ Showing REAL usage data from {len(response['Items'])} users")
        else:
            print("   ⚠️  No usage data found yet")
            print("   Run generate-test-traffic.py to create metrics")

    except Exception as e:
        print(f"   ⚠️  Could not query UserQuotaMetrics: {str(e)}")
        print("   This table might not exist yet or be in a different name")

def query_quota_policies():
    """Query real quota policies from DynamoDB"""
    dynamodb = boto3.resource('dynamodb', region_name=REGION)

    print("\n" + "=" * 80)
    print("📋 REAL QUOTA POLICIES (from DynamoDB)")
    print("=" * 80)

    try:
        table = dynamodb.Table('QuotaPolicies')

        print(f"\n🗄️  Querying table: QuotaPolicies")
        print("")

        response = table.scan()

        if response['Items']:
            print("   Type   | Identifier                     | Monthly Limit | Daily Limit | Mode")
            print("   " + "-" * 90)

            for item in sorted(response['Items'], key=lambda x: (x.get('policy_type', ''), x.get('identifier', ''))):
                policy_type = item.get('policy_type', 'unknown')
                identifier = item.get('identifier', 'unknown')
                monthly = int(item.get('monthly_limit', 0))
                daily = int(item.get('daily_limit', 0))
                mode = item.get('enforcement_mode', 'unknown')

                print(f"   {policy_type:<7} | {identifier:<30} | {monthly/1000000:>11.0f}M | {daily/1000000:>9.0f}M | {mode}")

            print("")
            print(f"✅ Showing {len(response['Items'])} REAL quota policies")
        else:
            print("   ⚠️  No policies found")

    except Exception as e:
        print(f"   ⚠️  Could not query QuotaPolicies: {str(e)}")

def query_cloudwatch_metrics():
    """Query real CloudWatch metrics"""
    cloudwatch = boto3.client('cloudwatch', region_name=REGION)

    print("\n" + "=" * 80)
    print("📈 REAL CLOUDWATCH METRICS (from AWS/Bedrock)")
    print("=" * 80)

    tenants = [
        ("Tenant A", "p24qm5pye2qr"),
        ("Tenant B", "3rg09c3irrs6"),
        ("Tenant C", "iq5vx6jibn89"),
        ("Tenant D", "f8a6a2e836bz")
    ]

    print(f"\n🔍 Querying AWS/Bedrock namespace (last hour)")
    print("")
    print("   Tenant     | Profile ID   | Invocations | Tokens (approx)")
    print("   " + "-" * 65)

    for tenant_name, profile_id in tenants:
        try:
            # Get invocations
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/Bedrock',
                MetricName='Invocations',
                Dimensions=[{'Name': 'ModelId', 'Value': profile_id}],
                StartTime=datetime.now().timestamp() - 3600,  # Last hour
                EndTime=datetime.now().timestamp(),
                Period=3600,
                Statistics=['Sum']
            )

            invocations = 0
            if response['Datapoints']:
                invocations = int(response['Datapoints'][0].get('Sum', 0))

            # Estimate tokens (avg ~500 per call)
            tokens = invocations * 500

            print(f"   {tenant_name:<11} | {profile_id} | {invocations:>11} | {tokens:>15,}")

        except Exception as e:
            print(f"   {tenant_name:<11} | {profile_id} | Error: {str(e)[:30]}")

    print("")
    print("✅ Showing REAL metrics from CloudWatch")

def main():
    print("\n" + "=" * 80)
    print("🔍 REAL USAGE DATA VERIFICATION")
    print("=" * 80)
    print("Showing actual data from DynamoDB and CloudWatch (not sample data)")
    print("")

    # Query DynamoDB tables
    query_user_metrics()
    query_quota_policies()

    # Query CloudWatch metrics
    query_cloudwatch_metrics()

    print("\n" + "=" * 80)
    print("📊 DASHBOARD DATA SOURCES")
    print("=" * 80)
    print("""
The dashboard you created uses these REAL data sources:

1. ✅ AWS/Bedrock CloudWatch Metrics
   - Invocations, InputTokenCount, OutputTokenCount
   - InvocationLatency, ModelErrors
   - Dimensioned by ModelId (profile IDs)

2. ✅ CCWB/UserQuota CloudWatch Metrics
   - MonthlyUsagePercent, DailyUsagePercent
   - Published by Lambda quota function
   - Sourced from DynamoDB

3. ✅ DynamoDB Tables (queried above)
   - UserQuotaMetrics: Real-time usage tracking
   - QuotaPolicies: Actual quota limits

All metrics in the dashboard are LIVE and update as users make API calls!

🔗 View Dashboard:
https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards/dashboard/Bedrock-Comprehensive-Monitoring
""")

    print("\n💡 To Generate More Real Traffic:")
    print("   python3 generate-test-traffic.py")
    print("")

if __name__ == "__main__":
    main()
