"""
Setup script for creating Bedrock Agents infrastructure.

This script creates:
1. IAM roles for Bedrock Agent execution
2. Bedrock Orchestrator Agent with Claude 3.5 Sonnet
3. Bedrock Role Determination Agent with Claude 3.5 Sonnet
4. Agent aliases for testing and production
"""

import json
import logging
import time
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
iam_client = boto3.client('iam')
bedrock_agent_client = boto3.client('bedrock-agent')
sts_client = boto3.client('sts')


def get_account_id() -> str:
    """Get the AWS account ID."""
    return sts_client.get_caller_identity()['Account']


def create_agent_execution_role(role_name: str, agent_type: str) -> str:
    """
    Create IAM role for Bedrock Agent execution.
    
    Args:
        role_name: Name for the IAM role
        agent_type: Type of agent ('orchestrator' or 'role-determination')
        
    Returns:
        ARN of the created IAM role
    """
    account_id = get_account_id()
    
    # Trust policy for Bedrock service
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": account_id
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:*:{account_id}:agent/*"
                    }
                }
            }
        ]
    }
    
    try:
        # Create the role
        logger.info(f"Creating IAM role: {role_name}")
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Execution role for Bedrock {agent_type} Agent",
            Tags=[
                {'Key': 'Project', 'Value': 'VideoProcessing'},
                {'Key': 'AgentType', 'Value': agent_type}
            ]
        )
        role_arn = response['Role']['Arn']
        logger.info(f"Created IAM role: {role_arn}")
        
        # Wait for role to be available
        time.sleep(10)
        
        return role_arn
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            logger.info(f"IAM role {role_name} already exists, retrieving ARN")
            response = iam_client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        else:
            logger.error(f"Error creating IAM role: {str(e)}")
            raise


def attach_agent_policies(role_name: str, agent_type: str) -> None:
    """
    Attach necessary policies to the agent execution role.
    
    Args:
        role_name: Name of the IAM role
        agent_type: Type of agent ('orchestrator' or 'role-determination')
    """
    # Base policy for all agents
    base_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": [
                    f"arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:log-group:/aws/bedrock/*"
            }
        ]
    }
    
    # Additional permissions for orchestrator agent
    if agent_type == 'orchestrator':
        base_policy['Statement'].extend([
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": "arn:aws:lambda:*:*:function:video-processing-*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeAgent"
                ],
                "Resource": "arn:aws:bedrock:*:*:agent/*"
            }
        ])
    
    policy_name = f"{role_name}-policy"
    
    try:
        # Create inline policy
        logger.info(f"Attaching policy to role: {role_name}")
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(base_policy)
        )
        logger.info(f"Successfully attached policy: {policy_name}")
        
    except ClientError as e:
        logger.error(f"Error attaching policy: {str(e)}")
        raise


def create_orchestrator_agent(role_arn: str, agent_name: str = "VideoProcessingOrchestrator") -> Dict[str, Any]:
    """
    Create Bedrock Orchestrator Agent.
    
    Args:
        role_arn: ARN of the IAM execution role
        agent_name: Name for the agent
        
    Returns:
        Dictionary with agent details (agentId, agentArn, agentName)
    """
    instruction = """You are an orchestrator agent that processes video files to generate role-specific summaries.

Your workflow:
1. First, invoke the Role Determination Agent to analyze the user's prompt and extract the target role perspective
2. Retrieve the video file from S3 using the retrieve_video_from_s3 action
3. Transcribe the video using the transcribe_video action
4. Generate a role-specific summary based on the transcription and identified role

When generating summaries:
- Tailor the content to the identified role's perspective and interests
- Focus on information most relevant to that role's responsibilities
- Use clear, professional language appropriate for the role
- Provide actionable insights when applicable

Handle errors gracefully and provide clear feedback if any step fails."""
    
    try:
        logger.info(f"Creating Orchestrator Agent: {agent_name}")
        response = bedrock_agent_client.create_agent(
            agentName=agent_name,
            agentResourceRoleArn=role_arn,
            foundationModel="anthropic.claude-3-5-sonnet-20240620-v1:0",
            instruction=instruction,
            description="Orchestrates video processing workflow including role determination, transcription, and summary generation",
            idleSessionTTLInSeconds=600,
            tags={
                'Project': 'VideoProcessing',
                'AgentType': 'Orchestrator'
            }
        )
        
        agent_id = response['agent']['agentId']
        agent_arn = response['agent']['agentArn']
        
        logger.info(f"Created Orchestrator Agent: {agent_id}")
        logger.info(f"Agent ARN: {agent_arn}")
        
        return {
            'agentId': agent_id,
            'agentArn': agent_arn,
            'agentName': agent_name,
            'status': response['agent']['agentStatus']
        }
        
    except ClientError as e:
        logger.error(f"Error creating Orchestrator Agent: {str(e)}")
        raise


def create_role_determination_agent(role_arn: str, agent_name: str = "RoleDeterminationAgent") -> Dict[str, Any]:
    """
    Create Bedrock Role Determination Agent.
    
    Args:
        role_arn: ARN of the IAM execution role
        agent_name: Name for the agent
        
    Returns:
        Dictionary with agent details (agentId, agentArn, agentName)
    """
    instruction = """You are a role determination agent specialized in analyzing user prompts to identify the target role perspective for video summaries.

Your task:
1. Analyze the user's prompt carefully
2. Identify the specific role or perspective they want the summary tailored for
3. Extract relevant context about what aspects are important for that role
4. Return your analysis in JSON format

Output format (JSON):
{
    "role": "identified role name (e.g., manager, engineer, executive, student)",
    "context": "relevant context about what this role cares about",
    "confidence": 0.95,
    "fallback": false
}

If you cannot determine a specific role:
- Set "fallback" to true
- Use "general" as the role
- Set confidence to 0.0

Examples:
- "Summarize this for a project manager" → role: "project manager"
- "What would an engineer find important?" → role: "engineer"
- "Give me the key points for executives" → role: "executive"
- "Summarize this video" → role: "general", fallback: true"""
    
    try:
        logger.info(f"Creating Role Determination Agent: {agent_name}")
        response = bedrock_agent_client.create_agent(
            agentName=agent_name,
            agentResourceRoleArn=role_arn,
            foundationModel="anthropic.claude-3-5-sonnet-20240620-v1:0",
            instruction=instruction,
            description="Analyzes user prompts to extract role information for tailored video summaries",
            idleSessionTTLInSeconds=600,
            tags={
                'Project': 'VideoProcessing',
                'AgentType': 'RoleDetermination'
            }
        )
        
        agent_id = response['agent']['agentId']
        agent_arn = response['agent']['agentArn']
        
        logger.info(f"Created Role Determination Agent: {agent_id}")
        logger.info(f"Agent ARN: {agent_arn}")
        
        return {
            'agentId': agent_id,
            'agentArn': agent_arn,
            'agentName': agent_name,
            'status': response['agent']['agentStatus']
        }
        
    except ClientError as e:
        logger.error(f"Error creating Role Determination Agent: {str(e)}")
        raise


def prepare_agent(agent_id: str) -> None:
    """
    Prepare agent for use (required before creating aliases).
    
    Args:
        agent_id: ID of the agent to prepare
    """
    try:
        logger.info(f"Preparing agent: {agent_id}")
        bedrock_agent_client.prepare_agent(agentId=agent_id)
        
        # Wait for agent to be prepared
        logger.info("Waiting for agent to be prepared...")
        time.sleep(30)
        
        logger.info(f"Agent {agent_id} prepared successfully")
        
    except ClientError as e:
        logger.error(f"Error preparing agent: {str(e)}")
        raise


def create_agent_alias(agent_id: str, alias_name: str, description: str) -> Dict[str, Any]:
    """
    Create an alias for a Bedrock Agent.
    
    Args:
        agent_id: ID of the agent
        alias_name: Name for the alias
        description: Description of the alias
        
    Returns:
        Dictionary with alias details (agentAliasId, agentAliasArn)
    """
    max_retries = 5
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Creating alias '{alias_name}' for agent: {agent_id} (attempt {attempt + 1}/{max_retries})")
            response = bedrock_agent_client.create_agent_alias(
                agentId=agent_id,
                agentAliasName=alias_name,
                description=description,
                tags={
                    'Project': 'VideoProcessing',
                    'Environment': alias_name
                }
            )
            
            alias_id = response['agentAlias']['agentAliasId']
            alias_arn = response['agentAlias']['agentAliasArn']
            
            logger.info(f"Created alias: {alias_id}")
            logger.info(f"Alias ARN: {alias_arn}")
            
            return {
                'agentAliasId': alias_id,
                'agentAliasArn': alias_arn,
                'agentAliasName': alias_name
            }
            
        except ClientError as e:
            if 'Versioning state' in str(e) and attempt < max_retries - 1:
                logger.warning(f"Agent still in versioning state, waiting {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            logger.error(f"Error creating agent alias: {str(e)}")
            raise


def setup_bedrock_infrastructure() -> Dict[str, Any]:
    """
    Set up complete Bedrock Agent infrastructure.
    
    Returns:
        Dictionary with all created resource details
    """
    logger.info("Starting Bedrock Agent infrastructure setup...")
    
    results = {}
    
    try:
        # Step 1: Create IAM roles
        logger.info("\n=== Step 1: Creating IAM Roles ===")
        orchestrator_role_name = "BedrockOrchestratorAgentRole"
        role_agent_role_name = "BedrockRoleDeterminationAgentRole"
        
        orchestrator_role_arn = create_agent_execution_role(orchestrator_role_name, "orchestrator")
        role_agent_role_arn = create_agent_execution_role(role_agent_role_name, "role-determination")
        
        results['orchestrator_role_arn'] = orchestrator_role_arn
        results['role_agent_role_arn'] = role_agent_role_arn
        
        # Step 2: Attach policies to roles
        logger.info("\n=== Step 2: Attaching IAM Policies ===")
        attach_agent_policies(orchestrator_role_name, "orchestrator")
        attach_agent_policies(role_agent_role_name, "role-determination")
        
        # Step 3: Create Role Determination Agent
        logger.info("\n=== Step 3: Creating Role Determination Agent ===")
        role_agent = create_role_determination_agent(role_agent_role_arn)
        results['role_agent'] = role_agent
        
        # Step 4: Create Orchestrator Agent
        logger.info("\n=== Step 4: Creating Orchestrator Agent ===")
        orchestrator_agent = create_orchestrator_agent(orchestrator_role_arn)
        results['orchestrator_agent'] = orchestrator_agent
        
        # Step 5: Prepare agents
        logger.info("\n=== Step 5: Preparing Agents ===")
        prepare_agent(role_agent['agentId'])
        prepare_agent(orchestrator_agent['agentId'])
        
        # Step 6: Create aliases for Role Determination Agent
        logger.info("\n=== Step 6: Creating Aliases for Role Determination Agent ===")
        role_agent_test_alias = create_agent_alias(
            role_agent['agentId'],
            "test",
            "Test alias for Role Determination Agent"
        )
        role_agent_prod_alias = create_agent_alias(
            role_agent['agentId'],
            "production",
            "Production alias for Role Determination Agent"
        )
        
        results['role_agent_aliases'] = {
            'test': role_agent_test_alias,
            'production': role_agent_prod_alias
        }
        
        # Step 7: Create aliases for Orchestrator Agent
        logger.info("\n=== Step 7: Creating Aliases for Orchestrator Agent ===")
        orchestrator_test_alias = create_agent_alias(
            orchestrator_agent['agentId'],
            "test",
            "Test alias for Orchestrator Agent"
        )
        orchestrator_prod_alias = create_agent_alias(
            orchestrator_agent['agentId'],
            "production",
            "Production alias for Orchestrator Agent"
        )
        
        results['orchestrator_aliases'] = {
            'test': orchestrator_test_alias,
            'production': orchestrator_prod_alias
        }
        
        logger.info("\n=== Setup Complete ===")
        logger.info(f"\nOrchestrator Agent ID: {orchestrator_agent['agentId']}")
        logger.info(f"Role Determination Agent ID: {role_agent['agentId']}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during infrastructure setup: {str(e)}")
        raise


def save_configuration(results: Dict[str, Any], output_file: str = "bedrock_agent_config.json") -> None:
    """
    Save agent configuration to a JSON file.
    
    Args:
        results: Dictionary with agent details
        output_file: Path to output file
    """
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nConfiguration saved to: {output_file}")
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")


if __name__ == "__main__":
    try:
        # Run the setup
        results = setup_bedrock_infrastructure()
        
        # Save configuration
        save_configuration(results)
        
        # Print summary
        print("\n" + "="*60)
        print("BEDROCK AGENT INFRASTRUCTURE SETUP COMPLETE")
        print("="*60)
        print(f"\nOrchestrator Agent:")
        print(f"  Agent ID: {results['orchestrator_agent']['agentId']}")
        print(f"  Test Alias: {results['orchestrator_aliases']['test']['agentAliasId']}")
        print(f"  Production Alias: {results['orchestrator_aliases']['production']['agentAliasId']}")
        print(f"\nRole Determination Agent:")
        print(f"  Agent ID: {results['role_agent']['agentId']}")
        print(f"  Test Alias: {results['role_agent_aliases']['test']['agentAliasId']}")
        print(f"  Production Alias: {results['role_agent_aliases']['production']['agentAliasId']}")
        print(f"\nConfiguration saved to: bedrock_agent_config.json")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")
        exit(1)
