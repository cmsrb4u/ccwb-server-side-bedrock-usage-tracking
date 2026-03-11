#!/bin/bash

set -e

REGION="us-west-2"
STACK_NAME="bedrock-hybrid-tracking"

echo "=========================================================================="
echo "Deploying Hybrid Solution: Server-Side Logging + Quota Enforcement"
echo "=========================================================================="
echo "Region: $REGION"
echo "Stack: $STACK_NAME"
echo ""

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ AWS SAM CLI not found. Please install it first:"
    echo "   brew install aws-sam-cli"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Build the SAM application
echo "📦 Building SAM application..."
sam build --template infrastructure-with-quotas.yaml

# Deploy the stack
echo ""
echo "🚀 Deploying CloudFormation stack..."
echo "   This may take 5-10 minutes..."
echo ""

sam deploy \
    --template-file .aws-sam/build/template.yaml \
    --stack-name $STACK_NAME \
    --region $REGION \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset \
    --parameter-overrides \
        Environment=production \
        AlertEmail=admin@example.com

# Get stack outputs
echo ""
echo "=========================================================================="
echo "Deployment Complete!"
echo "=========================================================================="
echo ""
echo "📊 Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

# Save outputs to file for later use
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs' \
    --output json > stack-outputs-hybrid.json

echo ""
echo "✅ Outputs saved to: stack-outputs-hybrid.json"
echo ""
echo "📝 Next Steps:"
echo "   1. Run: python3 post-deploy-hybrid.py"
echo "   2. Test: python3 test-quota-enforcement.py"
echo ""
