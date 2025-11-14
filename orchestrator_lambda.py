"""
Main Lambda handler that invokes Bedrock Orchestrator Agent.
"""

import json
import logging
import os
import uuid
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize Bedrock Agent Runtime client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Environment variables
ORCHESTRATOR_AGENT_ID = os.environ.get('ORCHESTRATOR_AGENT_ID')
ORCHESTRATOR_ALIAS_ID = os.environ.get('ORCHESTRATOR_ALIAS_ID', 'TSTALIASID')


def invoke_orchestrator_agent(user_prompt: str, bucket_name: str, video_key: str) -> Dict[str, Any]:
    """
    Invoke Bedrock Orchestrator Agent.
    
    Args:
        user_prompt: User's prompt with role information
        bucket_name: S3 bucket name
        video_key: S3 object key for video
        
    Returns:
        Agent response with summary and metadata
    """
    if not ORCHESTRATOR_AGENT_ID:
        raise ValueError("ORCHESTRATOR_AGENT_ID environment variable not set")
    
    # Generate unique session ID
    session_id = f"session-{uuid.uuid4()}"
    
    # Construct input for agent
    agent_input = f"""Process this video and provide a role-specific summary.

User Request: {user_prompt}

Video Location:
- Bucket: {bucket_name}
- Key: {video_key}

Please:
1. Determine the target role from my request
2. Retrieve and transcribe the video
3. Generate a summary tailored for that role"""
    
    logger.info(f"Invoking Orchestrator Agent: {ORCHESTRATOR_AGENT_ID}")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Input: {agent_input}")
    
    try:
        # Invoke agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=ORCHESTRATOR_AGENT_ID,
            agentAliasId=ORCHESTRATOR_ALIAS_ID,
            sessionId=session_id,
            inputText=agent_input
        )
        
        # Stream and collect response
        event_stream = response['completion']
        full_response = ""
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    full_response += chunk_text
                    logger.info(f"Received chunk: {len(chunk_text)} bytes")
        
        logger.info(f"Complete response received: {len(full_response)} characters")
        
        return {
            'success': True,
            'summary': full_response,
            'session_id': session_id
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"Bedrock error: {error_code} - {str(e)}")
        
        return {
            'success': False,
            'error': error_code,
            'message': str(e)
        }
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        
        return {
            'success': False,
            'error': 'UnexpectedError',
            'message': str(e)
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler that orchestrates video processing via Bedrock Agent.
    
    Args:
        event: Lambda event containing user_prompt, bucket_name, video_key
        context: Lambda context
        
    Returns:
        Response with role-specific summary
    """
    logger.info(f"Lambda invoked with event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        user_prompt = event.get('user_prompt')
        bucket_name = event.get('bucket_name')
        video_key = event.get('video_key')
        
        # Validate required parameters
        if not user_prompt:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'BadRequest',
                    'message': 'Missing required parameter: user_prompt'
                })
            }
        
        if not bucket_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'BadRequest',
                    'message': 'Missing required parameter: bucket_name'
                })
            }
        
        if not video_key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'BadRequest',
                    'message': 'Missing required parameter: video_key'
                })
            }
        
        # Invoke orchestrator agent
        result = invoke_orchestrator_agent(user_prompt, bucket_name, video_key)
        
        if result['success']:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'summary': result['summary'],
                    'session_id': result['session_id'],
                    'video_key': video_key,
                    'bucket_name': bucket_name,
                    'message': 'Video processed successfully'
                })
            }
        else:
            status_code = 500
            if result.get('error') == 'ThrottlingException':
                status_code = 429
            elif result.get('error') == 'ValidationException':
                status_code = 400
            
            return {
                'statusCode': status_code,
                'body': json.dumps({
                    'success': False,
                    'error': result.get('error'),
                    'message': result.get('message')
                })
            }
        
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'ConfigurationError',
                'message': str(e)
            })
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'InternalServerError',
                'message': str(e)
            })
        }
