#!/usr/bin/env python3
"""
Generate Real Test Traffic to Populate Dashboard

Makes actual Bedrock API calls through Application Inference Profiles
to generate real metrics in CloudWatch
"""

import boto3
import json
import time
from datetime import datetime

REGION = "us-west-2"

# Your actual Application Inference Profiles
TENANTS = [
    {
        "name": "Tenant A (Marketing)",
        "profile_arn": "arn:aws:bedrock:us-west-2:477205238526:application-inference-profile/p24qm5pye2qr",
        "prompts": [
            "Write a catchy tagline for a new product",
            "Generate 3 social media post ideas",
            "Create an email subject line"
        ]
    },
    {
        "name": "Tenant B (Sales)",
        "profile_arn": "arn:aws:bedrock:us-west-2:477205238526:application-inference-profile/3rg09c3irrs6",
        "prompts": [
            "Draft a follow-up email after a sales call",
            "Create an elevator pitch",
            "Write qualifying questions for prospects"
        ]
    },
    {
        "name": "Tenant C (Engineering)",
        "profile_arn": "arn:aws:bedrock:us-west-2:477205238526:application-inference-profile/iq5vx6jibn89",
        "prompts": [
            "Explain microservices architecture benefits",
            "Write a code review comment",
            "Draft API documentation"
        ]
    },
    {
        "name": "Tenant D (Finance)",
        "profile_arn": "arn:aws:bedrock:us-west-2:477205238526:application-inference-profile/f8a6a2e836bz",
        "prompts": [
            "Explain P&L statement basics",
            "Draft a monthly financial summary",
            "Write key metrics for Q1 performance"
        ]
    }
]

def generate_metrics():
    """Generate real metrics by making actual Bedrock API calls"""
    bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)

    print("\n" + "=" * 80)
    print("🔥 GENERATING REAL TEST TRAFFIC")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Region: {REGION}")
    print("")

    total_calls = 0
    total_tokens = 0

    for tenant in TENANTS:
        print(f"\n📊 {tenant['name']}")
        print("-" * 60)

        for i, prompt in enumerate(tenant['prompts'], 1):
            try:
                print(f"   Call {i}: '{prompt[:40]}...'", end=" ", flush=True)

                body = json.dumps({
                    "messages": [{
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}]
                    }],
                    "max_tokens": 100,
                    "anthropic_version": "bedrock-2023-05-31"
                })

                response = bedrock_runtime.invoke_model(
                    modelId=tenant['profile_arn'],
                    body=body
                )

                response_body = json.loads(response['body'].read())
                usage = response_body.get('usage', {})
                tokens = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)

                total_calls += 1
                total_tokens += tokens

                print(f"✅ {tokens} tokens")

                time.sleep(1)  # Small delay to avoid throttling

            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")

    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    print(f"   Total API Calls: {total_calls}")
    print(f"   Total Tokens: {total_tokens:,}")
    print(f"   Avg Tokens/Call: {total_tokens // total_calls if total_calls > 0 else 0}")

    print("\n✅ Real metrics generated!")
    print("\n📊 These metrics will appear in your dashboard within 1-3 minutes:")
    print("   https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards/dashboard/Bedrock-Comprehensive-Monitoring")
    print("\n⏱️  Refresh your dashboard in a few minutes to see the data")

if __name__ == "__main__":
    generate_metrics()
