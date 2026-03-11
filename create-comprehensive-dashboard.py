#!/usr/bin/env python3
"""
Create Comprehensive Multi-Tenant Bedrock Dashboard

Combines:
1. Application Inference Profile metrics (4 tenants)
2. CCWB User Quota monitoring (5 users)
3. Overall system health
4. Cost tracking
"""

import boto3
import json
from datetime import datetime

REGION = "us-west-2"
DASHBOARD_NAME = "Bedrock-Comprehensive-Monitoring"

# Tenants with Application Inference Profiles (from earlier deployment)
TENANTS = [
    {
        "name": "Tenant A (Marketing)",
        "profile_id": "p24qm5pye2qr",
        "color": "#1f77b4"
    },
    {
        "name": "Tenant B (Sales)",
        "profile_id": "3rg09c3irrs6",
        "color": "#ff7f0e"
    },
    {
        "name": "Tenant C (Engineering)",
        "profile_id": "iq5vx6jibn89",
        "color": "#2ca02c"
    },
    {
        "name": "Tenant D (Finance)",
        "profile_id": "f8a6a2e836bz",
        "color": "#d62728"
    }
]

# Users with CCWB quota monitoring
USERS = [
    {"email": "john.doe@company.com", "tenant": "tenant_a", "limit": 500000000, "color": "#1f77b4"},
    {"email": "jane.smith@company.com", "tenant": "tenant_a", "limit": 300000000, "color": "#ff7f0e"},
    {"email": "bob.wilson@company.com", "tenant": "tenant_b", "limit": 250000000, "color": "#2ca02c"},
    {"email": "alice.johnson@company.com", "tenant": "tenant_c", "limit": 400000000, "color": "#d62728"},
    {"email": "david.chen@company.com", "tenant": "tenant_d", "limit": 350000000, "color": "#9467bd"}
]

def create_header_widget():
    """Dashboard header"""
    header_md = f"""# 📊 Bedrock Comprehensive Multi-Tenant Monitoring
**Complete view: Tenants + Users + Quotas + Costs**

## System Overview
- **Tenants**: 4 (Marketing, Sales, Engineering, Finance)
- **Users**: 5 with quota enforcement
- **Profiles**: 4 Application Inference Profiles
- **Monitoring**: Real-time CloudWatch metrics

**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
    return {
        "type": "text",
        "x": 0, "y": 0, "width": 24, "height": 3,
        "properties": {"markdown": header_md}
    }

def create_tenant_invocations_widget():
    """Tenant invocation comparison"""
    metrics = []
    for tenant in TENANTS:
        metrics.append([
            "AWS/Bedrock", "Invocations",
            "ModelId", tenant["profile_id"],
            {"stat": "Sum", "label": tenant["name"].split("(")[0].strip(), "color": tenant["color"]}
        ])

    return {
        "type": "metric",
        "x": 0, "y": 3, "width": 12, "height": 6,
        "properties": {
            "metrics": metrics,
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "📞 Tenant API Invocations (Hourly)",
            "period": 3600,
            "stat": "Sum",
            "yAxis": {"left": {"label": "Count"}},
            "setPeriodToTimeRange": True
        }
    }

def create_tenant_tokens_widget():
    """Tenant token usage"""
    metrics = []
    for tenant in TENANTS:
        metrics.append([
            "AWS/Bedrock", "InputTokenCount",
            "ModelId", tenant["profile_id"],
            {"id": f"m1_{tenant['profile_id']}", "visible": False, "stat": "Sum"}
        ])
        metrics.append([
            "AWS/Bedrock", "OutputTokenCount",
            "ModelId", tenant["profile_id"],
            {"id": f"m2_{tenant['profile_id']}", "visible": False, "stat": "Sum"}
        ])
        metrics.append([
            {"expression": f"m1_{tenant['profile_id']} + m2_{tenant['profile_id']}",
             "label": tenant["name"].split("(")[0].strip(),
             "id": f"total_{tenant['profile_id']}",
             "color": tenant["color"]}
        ])

    return {
        "type": "metric",
        "x": 12, "y": 3, "width": 12, "height": 6,
        "properties": {
            "metrics": metrics,
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "💬 Tenant Token Usage (Hourly)",
            "period": 3600,
            "stat": "Sum",
            "yAxis": {"left": {"label": "Tokens"}},
            "setPeriodToTimeRange": True
        }
    }

def create_user_quota_gauges():
    """User quota gauges"""
    widgets = []
    col_width = 24 // 5  # ~4 each

    for i, user in enumerate(USERS):
        # Try both CCWB namespace and potential custom namespace
        widgets.append({
            "type": "metric",
            "x": i * col_width, "y": 9, "width": col_width, "height": 6,
            "properties": {
                "metrics": [
                    ["CCWB/UserQuota", "MonthlyUsagePercent",
                     {"stat": "Maximum", "label": user["email"].split("@")[0], "color": user["color"]}]
                ],
                "view": "gauge",
                "region": REGION,
                "title": f"{user['email'].split('@')[0]} Quota %",
                "period": 300,
                "yAxis": {"left": {"min": 0, "max": 100}},
                "annotations": {
                    "horizontal": [
                        {"color": "#2ca02c", "label": "OK", "value": 0, "fill": "below"},
                        {"color": "#ff9900", "label": "Warning", "value": 80},
                        {"color": "#d13212", "label": "Critical", "value": 95}
                    ]
                },
                "setPeriodToTimeRange": False
            }
        })

    return widgets

def create_tenant_comparison_bar():
    """Bar chart comparing tenants"""
    metrics = []
    for tenant in TENANTS:
        metrics.append([
            "AWS/Bedrock", "Invocations",
            "ModelId", tenant["profile_id"],
            {"stat": "Sum", "label": tenant["name"].split("(")[0].strip(), "color": tenant["color"]}
        ])

    return {
        "type": "metric",
        "x": 0, "y": 15, "width": 12, "height": 6,
        "properties": {
            "metrics": metrics,
            "view": "bar",
            "region": REGION,
            "title": "📊 Tenant Comparison (Last 24h)",
            "period": 86400,
            "stat": "Sum",
            "yAxis": {"left": {"label": "Invocations"}},
            "setPeriodToTimeRange": False
        }
    }

def create_cost_estimate_widget():
    """Estimated cost by tenant"""
    cost_md = """## 💰 Estimated Costs (Last 24h)

Based on Claude 3.5 Sonnet pricing:
- Input: $3.00 / MTok
- Output: $15.00 / MTok

### Cost Formula
```
Cost = (InputTokens × $3 + OutputTokens × $15) / 1,000,000
```

### View Real Costs
Use AWS Cost Explorer with tags:
- `tenant=tenant_a`
- `tenant=tenant_b`
- `tenant=tenant_c`
- `tenant=tenant_d`

### Per-User Attribution
Query DynamoDB `UserQuotaMetrics` table or use Athena for detailed per-user cost breakdowns.
"""
    return {
        "type": "text",
        "x": 12, "y": 15, "width": 12, "height": 6,
        "properties": {"markdown": cost_md}
    }

def create_latency_widget():
    """Invocation latency by tenant"""
    metrics = []
    for tenant in TENANTS:
        metrics.append([
            "AWS/Bedrock", "InvocationLatency",
            "ModelId", tenant["profile_id"],
            {"stat": "Average", "label": f"{tenant['name'].split('(')[0].strip()} Avg", "color": tenant["color"]}
        ])
        metrics.append([
            "...",
            {"stat": "p99", "label": f"{tenant['name'].split('(')[0].strip()} P99", "color": tenant["color"]}
        ])

    return {
        "type": "metric",
        "x": 0, "y": 21, "width": 12, "height": 6,
        "properties": {
            "metrics": metrics,
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "⚡ Invocation Latency (ms)",
            "period": 300,
            "yAxis": {"left": {"label": "Milliseconds"}},
            "setPeriodToTimeRange": True
        }
    }

def create_error_rate_widget():
    """Error rates by tenant"""
    metrics = []
    for tenant in TENANTS:
        metrics.append([
            "AWS/Bedrock", "ModelErrors",
            "ModelId", tenant["profile_id"],
            {"stat": "Sum", "label": tenant["name"].split("(")[0].strip(), "color": tenant["color"]}
        ])

    return {
        "type": "metric",
        "x": 12, "y": 21, "width": 12, "height": 6,
        "properties": {
            "metrics": metrics,
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "❌ Model Errors",
            "period": 300,
            "stat": "Sum",
            "yAxis": {"left": {"label": "Count"}},
            "setPeriodToTimeRange": True
        }
    }

def create_token_pie_widget():
    """Token distribution pie chart"""
    metrics = []
    for tenant in TENANTS:
        metrics.append([
            "AWS/Bedrock", "InputTokenCount",
            "ModelId", tenant["profile_id"],
            {"id": f"in_{tenant['profile_id']}", "visible": False, "stat": "Sum"}
        ])
        metrics.append([
            "AWS/Bedrock", "OutputTokenCount",
            "ModelId", tenant["profile_id"],
            {"id": f"out_{tenant['profile_id']}", "visible": False, "stat": "Sum"}
        ])
        metrics.append([
            {"expression": f"in_{tenant['profile_id']} + out_{tenant['profile_id']}",
             "label": tenant["name"].split("(")[0].strip(),
             "id": f"t_{tenant['profile_id']}",
             "color": tenant["color"]}
        ])

    return {
        "type": "metric",
        "x": 0, "y": 27, "width": 12, "height": 6,
        "properties": {
            "metrics": metrics,
            "view": "pie",
            "region": REGION,
            "title": "🥧 Token Distribution (Last 24h)",
            "period": 86400,
            "stat": "Sum",
            "setPeriodToTimeRange": False
        }
    }

def create_system_health_widget():
    """System health summary"""
    health_md = """## 🏥 System Health

### ✅ Active Components
- **Application Inference Profiles**: 4
- **User Quota Policies**: 5
- **DynamoDB Tables**: 3
- **CloudWatch Dashboards**: 4 (including this one)

### 📊 Monitoring Layers
1. **Tenant Level** (AIPs)
   - CloudWatch metrics by profile ID
   - Cost allocation via tags

2. **User Level** (CCWB)
   - Quota enforcement via Lambda
   - DynamoDB usage tracking
   - Real-time alerts

3. **Audit Trail**
   - CloudWatch Logs
   - S3 invocation logs
   - Athena queries

### 🔗 Quick Links
- [Cost Explorer](https://console.aws.amazon.com/cost-management/home#/dashboard)
- [DynamoDB Tables](https://us-west-2.console.aws.amazon.com/dynamodbv2/home?region=us-west-2#tables)
- [CloudWatch Logs](https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#logsV2:log-groups)
"""
    return {
        "type": "text",
        "x": 12, "y": 27, "width": 12, "height": 6,
        "properties": {"markdown": health_md}
    }

def build_dashboard():
    """Build complete dashboard"""
    widgets = []

    # Header
    widgets.append(create_header_widget())

    # Row 1: Tenant metrics
    widgets.append(create_tenant_invocations_widget())
    widgets.append(create_tenant_tokens_widget())

    # Row 2: User quota gauges
    widgets.extend(create_user_quota_gauges())

    # Row 3: Comparisons
    widgets.append(create_tenant_comparison_bar())
    widgets.append(create_cost_estimate_widget())

    # Row 4: Performance
    widgets.append(create_latency_widget())
    widgets.append(create_error_rate_widget())

    # Row 5: Distribution & Health
    widgets.append(create_token_pie_widget())
    widgets.append(create_system_health_widget())

    return widgets

def main():
    print("\n" + "=" * 80)
    print("📊 CREATING COMPREHENSIVE BEDROCK DASHBOARD")
    print("=" * 80)

    cloudwatch = boto3.client('cloudwatch', region_name=REGION)

    widgets = build_dashboard()
    dashboard_body = json.dumps({"widgets": widgets})

    print(f"\n   Region: {REGION}")
    print(f"   Dashboard: {DASHBOARD_NAME}")
    print(f"   Tenants: {len(TENANTS)}")
    print(f"   Users: {len(USERS)}")
    print(f"   Widgets: {len(widgets)}")

    try:
        cloudwatch.put_dashboard(
            DashboardName=DASHBOARD_NAME,
            DashboardBody=dashboard_body
        )

        console_url = (
            f"https://{REGION}.console.aws.amazon.com/cloudwatch/home"
            f"?region={REGION}#dashboards/dashboard/{DASHBOARD_NAME}"
        )

        print(f"\n✅ Dashboard created successfully!")
        print(f"\n🔗 View at:")
        print(f"   {console_url}")

        print(f"\n📊 Dashboard Sections:")
        print(f"   • Header: System overview")
        print(f"   • Row 1: Tenant invocations & tokens (4 tenants)")
        print(f"   • Row 2: User quota gauges (5 users)")
        print(f"   • Row 3: Tenant comparison & cost estimates")
        print(f"   • Row 4: Latency & error rates")
        print(f"   • Row 5: Token distribution & system health")

        print(f"\n📈 Metrics Tracked:")
        print(f"   • API invocations by tenant")
        print(f"   • Token usage (input/output)")
        print(f"   • User quota percentages")
        print(f"   • Invocation latency (avg/p99)")
        print(f"   • Error rates")
        print(f"   • Cost estimates")

        return True

    except Exception as e:
        print(f"\n❌ Error creating dashboard: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
