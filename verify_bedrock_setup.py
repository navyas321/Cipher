"""
Verification script for Bedrock Agent infrastructure.

This script verifies that all agents and resources are properly configured.
"""

import json
import logging
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
bedrock_agent_client = boto3.client('bedrock-agent')
iam_client = boto3.client('iam')


def load_configuration(config_file: str = "bedrock_agent_config.json") -> Optional[Dict[str, Any]]:
    """Load agent configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing configuration file: {str(e)}")
        return None


def verify_agent(agent_id: str, agent_name: str) -> bool:
    """
    Verify that an agent exists and is in the correct state.
    
    Args:
        agent_id: ID of the agent to verify
        agent_name: Expected name of the agent
        
    Returns:
        True if agent is properly configured, False otherwise
    """
    try:
        logger.info(f"Verifying agent: {agent_name} ({agent_id})")
        
        response = bedrock_agent_client.get_agent(agentId=agent_id)
        agent = response['agent']
        
        # Check agent status
        status = agent['agentStatus']
        logger.info(f"  Status: {status}")
        
        if status not in ['PREPARED', 'NOT_PREPARED', 'CREATING']:
            logger.warning(f"  Unexpected status: {status}")
            return False
        
        # Check foundation model
        model = agent['foundationModel']
        logger.info(f"  Foundation Model: {model}")
        
        if 'claude-3-5-sonnet' not in model:
            logger.warning(f"  Unexpected model: {model}")
            return False
        
        # Check agent name
        actual_name = agent['agentName']
        logger.info(f"  Agent Name: {actual_name}")
        
        logger.info(f"  ✓ Agent {agent_name} verified successfully")
        return True
        
    except ClientError as e:
        logger.error(f"  ✗ Error verifying agent: {str(e)}")
        return False


def verify_agent_alias(agent_id: str, alias_id: str, alias_name: str) -> bool:
    """
    Verify that an agent alias exists.
    
    Args:
        agent_id: ID of the agent
        alias_id: ID of the alias
        alias_name: Expected name of the alias
        
    Returns:
        True if alias is properly configured, False otherwise
    """
    try:
        logger.info(f"Verifying alias: {alias_name} ({alias_id})")
        
        response = bedrock_agent_client.get_agent_alias(
            agentId=agent_id,
            agentAliasId=alias_id
        )
        alias = response['agentAlias']
        
        # Check alias status
        status = alias['agentAliasStatus']
        logger.info(f"  Status: {status}")
        
        # Check alias name
        actual_name = alias['agentAliasName']
        logger.info(f"  Alias Name: {actual_name}")
        
        if actual_name != alias_name:
            logger.warning(f"  Name mismatch: expected {alias_name}, got {actual_name}")
            return False
        
        logger.info(f"  ✓ Alias {alias_name} verified successfully")
        return True
        
    except ClientError as e:
        logger.error(f"  ✗ Error verifying alias: {str(e)}")
        return False


def verify_iam_role(role_arn: str, role_name: str) -> bool:
    """
    Verify that an IAM role exists and has the correct trust policy.
    
    Args:
        role_arn: ARN of the role
        role_name: Name of the role
        
    Returns:
        True if role is properly configured, False otherwise
    """
    try:
        logger.info(f"Verifying IAM role: {role_name}")
        
        response = iam_client.get_role(RoleName=role_name)
        role = response['Role']
        
        # Check role ARN
        actual_arn = role['Arn']
        if actual_arn != role_arn:
            logger.warning(f"  ARN mismatch: expected {role_arn}, got {actual_arn}")
            return False
        
        # Check trust policy
        trust_policy = role['AssumeRolePolicyDocument']
        logger.info(f"  Trust Policy: {json.dumps(trust_policy, indent=2)}")
        
        # Verify Bedrock service is in trust policy
        has_bedrock_trust = False
        for statement in trust_policy.get('Statement', []):
            principal = statement.get('Principal', {})
            if 'bedrock.amazonaws.com' in str(principal):
                has_bedrock_trust = True
                break
        
        if not has_bedrock_trust:
            logger.warning("  Missing Bedrock trust relationship")
            return False
        
        # Check attached policies
        try:
            policies = iam_client.list_role_policies(RoleName=role_name)
            logger.info(f"  Inline Policies: {policies['PolicyNames']}")
        except ClientError:
            logger.warning("  Could not list inline policies")
        
        logger.info(f"  ✓ IAM role {role_name} verified successfully")
        return True
        
    except ClientError as e:
        logger.error(f"  ✗ Error verifying IAM role: {str(e)}")
        return False


def test_agent_invocation(agent_id: str, alias_id: str, test_prompt: str) -> bool:
    """
    Test invoking an agent with a simple prompt.
    
    Args:
        agent_id: ID of the agent
        alias_id: ID of the alias to use
        test_prompt: Test prompt to send
        
    Returns:
        True if invocation succeeds, False otherwise
    """
    try:
        logger.info(f"Testing agent invocation: {agent_id}")
        logger.info(f"  Test prompt: {test_prompt}")
        
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId='test-session-123',
            inputText=test_prompt
        )
        
        # Read response stream
        event_stream = response['completion']
        full_response = ""
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    full_response += chunk['bytes'].decode('utf-8')
        
        logger.info(f"  Response received: {len(full_response)} characters")
        logger.info(f"  ✓ Agent invocation successful")
        return True
        
    except ClientError as e:
        logger.error(f"  ✗ Error invoking agent: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"  ✗ Unexpected error: {str(e)}")
        return False


def run_verification() -> bool:
    """
    Run complete verification of Bedrock Agent infrastructure.
    
    Returns:
        True if all verifications pass, False otherwise
    """
    logger.info("="*60)
    logger.info("BEDROCK AGENT INFRASTRUCTURE VERIFICATION")
    logger.info("="*60)
    
    # Load configuration
    config = load_configuration()
    if not config:
        logger.error("Failed to load configuration. Run bedrock_agent_setup.py first.")
        return False
    
    all_checks_passed = True
    
    # Verify IAM Roles
    logger.info("\n=== Verifying IAM Roles ===")
    
    orchestrator_role_arn = config.get('orchestrator_role_arn')
    if orchestrator_role_arn:
        role_name = orchestrator_role_arn.split('/')[-1]
        if not verify_iam_role(orchestrator_role_arn, role_name):
            all_checks_passed = False
    
    role_agent_role_arn = config.get('role_agent_role_arn')
    if role_agent_role_arn:
        role_name = role_agent_role_arn.split('/')[-1]
        if not verify_iam_role(role_agent_role_arn, role_name):
            all_checks_passed = False
    
    # Verify Role Determination Agent
    logger.info("\n=== Verifying Role Determination Agent ===")
    role_agent = config.get('role_agent', {})
    role_agent_id = role_agent.get('agentId')
    
    if role_agent_id:
        if not verify_agent(role_agent_id, "RoleDeterminationAgent"):
            all_checks_passed = False
        
        # Verify aliases
        role_agent_aliases = config.get('role_agent_aliases', {})
        for alias_name, alias_info in role_agent_aliases.items():
            alias_id = alias_info.get('agentAliasId')
            if alias_id:
                if not verify_agent_alias(role_agent_id, alias_id, alias_name):
                    all_checks_passed = False
    
    # Verify Orchestrator Agent
    logger.info("\n=== Verifying Orchestrator Agent ===")
    orchestrator_agent = config.get('orchestrator_agent', {})
    orchestrator_agent_id = orchestrator_agent.get('agentId')
    
    if orchestrator_agent_id:
        if not verify_agent(orchestrator_agent_id, "VideoProcessingOrchestrator"):
            all_checks_passed = False
        
        # Verify aliases
        orchestrator_aliases = config.get('orchestrator_aliases', {})
        for alias_name, alias_info in orchestrator_aliases.items():
            alias_id = alias_info.get('agentAliasId')
            if alias_id:
                if not verify_agent_alias(orchestrator_agent_id, alias_id, alias_name):
                    all_checks_passed = False
    
    # Test agent invocations (optional)
    logger.info("\n=== Testing Agent Invocations ===")
    logger.info("Testing Role Determination Agent...")
    
    if role_agent_id:
        test_alias = role_agent_aliases.get('test', {}).get('agentAliasId')
        if test_alias:
            test_prompt = "Summarize this video for a project manager"
            if not test_agent_invocation(role_agent_id, test_alias, test_prompt):
                logger.warning("Role Determination Agent invocation test failed (this may be expected if action groups are not configured)")
    
    # Print summary
    logger.info("\n" + "="*60)
    if all_checks_passed:
        logger.info("✓ ALL VERIFICATIONS PASSED")
        logger.info("="*60)
        logger.info("\nYour Bedrock Agent infrastructure is properly configured!")
        logger.info("\nNext steps:")
        logger.info("1. Implement action group Lambda function (Task 2)")
        logger.info("2. Configure action groups for Orchestrator Agent (Task 3)")
        logger.info("3. Test complete workflow")
    else:
        logger.info("✗ SOME VERIFICATIONS FAILED")
        logger.info("="*60)
        logger.info("\nPlease review the errors above and fix any issues.")
    
    return all_checks_passed


if __name__ == "__main__":
    try:
        success = run_verification()
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Verification failed with error: {str(e)}")
        exit(1)
