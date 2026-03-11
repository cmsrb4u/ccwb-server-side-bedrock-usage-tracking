#!/usr/bin/env python3
"""
Post-Deployment Configuration

1. Enable Bedrock model invocation logging
2. Seed user metadata in DynamoDB
3. Verify Glue crawler configuration
4. Test Athena queries
"""

import boto3
import json
import sys
from datetime import datetime

REGION = "us-west-2"
STACK_NAME = "bedrock-serverside-logging"

# Sample user metadata
USERS = [
    {
        "userId": "john.doe@company.com",
        "group": "engineering",
        "tenant": "tenant_a",
        "department": "platform",
        "monthlyLimit": 500000000,
        "dailyLimit": 20000000
    },
    {
        "userId": "jane.smith@company.com",
        "group": "data-science",
        "tenant": "tenant_a",
        "department": "ml-ops",
        "monthlyLimit": 300000000,
        "dailyLimit": 12000000
    },
    {
        "userId": "bob.wilson@company.com",
        "group": "sales",
        "tenant": "tenant_b",
        "department": "sales-ops",
        "monthlyLimit": 250000000,
        "dailyLimit": 10000000
    },
    {
        "userId": "alice.johnson@company.com",
        "group": "engineering",
        "tenant": "tenant_c",
        "department": "devops",
        "monthlyLimit": 400000000,
        "dailyLimit": 15000000
    },
    {
        "userId": "david.chen@company.com",
        "group": "finance",
        "tenant": "tenant_d",
        "department": "analytics",
        "monthlyLimit": 350000000,
        "dailyLimit": 12000000
    }
]

def get_stack_outputs():
    """Get CloudFormation stack outputs"""
    try:
        with open('stack-outputs.json', 'r') as f:
            outputs = json.load(f)
            return {o['OutputKey']: o['OutputValue'] for o in outputs}
    except FileNotFoundError:
        print("❌ stack-outputs.json not found. Run deploy.sh first.")
        sys.exit(1)

def enable_bedrock_logging(log_group_arn, s3_bucket_arn, kms_key_id):
    """Enable Bedrock model invocation logging"""
    print("\n" + "=" * 80)
    print("📝 ENABLING BEDROCK MODEL INVOCATION LOGGING")
    print("=" * 80)

    bedrock = boto3.client('bedrock', region_name=REGION)

    logging_config = {
        "cloudWatchConfig": {
            "logGroupName": log_group_arn.split(':')[-1],
            "roleArn": log_group_arn.replace(':log-group:', ':role/'),  # Simplified
            "largeDataDeliveryS3Config": {
                "bucketName": s3_bucket_arn.split(':::')[-1],
                "keyPrefix": "large-payloads/"
            }
        },
        "s3Config": {
            "bucketName": s3_bucket_arn.split(':::')[-1],
            "keyPrefix": "invocations/"
        },
        "textDataDeliveryEnabled": True,
        "imageDataDeliveryEnabled": True,
        "embeddingDataDeliveryEnabled": True
    }

    try:
        response = bedrock.put_model_invocation_logging_configuration(
            loggingConfig=logging_config
        )
        print(f"✅ Bedrock logging enabled")
        print(f"   CloudWatch: {log_group_arn}")
        print(f"   S3: {s3_bucket_arn}")
    except Exception as e:
        print(f"⚠️  Could not enable logging automatically: {str(e)}")
        print(f"   You may need to enable it manually in the AWS Console")
        print(f"   Go to: Bedrock Console → Settings → Model invocation logging")

def seed_user_metadata(table_name):
    """Seed user metadata in DynamoDB"""
    print("\n" + "=" * 80)
    print("📊 SEEDING USER METADATA IN DYNAMODB")
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
                    'createdAt': datetime.now().isoformat(),
                    'updatedAt': datetime.now().isoformat(),
                    'status': 'active'
                }
            )
            print(f"✅ {user['userId']:<30} → {user['tenant']} / {user['department']}")
        except Exception as e:
            print(f"❌ {user['userId']}: {str(e)}")

    print(f"\n📈 Total users seeded: {len(USERS)}")

def verify_glue_crawler(crawler_name):
    """Verify Glue crawler configuration"""
    print("\n" + "=" * 80)
    print("🔍 VERIFYING GLUE CRAWLER CONFIGURATION")
    print("=" * 80)

    glue = boto3.client('glue', region_name=REGION)

    try:
        response = glue.get_crawler(Name=crawler_name)
        crawler = response['Crawler']

        print(f"✅ Crawler: {crawler_name}")
        print(f"   Status: {crawler['State']}")
        print(f"   Schedule: {crawler.get('Schedule', 'Not scheduled')}")
        print(f"   Database: {crawler['DatabaseName']}")

        # Start crawler for initial run
        print(f"\n🚀 Starting initial crawler run...")
        try:
            glue.start_crawler(Name=crawler_name)
            print(f"✅ Crawler started. This will take a few minutes.")
            print(f"   Monitor in AWS Console: Glue → Crawlers → {crawler_name}")
        except glue.exceptions.CrawlerRunningException:
            print(f"⚠️  Crawler is already running")

    except Exception as e:
        print(f"❌ Error verifying crawler: {str(e)}")

def test_athena_setup(workgroup_name, database_name):
    """Test Athena setup"""
    print("\n" + "=" * 80)
    print("🔬 TESTING ATHENA SETUP")
    print("=" * 80)

    athena = boto3.client('athena', region_name=REGION)

    # Simple query to test
    query = f"SHOW TABLES IN {database_name};"

    try:
        response = athena.start_query_execution(
            QueryString=query,
            WorkGroup=workgroup_name
        )

        query_execution_id = response['QueryExecutionId']
        print(f"✅ Athena workgroup: {workgroup_name}")
        print(f"   Database: {database_name}")
        print(f"   Test query submitted: {query_execution_id}")
        print(f"\n   Note: Run the Glue crawler first to create tables")

    except Exception as e:
        print(f"❌ Error testing Athena: {str(e)}")

def print_summary(outputs):
    """Print deployment summary"""
    print("\n" + "=" * 80)
    print("🎉 POST-DEPLOYMENT CONFIGURATION COMPLETE")
    print("=" * 80)

    print("\n📊 Stack Resources:")
    for key, value in outputs.items():
        print(f"   {key}: {value}")

    print("\n📝 Next Steps:")
    print("   1. Wait 5-10 minutes for Glue crawler to complete")
    print("   2. Verify tables in Athena:")
    print(f"      https://console.aws.amazon.com/athena/home?region={REGION}")
    print("   3. Test the API:")
    print("      python3 test-api.py")
    print("   4. Run sample queries:")
    print("      athena-queries.sql")

    print("\n🔗 Useful Links:")
    print(f"   CloudWatch Logs: https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#logsV2:log-groups")
    print(f"   Glue Crawlers: https://{REGION}.console.aws.amazon.com/glue/home?region={REGION}#catalog:tab=crawlers")
    print(f"   Athena: https://{REGION}.console.aws.amazon.com/athena/home?region={REGION}")
    print(f"   S3 Bucket: https://s3.console.aws.amazon.com/s3/buckets/{outputs.get('InvocationLogsBucket', '')}?region={REGION}")

def main():
    print("\n" + "=" * 80)
    print("🚀 POST-DEPLOYMENT CONFIGURATION")
    print("=" * 80)
    print(f"Region: {REGION}")
    print(f"Stack: {STACK_NAME}")
    print("")

    # Get stack outputs
    outputs = get_stack_outputs()

    # Enable Bedrock logging
    if 'BedrockLogGroupArn' in outputs and 'InvocationLogsBucket' in outputs:
        enable_bedrock_logging(
            outputs['BedrockLogGroupArn'],
            f"arn:aws:s3:::{outputs['InvocationLogsBucket']}",
            outputs.get('KMSKeyId', '')
        )

    # Seed user metadata
    if 'UserMetadataTable' in outputs:
        seed_user_metadata(outputs['UserMetadataTable'])

    # Verify Glue crawler
    if 'GlueCrawlerName' in outputs:
        verify_glue_crawler(outputs['GlueCrawlerName'])

    # Test Athena
    if 'AthenaWorkgroup' in outputs and 'GlueDatabaseName' in outputs:
        test_athena_setup(outputs['AthenaWorkgroup'], outputs['GlueDatabaseName'])

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
