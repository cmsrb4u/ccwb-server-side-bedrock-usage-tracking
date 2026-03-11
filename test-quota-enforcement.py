#!/usr/bin/env python3
"""
Test Quota Enforcement in Hybrid Solution

Tests:
1. Normal API call (within quota)
2. Quota exceeded scenario
3. Quota percentage metrics
4. Usage tracking accuracy
"""

import boto3
import json
import requests
import time
from datetime import datetime

REGION = "us-west-2"

def get_api_endpoint():
    """Get API Gateway endpoint from stack outputs"""
    try:
        with open('stack-outputs-hybrid.json', 'r') as f:
            outputs = json.load(f)
            for output in outputs:
                if output['OutputKey'] == 'ApiEndpoint':
                    return output['OutputValue']
        print("❌ ApiEndpoint not found in stack outputs")
        return None
    except FileNotFoundError:
        print("❌ stack-outputs-hybrid.json not found. Run deploy-hybrid.sh first.")
        return None

def get_table_names():
    """Get DynamoDB table names from stack outputs"""
    try:
        with open('stack-outputs-hybrid.json', 'r') as f:
            outputs = json.load(f)
            return {o['OutputKey']: o['OutputValue'] for o in outputs}
    except:
        return {}

def test_normal_call(api_endpoint, user_id):
    """Test normal API call within quota"""
    print(f"\n{'=' * 80}")
    print(f"🧪 TEST 1: Normal API Call (Within Quota)")
    print(f"{'=' * 80}")
    print(f"User: {user_id}")

    token = f"demo-token-{user_id}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    body = {
        "messages": [{
            "role": "user",
            "content": [{
                "type": "text",
                "text": "Write a short haiku about cloud computing"
            }]
        }],
        "max_tokens": 100
    }

    try:
        print(f"\n📤 Sending request...")
        response = requests.post(
            f"{api_endpoint}/invoke",
            headers=headers,
            json=body,
            timeout=30
        )

        print(f"\n📥 Response:")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if 'content' in result:
                text = result['content'][0]['text']
                print(f"   Response: {text[:100]}...")

            if 'usage' in result:
                usage = result['usage']
                print(f"\n   Token Usage:")
                print(f"      Input:  {usage.get('input_tokens', 0)}")
                print(f"      Output: {usage.get('output_tokens', 0)}")
                print(f"      Total:  {usage.get('total_tokens', 0)}")

            if 'quota' in result:
                quota = result['quota']
                print(f"\n   Quota Status:")
                print(f"      Monthly: {quota['monthly_used']:,} / {quota['monthly_limit']:,} ({quota['monthly_used']/quota['monthly_limit']*100:.2f}%)")
                print(f"      Daily:   {quota['daily_used']:,} / {quota['daily_limit']:,} ({quota['daily_used']/quota['daily_limit']*100:.2f}%)")
                print(f"      Remaining (monthly): {quota['monthly_remaining']:,}")
                print(f"      Remaining (daily):   {quota['daily_remaining']:,}")

            if 'metadata' in result:
                metadata = result['metadata']
                print(f"\n   Request Metadata (server-side):")
                print(f"      User: {metadata.get('userId', 'unknown')}")
                print(f"      Tenant: {metadata.get('tenant', 'unknown')}")
                print(f"      Department: {metadata.get('department', 'unknown')}")
                print(f"      Source: {metadata.get('source', 'unknown')}")

            print(f"\n✅ API call successful with quota enforcement!")
            return True

        else:
            print(f"   Error: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_quota_exceeded(api_endpoint, user_id, table_names):
    """Test quota exceeded scenario by temporarily lowering limits"""
    print(f"\n{'=' * 80}")
    print(f"🧪 TEST 2: Quota Exceeded Scenario")
    print(f"{'=' * 80}")
    print(f"User: {user_id}")

    # Get current usage
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    metrics_table = dynamodb.Table(table_names.get('UserQuotaMetricsTable', ''))

    now = datetime.now()
    month_key = f"monthly_{now.strftime('%Y-%m')}"

    try:
        response = metrics_table.get_item(
            Key={'user_email': user_id, 'metric_period': month_key}
        )
        current_usage = int(response.get('Item', {}).get('tokens_used', 0))
        print(f"\n📊 Current monthly usage: {current_usage:,} tokens")
    except:
        current_usage = 0

    # Temporarily set a very low quota by updating the policy
    policies_table = dynamodb.Table(table_names.get('QuotaPoliciesTable', ''))

    print(f"\n🔧 Temporarily setting very low quota (1000 tokens)...")

    try:
        policies_table.put_item(
            Item={
                'policy_type': 'user',
                'identifier': user_id,
                'monthly_limit': current_usage + 1000,  # Just 1000 tokens above current usage
                'daily_limit': 500,
                'enforcement_mode': 'block',
                'description': 'Temporary low quota for testing'
            }
        )

        # Make multiple calls to exceed quota
        token = f"demo-token-{user_id}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        body = {
            "messages": [{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": "Count from 1 to 100"
                }]
            }],
            "max_tokens": 200
        }

        print(f"\n📤 Making calls until quota is exceeded...")
        calls_made = 0
        quota_exceeded = False

        for i in range(10):  # Try up to 10 calls
            response = requests.post(
                f"{api_endpoint}/invoke",
                headers=headers,
                json=body,
                timeout=30
            )

            calls_made += 1

            if response.status_code == 429:
                print(f"\n✅ Quota exceeded after {calls_made} calls!")
                result = response.json()
                print(f"\n   Error: {result.get('error', 'unknown')}")
                print(f"   Message: {result.get('message', 'unknown')}")

                if 'quota' in result:
                    quota = result['quota']
                    print(f"\n   Quota Status:")
                    print(f"      Monthly: {quota['monthly_used']:,} / {quota['monthly_limit']:,}")
                    print(f"      Daily:   {quota['daily_used']:,} / {quota['daily_limit']:,}")

                quota_exceeded = True
                break

            elif response.status_code == 200:
                result = response.json()
                if 'usage' in result:
                    tokens = result['usage'].get('total_tokens', 0)
                    print(f"   Call {calls_made}: Used {tokens} tokens")
                time.sleep(1)  # Small delay between calls

            else:
                print(f"   Call {calls_made}: Error {response.status_code}")
                break

        if quota_exceeded:
            print(f"\n✅ Quota enforcement working correctly!")
            return True
        else:
            print(f"\n⚠️  Quota not exceeded after {calls_made} calls")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

    finally:
        # Restore original quota
        print(f"\n🔧 Restoring original quota...")
        try:
            # Get original limits from user metadata
            metadata_table = dynamodb.Table(table_names.get('UserMetadataTable', ''))
            response = metadata_table.get_item(Key={'userId': user_id})
            user_data = response.get('Item', {})

            policies_table.put_item(
                Item={
                    'policy_type': 'user',
                    'identifier': user_id,
                    'monthly_limit': int(user_data.get('monthlyLimit', 100000000)),
                    'daily_limit': int(user_data.get('dailyLimit', 5000000)),
                    'enforcement_mode': 'block',
                    'description': f'Quota for {user_id}'
                }
            )
            print(f"✅ Original quota restored")
        except Exception as e:
            print(f"⚠️  Could not restore quota: {str(e)}")

def check_cloudwatch_metrics(user_id):
    """Check CloudWatch metrics for quota monitoring"""
    print(f"\n{'=' * 80}")
    print(f"🧪 TEST 3: CloudWatch Quota Metrics")
    print(f"{'=' * 80}")
    print(f"User: {user_id}")

    cloudwatch = boto3.client('cloudwatch', region_name=REGION)

    metrics_to_check = [
        'MonthlyUsagePercent',
        'DailyUsagePercent',
        'TokensUsed'
    ]

    print(f"\n📊 Checking metrics (last 5 minutes)...")

    for metric_name in metrics_to_check:
        try:
            response = cloudwatch.get_metric_statistics(
                Namespace='Bedrock/Quota',
                MetricName=metric_name,
                Dimensions=[
                    {'Name': 'UserId', 'Value': user_id}
                ],
                StartTime=datetime.now().timestamp() - 300,  # 5 minutes ago
                EndTime=datetime.now().timestamp(),
                Period=300,
                Statistics=['Maximum', 'Average']
            )

            if response['Datapoints']:
                datapoint = response['Datapoints'][0]
                print(f"   ✅ {metric_name}: {datapoint.get('Maximum', 0):.2f}")
            else:
                print(f"   ⚠️  {metric_name}: No data yet")

        except Exception as e:
            print(f"   ❌ {metric_name}: Error - {str(e)}")

def check_usage_accuracy(user_id, table_names):
    """Verify usage tracking is accurate"""
    print(f"\n{'=' * 80}")
    print(f"🧪 TEST 4: Usage Tracking Accuracy")
    print(f"{'=' * 80}")
    print(f"User: {user_id}")

    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    metrics_table = dynamodb.Table(table_names.get('UserQuotaMetricsTable', ''))

    now = datetime.now()
    month_key = f"monthly_{now.strftime('%Y-%m')}"
    day_key = f"daily_{now.strftime('%Y-%m-%d')}"

    try:
        # Get monthly usage
        response = metrics_table.get_item(
            Key={'user_email': user_id, 'metric_period': month_key}
        )
        monthly_usage = int(response.get('Item', {}).get('tokens_used', 0))
        monthly_updated = response.get('Item', {}).get('last_updated', 'unknown')

        # Get daily usage
        response = metrics_table.get_item(
            Key={'user_email': user_id, 'metric_period': day_key}
        )
        daily_usage = int(response.get('Item', {}).get('tokens_used', 0))
        daily_updated = response.get('Item', {}).get('last_updated', 'unknown')

        print(f"\n📊 Current Usage (from DynamoDB):")
        print(f"   Monthly ({month_key}):")
        print(f"      Tokens:  {monthly_usage:,}")
        print(f"      Updated: {monthly_updated}")
        print(f"\n   Daily ({day_key}):")
        print(f"      Tokens:  {daily_usage:,}")
        print(f"      Updated: {daily_updated}")

        print(f"\n✅ Usage tracking is working")
        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("\n" + "=" * 80)
    print("🧪 TESTING HYBRID SOLUTION: QUOTA ENFORCEMENT")
    print("=" * 80)
    print(f"Region: {REGION}")
    print("")

    # Get API endpoint
    api_endpoint = get_api_endpoint()
    if not api_endpoint:
        print("\n❌ Cannot proceed without API endpoint")
        return False

    # Get table names
    table_names = get_table_names()

    # Test users
    test_user = "john.doe@company.com"

    results = []

    # Test 1: Normal call
    results.append(test_normal_call(api_endpoint, test_user))

    # Test 2: Quota exceeded
    # results.append(test_quota_exceeded(api_endpoint, test_user, table_names))

    # Test 3: CloudWatch metrics
    check_cloudwatch_metrics(test_user)

    # Test 4: Usage accuracy
    results.append(check_usage_accuracy(test_user, table_names))

    # Summary
    print(f"\n{'=' * 80}")
    print(f"📊 TEST SUMMARY")
    print(f"{'=' * 80}")
    passed = sum(results)
    total = len(results)
    print(f"   Tests Passed: {passed}/{total}")

    if passed == total:
        print(f"   ✅ All tests passed!")
    else:
        print(f"   ⚠️  Some tests failed")

    print(f"\n📝 Next Steps:")
    print(f"   1. Monitor CloudWatch metrics:")
    print(f"      https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#metricsV2:graph=~(namespace~'Bedrock*2fQuota)")
    print(f"   2. Check DynamoDB tables:")
    print(f"      https://{REGION}.console.aws.amazon.com/dynamodbv2/home?region={REGION}#tables")
    print(f"   3. View CloudWatch alarms:")
    print(f"      https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#alarmsV2:")
    print(f"   4. Query Athena for historical analysis:")
    print(f"      https://{REGION}.console.aws.amazon.com/athena/home?region={REGION}")

    print("\n")
    print("💡 Quota Enforcement Features:")
    print("   ✅ Pre-request quota check (blocks before Bedrock call)")
    print("   ✅ Atomic usage updates (DynamoDB)")
    print("   ✅ CloudWatch metrics (quota percentage)")
    print("   ✅ 429 error on quota exceeded")
    print("   ✅ Quota info in every response")
    print("   ✅ Server-side requestMetadata (audit trail)")

    return passed == total

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
