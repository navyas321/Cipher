# Deployment Guide

Quick deployment steps for the Bedrock Agent video processing system.

## Prerequisites

```bash
pip install boto3
export DEEPGRAM_API_KEY=your_key_here
```

## Step 1: Setup Bedrock Agents

```bash
python bedrock_agent_setup.py
```

Creates agents, roles, and aliases. Outputs `bedrock_agent_config.json`.

## Step 2: Deploy Lambda Functions

```bash
python deploy_lambdas.py
```

Deploys both Lambda functions with dependencies.

## Step 3: Configure Action Groups

```bash
# Get action Lambda ARN from previous step output
python configure_orchestrator_agent.py arn:aws:lambda:REGION:ACCOUNT:function:video-processing-action-group
```

## Step 4: Test

```bash
# Upload a test video to S3 first
aws s3 cp test_video.mp4 s3://your-bucket/

# Test the workflow
python test_workflow.py your-bucket test_video.mp4 "Summarize this for a project manager"
```

## Environment Variables

Set in Lambda console or update deployment script:
- `DEEPGRAM_API_KEY` - Your Deepgram API key
- `ORCHESTRATOR_AGENT_ID` - From bedrock_agent_config.json
- `ROLE_AGENT_ID` - From bedrock_agent_config.json

## Verify

```bash
python verify_bedrock_setup.py
```

## Cleanup

```bash
# Delete Lambda functions
aws lambda delete-function --function-name video-processing-orchestrator
aws lambda delete-function --function-name video-processing-action-group

# Delete agents
aws bedrock-agent delete-agent --agent-id <ORCHESTRATOR_ID> --skip-resource-in-use-check
aws bedrock-agent delete-agent --agent-id <ROLE_AGENT_ID> --skip-resource-in-use-check

# Delete IAM roles (remove policies first)
aws iam delete-role --role-name VideoProcessingOrchestratorRole
aws iam delete-role --role-name VideoProcessingActionGroupRole
aws iam delete-role --role-name BedrockOrchestratorAgentRole
aws iam delete-role --role-name BedrockRoleDeterminationAgentRole
```
