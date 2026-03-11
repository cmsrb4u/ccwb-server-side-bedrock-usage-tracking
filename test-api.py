#!/usr/bin/env python3
"""
Test the Bedrock API Gateway with JWT authentication
"""

import boto3
import json
import requests
from datetime import datetime

REGION = "us-west-2"

def get_api_endpoint():
    """Get API Gateway endpoint from stack outputs"""
    try:
        with open('stack-outputs.json', 'r') as f:
            outputs = json.load(f)
            for output in outputs:
                if output['OutputKey'] == 'ApiEndpoint':
                    return output['OutputValue']
        print("❌ ApiEndpoint not found in stack outputs")
        return None
    except FileNotFoundError:
        print("❌ stack-outputs.json not found. Run deploy.sh first.")
        return None

def test_invoke_bedrock(api_endpoint, user_id):
    """Test Bedrock invocation through API Gateway"""
    print(f"\n{'=' * 80}")
    print(f"🧪 TESTING BEDROCK API FOR USER: {user_id}")
    print(f"{'=' * 80}")

    # Demo JWT token (format: Bearer demo-token-{userId})
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
                "text": "Write a haiku about server-side tracking"
            }]
        }],
        "max_tokens": 100,
        "anthropic_version": "bedrock-2023-05-31"
    }

    print(f"\n📤 Request:")
    print(f"   Endpoint: {api_endpoint}/invoke")
    print(f"   User: {user_id}")
    print(f"   Token: {token}")
    print(f"   Model: us.anthropic.claude-3-5-sonnet-20241022-v2:0")

    try:
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

            # Extract response
            if 'content' in result:
                text = result['content'][0]['text']
                print(f"   Text: {text[:100]}...")

            # Extract metadata
            if 'usage' in result:
                usage = result['usage']
                print(f"   Input Tokens: {usage.get('input_tokens', 0)}")
                print(f"   Output Tokens: {usage.get('output_tokens', 0)}")
                print(f"   Total Tokens: {usage.get('input_tokens', 0) + usage.get('output_tokens', 0)}")

            print(f"\n✅ API call successful!")
            print(f"   requestMetadata was set server-side for user: {user_id}")
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

def verify_cloudwatch_logs():
    """Verify logs are being written to CloudWatch"""
    print(f"\n{'=' * 80}")
    print(f"🔍 VERIFYING CLOUDWATCH LOGS")
    print(f"{'=' * 80}")

    logs = boto3.client('logs', region_name=REGION)

    log_groups = [
        '/aws/bedrock/modelinvocations',
        '/aws/lambda/BedrockProxyFunction',
        '/aws/lambda/JWTAuthorizerFunction'
    ]

    for log_group in log_groups:
        try:
            response = logs.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )

            if response['logStreams']:
                last_event = response['logStreams'][0].get('lastEventTime', 0)
                last_event_time = datetime.fromtimestamp(last_event / 1000)
                print(f"✅ {log_group}")
                print(f"   Last event: {last_event_time}")
            else:
                print(f"⚠️  {log_group} (no streams yet)")

        except logs.exceptions.ResourceNotFoundException:
            print(f"⚠️  {log_group} (not created yet)")
        except Exception as e:
            print(f"❌ {log_group}: {str(e)}")

def check_s3_logs(bucket_name):
    """Check if logs are being written to S3"""
    print(f"\n{'=' * 80}")
    print(f"📦 CHECKING S3 LOGS")
    print(f"{'=' * 80}")

    s3 = boto3.client('s3', region_name=REGION)

    try:
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix='invocations/',
            MaxKeys=10
        )

        if 'Contents' in response:
            print(f"✅ Found {len(response['Contents'])} log files in S3")
            for obj in response['Contents'][:5]:
                print(f"   • {obj['Key']} ({obj['Size']} bytes)")
        else:
            print(f"⚠️  No log files found yet (this is normal if you just deployed)")
            print(f"   Logs are written after Bedrock invocations")

    except s3.exceptions.NoSuchBucket:
        print(f"❌ Bucket not found: {bucket_name}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def check_glue_tables(database_name):
    """Check if Glue crawler has created tables"""
    print(f"\n{'=' * 80}")
    print(f"🗄️  CHECKING GLUE TABLES")
    print(f"{'=' * 80}")

    glue = boto3.client('glue', region_name=REGION)

    try:
        response = glue.get_tables(DatabaseName=database_name)

        if response['TableList']:
            print(f"✅ Found {len(response['TableList'])} tables:")
            for table in response['TableList']:
                print(f"   • {table['Name']} ({table.get('StorageDescriptor', {}).get('Location', 'unknown location')})")
        else:
            print(f"⚠️  No tables found yet")
            print(f"   Run the Glue crawler first: post-deploy.py")

    except glue.exceptions.EntityNotFoundException:
        print(f"❌ Database not found: {database_name}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    print("\n" + "=" * 80)
    print("🧪 TESTING BEDROCK SERVER-SIDE LOGGING")
    print("=" * 80)
    print(f"Region: {REGION}")
    print("")

    # Get API endpoint
    api_endpoint = get_api_endpoint()
    if not api_endpoint:
        print("\n❌ Cannot proceed without API endpoint")
        return False

    # Get stack outputs
    try:
        with open('stack-outputs.json', 'r') as f:
            outputs = json.load(f)
            outputs_dict = {o['OutputKey']: o['OutputValue'] for o in outputs}
    except:
        outputs_dict = {}

    # Test API calls for different users
    test_users = [
        "john.doe@company.com",
        "alice.johnson@company.com"
    ]

    success_count = 0
    for user in test_users:
        if test_invoke_bedrock(api_endpoint, user):
            success_count += 1

    # Verify CloudWatch logs
    verify_cloudwatch_logs()

    # Check S3 logs
    if 'InvocationLogsBucket' in outputs_dict:
        check_s3_logs(outputs_dict['InvocationLogsBucket'])

    # Check Glue tables
    if 'GlueDatabaseName' in outputs_dict:
        check_glue_tables(outputs_dict['GlueDatabaseName'])

    # Summary
    print(f"\n{'=' * 80}")
    print(f"📊 TEST SUMMARY")
    print(f"{'=' * 80}")
    print(f"   API Tests: {success_count}/{len(test_users)} passed")

    print(f"\n📝 Next Steps:")
    print(f"   1. Check CloudWatch Logs for requestMetadata in invocation logs")
    print(f"   2. Wait 5-10 minutes for logs to appear in S3")
    print(f"   3. Run Glue crawler to create tables")
    print(f"   4. Query logs using Athena (see athena-queries.sql)")

    print(f"\n🔗 Useful Links:")
    if api_endpoint:
        print(f"   API Gateway: {api_endpoint}")
    print(f"   CloudWatch Logs: https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#logsV2:log-groups")
    if 'InvocationLogsBucket' in outputs_dict:
        print(f"   S3 Bucket: https://s3.console.aws.amazon.com/s3/buckets/{outputs_dict['InvocationLogsBucket']}?region={REGION}")

    return success_count == len(test_users)

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
