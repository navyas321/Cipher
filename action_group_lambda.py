"""
Action Group Lambda function for Bedrock Agent.
Handles video retrieval, transcription, and role determination actions.
"""

import json
import logging
import os
import tempfile
import uuid
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize AWS clients
s3_client = boto3.client('s3')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Environment variables
DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY')
DEFAULT_ROLE = os.environ.get('DEFAULT_ROLE', 'general')
ROLE_AGENT_ID = os.environ.get('ROLE_AGENT_ID')


def get_video_from_s3(bucket_name: str, object_key: str) -> bytes:
    """
    Retrieve a video file from S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket
        object_key: S3 object key
        
    Returns:
        Video file content as bytes
    """
    try:
        logger.info(f"Retrieving video from S3: s3://{bucket_name}/{object_key}")
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        video_data = response['Body'].read()
        logger.info(f"Successfully retrieved video: {len(video_data)} bytes")
        return video_data
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"S3 error: {error_code}")
        raise


def retrieve_video_from_s3_action(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Action: Retrieve video file from S3.
    
    Args:
        parameters: Action parameters containing bucket_name and video_key
        
    Returns:
        Action response with video data or error
    """
    try:
        bucket_name = parameters.get('bucket_name')
        video_key = parameters.get('video_key')
        
        if not bucket_name or not video_key:
            return {
                'success': False,
                'error': 'MissingParameters',
                'message': 'bucket_name and video_key are required'
            }
        
        video_data = get_video_from_s3(bucket_name, video_key)
        
        return {
            'success': True,
            'video_size_bytes': len(video_data),
            'bucket_name': bucket_name,
            'video_key': video_key,
            'message': 'Video retrieved successfully'
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'NoSuchKey':
            return {
                'success': False,
                'error': 'NoSuchKey',
                'message': f'Video file not found: {video_key}'
            }
        elif error_code == 'AccessDenied':
            return {
                'success': False,
                'error': 'AccessDenied',
                'message': f'Access denied to video file: {video_key}'
            }
        else:
            return {
                'success': False,
                'error': error_code,
                'message': f'S3 error: {str(e)}'
            }
    
    except Exception as e:
        logger.error(f"Unexpected error in retrieve_video_from_s3: {str(e)}")
        return {
            'success': False,
            'error': 'UnexpectedError',
            'message': str(e)
        }


def transcribe_video_action(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Action: Transcribe video using AWS Transcribe (fallback from Deepgram).
    
    Args:
        parameters: Action parameters containing bucket_name and video_key
        
    Returns:
        Action response with transcription or error
    """
    try:
        bucket_name = parameters.get('bucket_name')
        video_key = parameters.get('video_key')
        
        if not bucket_name or not video_key:
            return {
                'success': False,
                'error': 'MissingParameters',
                'message': 'bucket_name and video_key are required'
            }
        
        # Use AWS Transcribe as fallback since FFmpeg is not available
        transcribe_client = boto3.client('transcribe')
        
        # Generate unique job name
        import time
        job_name = f"video-transcribe-{int(time.time())}"
        
        # Start transcription job
        logger.info(f"Starting AWS Transcribe job: {job_name}")
        
        media_uri = f"s3://{bucket_name}/{video_key}"
        
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            MediaFormat='mp4',
            LanguageCode='en-US',
            Settings={
                'ShowSpeakerLabels': False
            }
        )
        
        # Wait for job to complete (with timeout)
        max_wait = 300  # 5 minutes
        wait_time = 0
        
        while wait_time < max_wait:
            status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = status['TranscriptionJob']['TranscriptionJobStatus']
            
            if job_status == 'COMPLETED':
                # Get transcript
                transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                
                # Download transcript
                import urllib.request
                with urllib.request.urlopen(transcript_uri) as response:
                    transcript_data = json.loads(response.read())
                
                transcript_text = transcript_data['results']['transcripts'][0]['transcript']
                
                # Clean up job
                try:
                    transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
                except:
                    pass
                
                logger.info(f"Transcription complete: {len(transcript_text)} characters")
                
                return {
                    'success': True,
                    'transcript': transcript_text,
                    'word_count': len(transcript_text.split()),
                    'duration': 0,  # Not available from Transcribe
                    'language': 'en-US',
                    'confidence': 0.95,
                    'message': 'Video transcribed successfully using AWS Transcribe'
                }
            
            elif job_status == 'FAILED':
                failure_reason = status['TranscriptionJob'].get('FailureReason', 'Unknown')
                return {
                    'success': False,
                    'error': 'TranscriptionFailed',
                    'message': f'AWS Transcribe failed: {failure_reason}'
                }
            
            # Wait and retry
            time.sleep(10)
            wait_time += 10
            logger.info(f"Waiting for transcription... ({wait_time}s)")
        
        return {
            'success': False,
            'error': 'TranscriptionTimeout',
            'message': 'Transcription job timed out after 5 minutes'
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        return {
            'success': False,
            'error': error_code,
            'message': f'AWS error: {str(e)}'
        }
    
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return {
            'success': False,
            'error': 'TranscriptionError',
            'message': str(e)
        }


def invoke_role_agent_action(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Action: Invoke Role Determination Agent.
    
    Args:
        parameters: Action parameters containing user_prompt
        
    Returns:
        Action response with role information or error
    """
    try:
        user_prompt = parameters.get('user_prompt')
        
        if not user_prompt:
            return {
                'success': False,
                'error': 'MissingParameters',
                'message': 'user_prompt is required'
            }
        
        if not ROLE_AGENT_ID:
            logger.warning("ROLE_AGENT_ID not configured, using default role")
            return {
                'success': True,
                'role': DEFAULT_ROLE,
                'context': 'Default role used (agent not configured)',
                'confidence': 0.0,
                'fallback': True
            }
        
        # Generate session ID
        session_id = f"role-session-{uuid.uuid4()}"
        
        logger.info(f"Invoking Role Determination Agent: {ROLE_AGENT_ID}")
        logger.info(f"User prompt: {user_prompt}")
        
        # Invoke Role Determination Agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=ROLE_AGENT_ID,
            agentAliasId='TSTALIASID',
            sessionId=session_id,
            inputText=f"Extract role from: {user_prompt}"
        )
        
        # Stream and parse response
        event_stream = response['completion']
        full_response = ""
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    full_response += chunk['bytes'].decode('utf-8')
        
        logger.info(f"Role agent response: {full_response}")
        
        # Try to parse JSON response
        try:
            role_info = json.loads(full_response)
            return {
                'success': True,
                'role': role_info.get('role', DEFAULT_ROLE),
                'context': role_info.get('context', ''),
                'confidence': role_info.get('confidence', 0.5),
                'fallback': role_info.get('fallback', False)
            }
        except json.JSONDecodeError:
            # If not JSON, extract role from text
            logger.warning("Could not parse JSON response, extracting role from text")
            return {
                'success': True,
                'role': DEFAULT_ROLE,
                'context': full_response,
                'confidence': 0.3,
                'fallback': True
            }
        
    except ClientError as e:
        logger.error(f"Bedrock error invoking role agent: {str(e)}")
        return {
            'success': True,
            'role': DEFAULT_ROLE,
            'context': f'Error invoking agent: {str(e)}',
            'confidence': 0.0,
            'fallback': True
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in invoke_role_agent: {str(e)}")
        return {
            'success': True,
            'role': DEFAULT_ROLE,
            'context': f'Error: {str(e)}',
            'confidence': 0.0,
            'fallback': True
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Bedrock Agent action group.
    
    Args:
        event: Bedrock Agent action group event
        context: Lambda context
        
    Returns:
        Action group response
    """
    logger.info(f"Action group event: {json.dumps(event)}")
    
    try:
        # Parse Bedrock Agent action group event
        action_group = event.get('actionGroup')
        api_path = event.get('apiPath')
        http_method = event.get('httpMethod')
        parameters = event.get('parameters', [])
        
        # Convert parameters list to dict
        params_dict = {}
        for param in parameters:
            params_dict[param['name']] = param['value']
        
        logger.info(f"Action: {api_path}, Method: {http_method}")
        logger.info(f"Parameters: {params_dict}")
        
        # Route to appropriate action handler
        if api_path == '/retrieve_video_from_s3':
            result = retrieve_video_from_s3_action(params_dict)
        elif api_path == '/transcribe_video':
            result = transcribe_video_action(params_dict)
        elif api_path == '/invoke_role_agent':
            result = invoke_role_agent_action(params_dict)
        else:
            result = {
                'success': False,
                'error': 'UnknownAction',
                'message': f'Unknown action: {api_path}'
            }
        
        # Format response for Bedrock Agent
        response = {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': action_group,
                'apiPath': api_path,
                'httpMethod': http_method,
                'httpStatusCode': 200 if result.get('success') else 400,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(result)
                    }
                }
            }
        }
        
        logger.info(f"Action response: {json.dumps(response)}")
        return response
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', 'unknown'),
                'apiPath': event.get('apiPath', 'unknown'),
                'httpMethod': event.get('httpMethod', 'POST'),
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'success': False,
                            'error': 'InternalError',
                            'message': str(e)
                        })
                    }
                }
            }
        }
