#!/bin/bash

set -e

echo "=========================================================================="
echo "Deploying Bedrock Tracking Solution (Simplified Approach)"
echo "=========================================================================="

# Step 1: Deploy core DynamoDB tables first
echo ""
echo "Step 1: Creating DynamoDB tables..."
echo ""

aws dynamodb create-table \
    --table-name Bedrock-UserMetadata \
    --attribute-definitions \
        AttributeName=userId,AttributeType=S \
    --key-schema \
        AttributeName=userId,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-west-2 \
    --no-cli-pager 2>/dev/null || echo "Table already exists"

aws dynamodb create-table \
    --table-name Bedrock-QuotaPolicies \
    --attribute-definitions \
        AttributeName=policy_type,AttributeType=S \
        AttributeName=identifier,AttributeType=S \
    --key-schema \
        AttributeName=policy_type,KeyType=HASH \
        AttributeName=identifier,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region us-west-2 \
    --no-cli-pager 2>/dev/null || echo "Table already exists"

aws dynamodb create-table \
    --table-name Bedrock-UserQuotaMetrics \
    --attribute-definitions \
        AttributeName=user_email,AttributeType=S \
        AttributeName=metric_period,AttributeType=S \
    --key-schema \
        AttributeName=user_email,KeyType=HASH \
        AttributeName=metric_period,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region us-west-2 \
    --no-cli-pager 2>/dev/null || echo "Table already exists"

echo "✅ DynamoDB tables created"

# Step 2: Run post-deploy to seed data
echo ""
echo "Step 2: Seeding user data..."
python3 post-deploy-hybrid.py

echo ""
echo "=========================================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================================================="
echo ""
echo "📝 Next steps:"
echo "   1. Create dashboard: python3 create-dashboard.py"
echo "   2. Test: python3 test-quota-enforcement.py"
echo ""
