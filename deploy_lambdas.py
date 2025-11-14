"""
Deploy Lambda functions for Bedrock Agent video processing.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

lambda_client = boto3.client('lambda')
iam_client = boto3.client('iam')
sts_client = boto3.client('sts')


def get_account_id() -> str:
    """Get AWS account ID."""
    return sts_client.get_caller_identity()['Account']


def create_lambda_role(role_name: str, role_type: str) -> str:
    """
    Create IAM role for Lambda function.
    
    Args:
        role_name: Name for the IAM role
        role_type: Type of Lambda (orchestrator or action-group)
        
    Returns:
        Role ARN
    """
    account_id = get_account_id()
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        logger.info(f"Creating Lambda role: {role_name}")
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Role for {role_type} Lambda function"
        )
        role_arn = response['Role']['Arn']
        logger.info(f"Created role: {role_arn}")
        
        # Attach basic Lambda execution policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        # Add custom policies
        if role_type == 'action-group':
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject"],
                        "Resource": "arn:aws:s3:::*/*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["bedrock:InvokeAgent"],
                        "Resource": f"arn:aws:bedrock:*:{account_id}:agent/*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["secretsmanager:GetSecretValue"],
                        "Resource": f"arn:aws:secretsmanager:*:{account_id}:secret:*"
                    }
                ]
            }
        else:  # orchestrator
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["bedrock:InvokeAgent"],
                        "Resource": f"arn:aws:bedrock:*:{account_id}:agent/*"
                    }
                ]
            }
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}-policy",
            PolicyDocument=json.dumps(policy)
        )
        
        import time
        time.sleep(10)  # Wait for role propagation
        
        return role_arn
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            logger.info(f"Role {role_name} already exists")
            response = iam_client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        raise


def create_deployment_package(function_name: str, handler_file: str, include_deps: bool = False) -> str:
    """
    Create Lambda deployment package.
    
    Args:
        function_name: Name of the function
        handler_file: Python file containing handler
        include_deps: Whether to include video_summarization_tool
        
    Returns:
        Path to zip file
    """
    logger.info(f"Creating deployment package for {function_name}")
    
    temp_dir = tempfile.mkdtemp()
    zip_path = f"{function_name}.zip"
    
    try:
        # Copy handler file
        shutil.copy(handler_file, os.path.join(temp_dir, os.path.basename(handler_file)))
        
        # Copy dependencies if needed
        if include_deps:
            # Copy video_summarization_tool module
            if os.path.exists('video_summarization_tool'):
                shutil.copytree(
                    'video_summarization_tool',
                    os.path.join(temp_dir, 'video_summarization_tool')
                )
            
            # Install Python dependencies
            logger.info("Installing Python dependencies...")
            subprocess.run([
                'pip', 'install',
                '-r', 'requirements.txt',
                '-t', temp_dir,
                '--upgrade'
            ], check=True)
        
        # Create zip file
        logger.info(f"Creating zip file: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Deployment package created: {zip_path}")
        return zip_path
        
    finally:
        shutil.rmtree(temp_dir)


def create_or_update_lambda(
    function_name: str,
    handler: str,
    role_arn: str,
    zip_path: str,
    env_vars: Dict[str, str],
    timeout: int = 300,
    memory: int = 2048
) -> str:
    """
    Create or update Lambda function.
    
    Args:
        function_name: Name of the Lambda function
        handler: Handler string (e.g., 'lambda_handler.lambda_handler')
        role_arn: IAM role ARN
        zip_path: Path to deployment package
        env_vars: Environment variables
        timeout: Function timeout in seconds
        memory: Memory allocation in MB
        
    Returns:
        Function ARN
    """
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    try:
        # Try to get existing function
        logger.info(f"Checking if function exists: {function_name}")
        lambda_client.get_function(FunctionName=function_name)
        
        # Update existing function
        logger.info(f"Updating function: {function_name}")
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        # Update configuration
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Role=role_arn,
            Handler=handler,
            Runtime='python3.11',
            Timeout=timeout,
            MemorySize=memory,
            Environment={'Variables': env_vars}
        )
        
        logger.info(f"Updated function: {response['FunctionArn']}")
        return response['FunctionArn']
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # Create new function
            logger.info(f"Creating function: {function_name}")
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.11',
                Role=role_arn,
                Handler=handler,
                Code={'ZipFile': zip_content},
                Timeout=timeout,
                MemorySize=memory,
                Environment={'Variables': env_vars},
                Description=f"Bedrock Agent {function_name}"
            )
            
            logger.info(f"Created function: {response['FunctionArn']}")
            return response['FunctionArn']
        else:
            raise


def add_bedrock_permission(function_name: str, agent_id: str) -> None:
    """Add permission for Bedrock Agent to invoke Lambda."""
    try:
        account_id = get_account_id()
        region = boto3.session.Session().region_name or 'us-west-2'
        
        logger.info(f"Adding Bedrock permission to {function_name}")
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId='AllowBedrockInvoke',
            Action='lambda:InvokeFunction',
            Principal='bedrock.amazonaws.com',
            SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/{agent_id}"
        )
        logger.info("Permission added successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            logger.info("Permission already exists")
        else:
            raise


def deploy_all() -> Dict[str, Any]:
    """Deploy all Lambda functions."""
    logger.info("Starting Lambda deployment...")
    
    results = {}
    
    # Load agent config
    with open('bedrock_agent_config.json', 'r') as f:
        config = json.load(f)
    
    orchestrator_agent_id = config['orchestrator_agent']['agentId']
    role_agent_id = config['role_agent']['agentId']
    
    # Deploy Action Group Lambda
    logger.info("\n=== Deploying Action Group Lambda ===")
    action_role_arn = create_lambda_role('VideoProcessingActionGroupRole', 'action-group')
    
    action_zip = create_deployment_package(
        'video-processing-action-group',
        'action_group_lambda.py',
        include_deps=True
    )
    
    action_env = {
        'DEEPGRAM_API_KEY': os.environ.get('DEEPGRAM_API_KEY', 'REPLACE_ME'),
        'DEFAULT_ROLE': 'general',
        'ROLE_AGENT_ID': role_agent_id,
        'LOG_LEVEL': 'INFO'
    }
    
    action_arn = create_or_update_lambda(
        'video-processing-action-group',
        'action_group_lambda.lambda_handler',
        action_role_arn,
        action_zip,
        action_env,
        timeout=600,
        memory=3008
    )
    
    add_bedrock_permission('video-processing-action-group', orchestrator_agent_id)
    
    results['action_group_lambda'] = {
        'arn': action_arn,
        'role_arn': action_role_arn
    }
    
    # Deploy Orchestrator Lambda
    logger.info("\n=== Deploying Orchestrator Lambda ===")
    orchestrator_role_arn = create_lambda_role('VideoProcessingOrchestratorRole', 'orchestrator')
    
    orchestrator_zip = create_deployment_package(
        'video-processing-orchestrator',
        'orchestrator_lambda.py',
        include_deps=False
    )
    
    orchestrator_env = {
        'ORCHESTRATOR_AGENT_ID': orchestrator_agent_id,
        'ORCHESTRATOR_ALIAS_ID': 'TSTALIASID',
        'LOG_LEVEL': 'INFO'
    }
    
    orchestrator_arn = create_or_update_lambda(
        'video-processing-orchestrator',
        'orchestrator_lambda.lambda_handler',
        orchestrator_role_arn,
        orchestrator_zip,
        orchestrator_env,
        timeout=600,
        memory=512
    )
    
    results['orchestrator_lambda'] = {
        'arn': orchestrator_arn,
        'role_arn': orchestrator_role_arn
    }
    
    # Update config
    config['lambda_functions'] = results
    with open('bedrock_agent_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info("\n=== Deployment Complete ===")
    return results


if __name__ == "__main__":
    try:
        results = deploy_all()
        
        print("\n" + "="*60)
        print("LAMBDA DEPLOYMENT COMPLETE")
        print("="*60)
        print(f"\nAction Group Lambda ARN:")
        print(f"  {results['action_group_lambda']['arn']}")
        print(f"\nOrchestrator Lambda ARN:")
        print(f"  {results['orchestrator_lambda']['arn']}")
        print("\nNext steps:")
        print("1. Configure action group: python configure_orchestrator_agent.py <action_lambda_arn>")
        print("2. Test the workflow")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        exit(1)
