#!/usr/bin/env python3
"""
Create Comprehensive CloudWatch Dashboard for Hybrid Solution

Visualizes:
1. Quota usage by user (monthly/daily)
2. Token consumption trends
3. API call rates
4. Quota exceeded errors
5. Lambda performance
6. User comparison charts
"""

import boto3
import json
from datetime import datetime

REGION = "us-west-2"
DASHBOARD_NAME = "Bedrock-Hybrid-Quota-Monitoring"

# Sample users (update based on actual deployment)
USERS = [
    {
        "userId": "john.doe@company.com",
        "tenant": "tenant_a",
        "color": "#1f77b4",
        "monthlyLimit": 500000000
    },
    {
        "userId": "jane.smith@company.com",
        "tenant": "tenant_a",
        "color": "#ff7f0e",
        "monthlyLimit": 300000000
    },
    {
        "userId": "bob.wilson@company.com",
        "tenant": "tenant_b",
        "color": "#2ca02c",
        "monthlyLimit": 250000000
    },
    {
        "userId": "alice.johnson@company.com",
        "tenant": "tenant_c",
        "color": "#d62728",
        "monthlyLimit": 400000000
    },
    {
        "userId": "david.chen@company.com",
        "tenant": "tenant_d",
        "color": "#9467bd",
        "monthlyLimit": 350000000
    }
]

def create_header_widget():
    """Create dashboard header"""
    header_md = f"""# 📊 Bedrock Hybrid Quota Monitoring Dashboard
**Real-time quota enforcement + Server-side tracking**

| Feature | Status |
|---------|--------|
| Quota Enforcement | ✅ Real-time pre-request blocking |
| Identity Validation | ✅ JWT + API Gateway |
| Usage Tracking | ✅ DynamoDB atomic updates |
| Audit Trail | ✅ CloudWatch → S3 → Athena |

**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

    return {
        "type": "text",
        "x": 0, "y": 0, "width": 24, "height": 3,
        "properties": {"markdown": header_md}
    }

def create_quota_gauge_widget(user, x, y, width=4, height=6):
    """Create quota percentage gauge for a user"""
    return {
        "type": "metric",
        "x": x, "y": y, "width": width, "height": height,
        "properties": {
            "metrics": [
                ["Bedrock/Quota", "MonthlyUsagePercent",
                 {"stat": "Maximum", "label": f"{user['userId'].split('@')[0]}", "color": user['color']}]
            ],
            "view": "gauge",
            "region": REGION,
            "title": f"{user['userId'].split('@')[0]} - Monthly Quota",
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
    }

def create_quota_sparkline_widget(user, x, y, width=4, height=4):
    """Create sparkline showing quota usage over time"""
    return {
        "type": "metric",
        "x": x, "y": y, "width": width, "height": height,
        "properties": {
            "metrics": [
                ["Bedrock/Quota", "MonthlyUsagePercent",
                 {"stat": "Maximum", "label": f"{user['userId'].split('@')[0]}", "color": user['color']}]
            ],
            "view": "singleValue",
            "region": REGION,
            "title": f"{user['userId'].split('@')[0]} - Usage %",
            "period": 300,
            "sparkline": True,
            "setPeriodToTimeRange": True
        }
    }

def create_tokens_used_widget():
    """Create widget showing total tokens used by all users"""
    metrics = []
    for i, user in enumerate(USERS):
        metrics.append([
            "Bedrock/Quota", "TokensUsed",
            "UserId", user['userId'],
            {"stat": "Sum", "label": user['userId'].split('@')[0], "color": user['color']}
        ])

    return {
        "type": "metric",
        "x": 0, "y": 13, "width": 12, "height": 6,
        "properties": {
            "metrics": metrics,
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "Token Usage by User (Hourly)",
            "period": 3600,
            "stat": "Sum",
            "yAxis": {"left": {"label": "Tokens"}},
            "setPeriodToTimeRange": True
        }
    }

def create_quota_percentage_trend_widget():
    """Create widget showing quota percentage trends"""
    metrics = []
    for user in USERS:
        metrics.append([
            "Bedrock/Quota", "MonthlyUsagePercent",
            "UserId", user['userId'],
            {"stat": "Maximum", "label": user['userId'].split('@')[0], "color": user['color']}
        ])

    return {
        "type": "metric",
        "x": 12, "y": 13, "width": 12, "height": 6,
        "properties": {
            "metrics": metrics,
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "Monthly Quota Usage % (Trend)",
            "period": 300,
            "stat": "Maximum",
            "yAxis": {"left": {"label": "Percentage", "min": 0, "max": 100}},
            "annotations": {
                "horizontal": [
                    {"label": "Warning", "value": 80, "color": "#ff9900"},
                    {"label": "Critical", "value": 95, "color": "#d13212"}
                ]
            },
            "setPeriodToTimeRange": True
        }
    }

def create_daily_quota_widget():
    """Create widget showing daily quota usage"""
    metrics = []
    for user in USERS:
        metrics.append([
            "Bedrock/Quota", "DailyUsagePercent",
            "UserId", user['userId'],
            {"stat": "Maximum", "label": user['userId'].split('@')[0], "color": user['color']}
        ])

    return {
        "type": "metric",
        "x": 0, "y": 19, "width": 12, "height": 6,
        "properties": {
            "metrics": metrics,
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "Daily Quota Usage %",
            "period": 300,
            "stat": "Maximum",
            "yAxis": {"left": {"label": "Percentage", "min": 0, "max": 100}},
            "annotations": {
                "horizontal": [
                    {"label": "Warning", "value": 80, "color": "#ff9900"}
                ]
            },
            "setPeriodToTimeRange": True
        }
    }

def create_api_calls_widget():
    """Create widget showing API call count"""
    return {
        "type": "metric",
        "x": 12, "y": 19, "width": 12, "height": 6,
        "properties": {
            "metrics": [
                ["AWS/Lambda", "Invocations",
                 {"stat": "Sum", "label": "Total API Calls"}]
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "API Gateway Invocations",
            "period": 300,
            "stat": "Sum",
            "yAxis": {"left": {"label": "Count"}},
            "setPeriodToTimeRange": True
        }
    }

def create_lambda_errors_widget(lambda_function_name):
    """Create widget showing Lambda errors"""
    return {
        "type": "metric",
        "x": 0, "y": 25, "width": 8, "height": 6,
        "properties": {
            "metrics": [
                ["AWS/Lambda", "Errors", "FunctionName", lambda_function_name,
                 {"stat": "Sum", "label": "Errors", "color": "#d13212"}],
                [".", "Throttles", ".", ".",
                 {"stat": "Sum", "label": "Throttles", "color": "#ff9900"}],
                [".", "Invocations", ".", ".",
                 {"stat": "Sum", "label": "Total Invocations", "color": "#1f77b4"}]
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "Lambda Function Health",
            "period": 300,
            "stat": "Sum",
            "yAxis": {"left": {"label": "Count"}},
            "setPeriodToTimeRange": True
        }
    }

def create_lambda_duration_widget(lambda_function_name):
    """Create widget showing Lambda duration"""
    return {
        "type": "metric",
        "x": 8, "y": 25, "width": 8, "height": 6,
        "properties": {
            "metrics": [
                ["AWS/Lambda", "Duration", "FunctionName", lambda_function_name,
                 {"stat": "Average", "label": "Avg Duration"}],
                ["...", {"stat": "Maximum", "label": "Max Duration"}],
                ["...", {"stat": "p99", "label": "P99 Duration"}]
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "Lambda Duration (ms)",
            "period": 300,
            "yAxis": {"left": {"label": "Milliseconds"}},
            "setPeriodToTimeRange": True
        }
    }

def create_lambda_concurrent_widget(lambda_function_name):
    """Create widget showing Lambda concurrency"""
    return {
        "type": "metric",
        "x": 16, "y": 25, "width": 8, "height": 6,
        "properties": {
            "metrics": [
                ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", lambda_function_name,
                 {"stat": "Maximum", "label": "Concurrent Executions"}]
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": REGION,
            "title": "Lambda Concurrency",
            "period": 60,
            "stat": "Maximum",
            "yAxis": {"left": {"label": "Count"}},
            "setPeriodToTimeRange": True
        }
    }

def create_user_comparison_bar_widget():
    """Create bar chart comparing users"""
    metrics = []
    for user in USERS:
        metrics.append([
            "Bedrock/Quota", "TokensUsed",
            "UserId", user['userId'],
            {"stat": "Sum", "label": user['userId'].split('@')[0], "color": user['color']}
        ])

    return {
        "type": "metric",
        "x": 0, "y": 31, "width": 12, "height": 6,
        "properties": {
            "metrics": metrics,
            "view": "bar",
            "region": REGION,
            "title": "Token Usage Comparison (Last 24 Hours)",
            "period": 86400,
            "stat": "Sum",
            "yAxis": {"left": {"label": "Tokens"}},
            "setPeriodToTimeRange": False
        }
    }

def create_quota_status_table():
    """Create table showing quota status"""
    table_md = """## 📋 Quota Status Summary

| User | Monthly Limit | Daily Limit | Status |
|------|---------------|-------------|--------|
"""
    for user in USERS:
        user_name = user['userId'].split('@')[0]
        monthly_limit = f"{user['monthlyLimit'] / 1000000:.0f}M"
        table_md += f"| {user_name} | {monthly_limit} | Varies | ✅ Active |\n"

    table_md += """
### 🎯 Enforcement Mode
- **Block Mode**: Requests blocked when quota exceeded (429 error)
- **Alert Mode**: Requests allowed but CloudWatch alarm triggered

### 📊 Metrics Refresh
- Real-time: Every 5 minutes
- DynamoDB: Atomic updates after each call
- CloudWatch Logs: 1-2 minutes
- S3 Logs: 5-10 minutes
"""

    return {
        "type": "text",
        "x": 12, "y": 31, "width": 12, "height": 6,
        "properties": {"markdown": table_md}
    }

def create_alarms_widget():
    """Create widget showing alarm status"""
    return {
        "type": "alarm",
        "x": 0, "y": 37, "width": 24, "height": 3,
        "properties": {
            "title": "Active Alarms",
            "alarms": [
                f"arn:aws:cloudwatch:{REGION}:{boto3.client('sts').get_caller_identity()['Account']}:alarm:bedrock-hybrid-tracking-high-quota-usage",
                f"arn:aws:cloudwatch:{REGION}:{boto3.client('sts').get_caller_identity()['Account']}:alarm:bedrock-hybrid-tracking-lambda-errors"
            ]
        }
    }

def build_dashboard(lambda_function_name):
    """Build complete dashboard structure"""
    widgets = []
    y = 0

    # Row 1: Header
    widgets.append(create_header_widget())
    y += 3

    # Row 2: Quota gauges (5 users × 4 width = 20, but we'll use 4 each with padding)
    col_width = 24 // 5  # 4.8 → 4
    for i, user in enumerate(USERS):
        widgets.append(create_quota_gauge_widget(user, x=i * col_width, y=y, width=col_width))
    y += 6

    # Row 3: Sparklines
    for i, user in enumerate(USERS):
        widgets.append(create_quota_sparkline_widget(user, x=i * col_width, y=y, width=col_width))
    y += 4

    # Row 4: Token usage trends
    widgets.append(create_tokens_used_widget())
    widgets.append(create_quota_percentage_trend_widget())
    y += 6

    # Row 5: Daily quota + API calls
    widgets.append(create_daily_quota_widget())
    widgets.append(create_api_calls_widget())
    y += 6

    # Row 6: Lambda performance
    widgets.append(create_lambda_errors_widget(lambda_function_name))
    widgets.append(create_lambda_duration_widget(lambda_function_name))
    widgets.append(create_lambda_concurrent_widget(lambda_function_name))
    y += 6

    # Row 7: User comparison + status table
    widgets.append(create_user_comparison_bar_widget())
    widgets.append(create_quota_status_table())
    y += 6

    # Row 8: Alarms
    try:
        widgets.append(create_alarms_widget())
    except:
        pass  # Alarms might not exist yet

    return widgets

def main():
    print("\n" + "=" * 80)
    print("📊 CREATING CLOUDWATCH DASHBOARD")
    print("=" * 80)

    # Get Lambda function name from stack outputs
    try:
        with open('stack-outputs-hybrid.json', 'r') as f:
            outputs = json.load(f)
            lambda_function_name = None
            for output in outputs:
                if 'Lambda' in output.get('OutputKey', '') or 'Function' in output.get('OutputKey', ''):
                    lambda_function_name = output.get('OutputValue', '').split(':')[-1]
                    break

            if not lambda_function_name:
                lambda_function_name = "bedrock-hybrid-tracking-bedrock-proxy"
                print(f"⚠️  Using default Lambda name: {lambda_function_name}")
    except:
        lambda_function_name = "bedrock-hybrid-tracking-bedrock-proxy"
        print(f"⚠️  Stack outputs not found, using default Lambda name: {lambda_function_name}")

    cloudwatch = boto3.client('cloudwatch', region_name=REGION)

    # Build dashboard
    widgets = build_dashboard(lambda_function_name)
    dashboard_body = json.dumps({"widgets": widgets})

    print(f"\n   Region: {REGION}")
    print(f"   Dashboard: {DASHBOARD_NAME}")
    print(f"   Users: {len(USERS)}")
    print(f"   Widgets: {len(widgets)}")
    print(f"   Lambda Function: {lambda_function_name}")

    try:
        # Create or update dashboard
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

        print(f"\n📊 Dashboard Features:")
        print(f"   • Real-time quota gauges (per user)")
        print(f"   • Token usage trends (hourly)")
        print(f"   • Monthly/daily quota tracking")
        print(f"   • Lambda performance metrics")
        print(f"   • User comparison charts")
        print(f"   • Alarm status")

        print(f"\n📝 Dashboard Sections:")
        print(f"   Row 1: Header and overview")
        print(f"   Row 2: Quota gauges (5 users)")
        print(f"   Row 3: Usage sparklines")
        print(f"   Row 4: Token trends + quota %")
        print(f"   Row 5: Daily quota + API calls")
        print(f"   Row 6: Lambda health metrics")
        print(f"   Row 7: User comparison + status")
        print(f"   Row 8: Active alarms")

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
