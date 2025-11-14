# Quick Start Guide - Bedrock Agent Infrastructure

This guide will help you quickly set up and verify the Bedrock Agent infrastructure for video processing.

## Prerequisites Checklist

- [ ] AWS CLI installed and configured
- [ ] Python 3.9+ installed
- [ ] AWS account with Bedrock access enabled
- [ ] IAM permissions to create roles and Bedrock agents
- [ ] Deepgram API key (sign up at [deepgram.com](https://deepgram.com))

## Step-by-Step Setup

### 1. Install Dependencies

```bash
cd Cipher
pip install -r setup_requirements.txt
```

### 2. Configure AWS Credentials

Ensure your AWS credentials are configured:

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and default region
```

Verify access:

```bash
aws sts get-caller-identity
```

### 3. Run the Setup Script

```bash
python bedrock_agent_setup.py
```

This will create:
- 2 IAM roles with appropriate permissions
- 2 Bedrock Agents (Orchestrator and Role Determination)
- 4 Agent aliases (test and production for each agent)
- Configuration file: `bedrock_agent_config.json`

**Expected output:**
```
=== Step 1: Creating IAM Roles ===
Creating IAM role: BedrockOrchestratorAgentRole
Created IAM role: arn:aws:iam::...

=== Step 2: Attaching IAM Policies ===
Attaching policy to role: BedrockOrchestratorAgentRole
...

=== Setup Complete ===
Orchestrator Agent ID: XXXXXXXXXX
Role Determination Agent ID: YYYYYYYYYY
```

**Time estimate:** 2-3 minutes

### 4. Verify the Setup

```bash
python verify_bedrock_setup.py
```

This will verify:
- IAM roles exist with correct permissions
- Agents are created and in correct state
- Aliases are configured properly
- Basic agent invocation works

**Expected output:**
```
=== Verifying IAM Roles ===
✓ IAM role BedrockOrchestratorAgentRole verified successfully

=== Verifying Role Determination Agent ===
✓ Agent RoleDeterminationAgent verified successfully
✓ Alias test verified successfully
✓ Alias production verified successfully

=== Verifying Orchestrator Agent ===
✓ Agent VideoProcessingOrchestrator verified successfully
✓ Alias test verified successfully
✓ Alias production verified successfully

✓ ALL VERIFICATIONS PASSED
```

### 5. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```bash
# Required: Your Deepgram API key
DEEPGRAM_API_KEY=your_actual_deepgram_key

# Copy these from bedrock_agent_config.json
ORCHESTRATOR_AGENT_ID=XXXXXXXXXX
ROLE_AGENT_ID=YYYYYYYYYY
```

To extract agent IDs from the config file:

```bash
# On macOS/Linux
cat bedrock_agent_config.json | grep -A 1 '"agentId"'

# Or use Python
python -c "import json; config = json.load(open('bedrock_agent_config.json')); print('Orchestrator:', config['orchestrator_agent']['agentId']); print('Role Agent:', config['role_agent']['agentId'])"
```

### 6. Test the Infrastructure

You can test the Role Determination Agent directly:

```bash
# Create a test script
cat > test_agent.py << 'EOF'
import boto3
import json

# Load configuration
with open('bedrock_agent_config.json', 'r') as f:
    config = json.load(f)

role_agent_id = config['role_agent']['agentId']
test_alias_id = config['role_agent_aliases']['test']['agentAliasId']

# Initialize client
client = boto3.client('bedrock-agent-runtime')

# Test invocation
response = client.invoke_agent(
    agentId=role_agent_id,
    agentAliasId=test_alias_id,
    sessionId='test-session-123',
    inputText='Summarize this video for a project manager'
)

# Read response
for event in response['completion']:
    if 'chunk' in event:
        chunk = event['chunk']
        if 'bytes' in chunk:
            print(chunk['bytes'].decode('utf-8'), end='')
print()
EOF

python test_agent.py
```

## Troubleshooting

### Issue: "Access Denied" when creating agents

**Solution:** Ensure your IAM user/role has these permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:CreateAgent",
        "bedrock:CreateAgentAlias",
        "bedrock:PrepareAgent",
        "iam:CreateRole",
        "iam:PutRolePolicy",
        "iam:GetRole"
      ],
      "Resource": "*"
    }
  ]
}
```

### Issue: "Model not found" error

**Solution:** Ensure Bedrock is enabled in your AWS account and you have access to Claude 3.5 Sonnet:

```bash
# Check available models
aws bedrock list-foundation-models --region us-east-1 | grep claude-3-5-sonnet
```

If not available, request access in the AWS Bedrock console.

### Issue: Setup script hangs or times out

**Solution:** The script includes wait times for AWS resource propagation. If it hangs:
1. Check CloudWatch logs for errors
2. Verify network connectivity
3. Try running in a different AWS region

### Issue: Verification fails with "Agent not found"

**Solution:** Wait a few minutes for AWS resources to propagate, then run verification again:

```bash
sleep 60
python verify_bedrock_setup.py
```

## Next Steps

After successful setup:

1. **Implement Action Group Lambda** (Task 2)
   - Create Lambda function for action group handlers
   - Implement S3 retrieval, transcription, and role invocation actions

2. **Configure Action Groups** (Task 3)
   - Link action group Lambda to Orchestrator Agent
   - Define action schemas

3. **Test End-to-End Workflow**
   - Upload test video to S3
   - Invoke Orchestrator Agent with user prompt
   - Verify role-specific summary generation

## Useful Commands

```bash
# List all agents
aws bedrock-agent list-agents --region us-east-1

# Get agent details
aws bedrock-agent get-agent --agent-id <AGENT_ID> --region us-east-1

# List agent aliases
aws bedrock-agent list-agent-aliases --agent-id <AGENT_ID> --region us-east-1

# View CloudWatch logs
aws logs tail /aws/bedrock/agents --follow --region us-east-1
```

## Cleanup

To remove all created resources:

```bash
# Delete agents (includes aliases)
aws bedrock-agent delete-agent --agent-id <ORCHESTRATOR_ID> --skip-resource-in-use-check
aws bedrock-agent delete-agent --agent-id <ROLE_AGENT_ID> --skip-resource-in-use-check

# Delete IAM roles
aws iam delete-role-policy --role-name BedrockOrchestratorAgentRole --policy-name BedrockOrchestratorAgentRole-policy
aws iam delete-role --role-name BedrockOrchestratorAgentRole

aws iam delete-role-policy --role-name BedrockRoleDeterminationAgentRole --policy-name BedrockRoleDeterminationAgentRole-policy
aws iam delete-role --role-name BedrockRoleDeterminationAgentRole
```

## Support

- **AWS Bedrock Documentation**: https://docs.aws.amazon.com/bedrock/
- **Bedrock Agents Guide**: https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- **Deepgram Documentation**: https://developers.deepgram.com/

## Summary

You've successfully set up:
- ✅ 2 Bedrock Agents with Claude 3.5 Sonnet
- ✅ IAM roles with appropriate permissions
- ✅ Test and production aliases
- ✅ Configuration file for easy reference

Your infrastructure is ready for the next implementation tasks!
