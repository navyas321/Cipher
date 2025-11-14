# Bedrock Agent Infrastructure Setup

This directory contains scripts and templates to set up the Bedrock Agent infrastructure for video processing.

## Overview

The infrastructure consists of:
- **Orchestrator Agent**: Coordinates the video processing workflow
- **Role Determination Agent**: Analyzes user prompts to extract role information
- **IAM Roles**: Execution roles with necessary permissions for both agents
- **Agent Aliases**: Test and production aliases for both agents

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Python 3.9+ with boto3 installed
3. AWS account with Bedrock access enabled
4. Permissions to create IAM roles and Bedrock agents

## Deployment Options

### Option 1: Python Script (Recommended for Quick Setup)

The Python script provides a programmatic way to create all resources with detailed logging.

```bash
# Install dependencies
pip install boto3

# Run the setup script
cd Cipher
python bedrock_agent_setup.py
```

The script will:
1. Create IAM roles for both agents
2. Attach necessary policies
3. Create the Role Determination Agent
4. Create the Orchestrator Agent
5. Prepare both agents
6. Create test and production aliases
7. Save configuration to `bedrock_agent_config.json`

**Output:**
- Console output with progress and resource IDs
- `bedrock_agent_config.json` file with all resource details

### Option 2: CloudFormation Template

The CloudFormation template provides infrastructure-as-code for reproducible deployments.

```bash
# Deploy the stack
aws cloudformation create-stack \
  --stack-name bedrock-video-processing-agents \
  --template-body file://bedrock-agents-cfn.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Wait for stack creation to complete
aws cloudformation wait stack-create-complete \
  --stack-name bedrock-video-processing-agents \
  --region us-east-1

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name bedrock-video-processing-agents \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'
```

**Note:** CloudFormation support for Bedrock Agents may vary by region. If you encounter issues, use the Python script instead.

## Configuration Details

### Orchestrator Agent

- **Name**: VideoProcessingOrchestrator
- **Foundation Model**: Claude 3.5 Sonnet (anthropic.claude-3-5-sonnet-20240620-v1:0)
- **Purpose**: Coordinates workflow from video retrieval to summary generation
- **Capabilities**:
  - Invokes Role Determination Agent
  - Calls action group functions (S3 retrieval, transcription)
  - Generates role-specific summaries

### Role Determination Agent

- **Name**: RoleDeterminationAgent
- **Foundation Model**: Claude 3.5 Sonnet (anthropic.claude-3-5-sonnet-20240620-v1:0)
- **Purpose**: Extracts role information from user prompts
- **Output Format**: JSON with role, context, confidence, and fallback fields

### IAM Permissions

**Orchestrator Agent Role:**
- `bedrock:InvokeModel` - For Claude 3.5 Sonnet
- `bedrock:InvokeAgent` - For calling Role Determination Agent
- `lambda:InvokeFunction` - For action group Lambda functions
- CloudWatch Logs permissions

**Role Determination Agent Role:**
- `bedrock:InvokeModel` - For Claude 3.5 Sonnet
- CloudWatch Logs permissions

## Verification

After deployment, verify the agents are created:

```bash
# List all agents
aws bedrock-agent list-agents --region us-east-1

# Get specific agent details
aws bedrock-agent get-agent \
  --agent-id <AGENT_ID> \
  --region us-east-1

# List agent aliases
aws bedrock-agent list-agent-aliases \
  --agent-id <AGENT_ID> \
  --region us-east-1
```

## Using the Configuration

The `bedrock_agent_config.json` file (created by Python script) contains:

```json
{
  "orchestrator_agent": {
    "agentId": "XXXXXXXXXX",
    "agentArn": "arn:aws:bedrock:...",
    "agentName": "VideoProcessingOrchestrator"
  },
  "role_agent": {
    "agentId": "YYYYYYYYYY",
    "agentArn": "arn:aws:bedrock:...",
    "agentName": "RoleDeterminationAgent"
  },
  "orchestrator_aliases": {
    "test": {"agentAliasId": "TSTALIASID", ...},
    "production": {"agentAliasId": "PRODALIASID", ...}
  },
  "role_agent_aliases": {
    "test": {"agentAliasId": "TSTALIASID", ...},
    "production": {"agentAliasId": "PRODALIASID", ...}
  }
}
```

Use these IDs in your Lambda functions and environment variables.

## Environment Variables for Lambda

After setup, configure your Lambda functions with:

```bash
# For main Lambda handler
ORCHESTRATOR_AGENT_ID=<orchestrator_agent_id>
ROLE_AGENT_ID=<role_agent_id>

# For action group Lambda
DEEPGRAM_API_KEY=<your_deepgram_key>
DEFAULT_ROLE=general
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
```

## Cleanup

### Python Script Resources

To delete resources created by the Python script:

```bash
# Delete agents (this also deletes aliases)
aws bedrock-agent delete-agent \
  --agent-id <ORCHESTRATOR_AGENT_ID> \
  --skip-resource-in-use-check \
  --region us-east-1

aws bedrock-agent delete-agent \
  --agent-id <ROLE_AGENT_ID> \
  --skip-resource-in-use-check \
  --region us-east-1

# Delete IAM roles
aws iam delete-role-policy \
  --role-name BedrockOrchestratorAgentRole \
  --policy-name BedrockOrchestratorAgentRole-policy

aws iam delete-role \
  --role-name BedrockOrchestratorAgentRole

aws iam delete-role-policy \
  --role-name BedrockRoleDeterminationAgentRole \
  --policy-name BedrockRoleDeterminationAgentRole-policy

aws iam delete-role \
  --role-name BedrockRoleDeterminationAgentRole
```

### CloudFormation Stack

```bash
aws cloudformation delete-stack \
  --stack-name bedrock-video-processing-agents \
  --region us-east-1
```

## Troubleshooting

### Agent Creation Fails

- Ensure Bedrock is enabled in your AWS account
- Verify you have access to Claude 3.5 Sonnet model
- Check IAM permissions for creating agents and roles

### Permission Errors

- Ensure the IAM user/role running the script has:
  - `iam:CreateRole`, `iam:PutRolePolicy`
  - `bedrock:CreateAgent`, `bedrock:CreateAgentAlias`
  - `bedrock:PrepareAgent`

### Region Availability

- Bedrock Agents may not be available in all regions
- Recommended regions: us-east-1, us-west-2
- Check AWS documentation for current availability

## Next Steps

After infrastructure setup:
1. Implement action group Lambda function (Task 2)
2. Configure action groups for Orchestrator Agent (Task 3)
3. Test agent invocations
4. Deploy main Lambda handler (Task 5)

## Support

For issues or questions:
- Check AWS Bedrock documentation
- Review CloudWatch logs for agent execution
- Verify IAM permissions and trust relationships
