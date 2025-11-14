"""
Configure Bedrock Orchestrator Agent with action groups.
"""

import json
import logging
import time
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bedrock_agent_client = boto3.client('bedrock-agent')


def load_config(config_file: str = "bedrock_agent_config.json") -> Dict[str, Any]:
    """Load agent configuration."""
    with open(config_file, 'r') as f:
        return json.load(f)


def load_action_schema(schema_file: str = "action_group_schema.json") -> str:
    """Load action group schema."""
    with open(schema_file, 'r') as f:
        return json.dumps(json.load(f))


def create_action_group(agent_id: str, lambda_arn: str, schema: str) -> Dict[str, Any]:
    """
    Create action group for Orchestrator Agent.
    
    Args:
        agent_id: Orchestrator Agent ID
        lambda_arn: ARN of action group Lambda function
        schema: OpenAPI schema as JSON string
        
    Returns:
        Action group details
    """
    try:
        logger.info(f"Creating action group for agent: {agent_id}")
        
        response = bedrock_agent_client.create_agent_action_group(
            agentId=agent_id,
            agentVersion='DRAFT',
            actionGroupName='video-processing-actions',
            description='Actions for video processing workflow',
            actionGroupExecutor={
                'lambda': lambda_arn
            },
            apiSchema={
                'payload': schema
            },
            actionGroupState='ENABLED'
        )
        
        action_group = response['agentActionGroup']
        logger.info(f"Created action group: {action_group['actionGroupId']}")
        
        return action_group
        
    except ClientError as e:
        logger.error(f"Error creating action group: {str(e)}")
        raise


def update_agent_instruction(agent_id: str) -> None:
    """
    Update Orchestrator Agent instruction with workflow details.
    
    Args:
        agent_id: Orchestrator Agent ID
    """
    instruction = """You are an orchestrator agent that processes video files to generate role-specific summaries.

Your workflow:
1. First, call the invoke_role_agent action to analyze the user's prompt and extract the target role perspective
2. Call the retrieve_video_from_s3 action to get the video file from S3
3. Call the transcribe_video action to transcribe the video using Deepgram
4. Generate a role-specific summary based on the transcription and identified role using your foundation model

When generating summaries:
- Tailor the content to the identified role's perspective and interests
- Focus on information most relevant to that role's responsibilities
- Use clear, professional language appropriate for the role
- Provide actionable insights when applicable
- Structure the summary with clear sections

Handle errors gracefully:
- If role determination fails, use the default role provided
- If video retrieval fails, inform the user about the specific error
- If transcription fails, explain the issue clearly

Always provide a complete, well-structured response to the user."""
    
    try:
        logger.info(f"Updating agent instruction for: {agent_id}")
        
        # Get current agent details
        agent_response = bedrock_agent_client.get_agent(agentId=agent_id)
        agent = agent_response['agent']
        
        bedrock_agent_client.update_agent(
            agentId=agent_id,
            agentName='VideoProcessingOrchestrator',
            agentResourceRoleArn=agent['agentResourceRoleArn'],
            instruction=instruction,
            foundationModel='anthropic.claude-3-5-sonnet-20240620-v1:0'
        )
        
        logger.info("Agent instruction updated successfully")
        
    except ClientError as e:
        logger.error(f"Error updating agent instruction: {str(e)}")
        raise


def prepare_agent(agent_id: str) -> None:
    """Prepare agent after configuration changes."""
    try:
        logger.info(f"Preparing agent: {agent_id}")
        bedrock_agent_client.prepare_agent(agentId=agent_id)
        logger.info("Waiting for agent to be prepared...")
        time.sleep(30)
        logger.info("Agent prepared successfully")
    except ClientError as e:
        logger.error(f"Error preparing agent: {str(e)}")
        raise


def configure_orchestrator(lambda_arn: str) -> None:
    """
    Configure Orchestrator Agent with action groups.
    
    Args:
        lambda_arn: ARN of action group Lambda function
    """
    logger.info("Configuring Orchestrator Agent...")
    
    # Load configuration
    config = load_config()
    agent_id = config['orchestrator_agent']['agentId']
    
    # Load action schema
    schema = load_action_schema()
    
    # Update agent instruction
    update_agent_instruction(agent_id)
    
    # Create action group
    action_group = create_action_group(agent_id, lambda_arn, schema)
    
    # Prepare agent
    prepare_agent(agent_id)
    
    # Save updated config
    config['orchestrator_action_group'] = {
        'actionGroupId': action_group['actionGroupId'],
        'actionGroupName': action_group['actionGroupName'],
        'lambdaArn': lambda_arn
    }
    
    with open('bedrock_agent_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info("Orchestrator Agent configured successfully")
    logger.info(f"Action Group ID: {action_group['actionGroupId']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python configure_orchestrator_agent.py <lambda_arn>")
        print("Example: python configure_orchestrator_agent.py arn:aws:lambda:us-east-1:123456789012:function:video-actions")
        sys.exit(1)
    
    lambda_arn = sys.argv[1]
    
    try:
        configure_orchestrator(lambda_arn)
        print("\n✓ Orchestrator Agent configured successfully")
    except Exception as e:
        logger.error(f"Configuration failed: {str(e)}")
        sys.exit(1)
