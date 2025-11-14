"""
AWS Lambda handler for processing video files from S3 using Amazon Bedrock models.

This module provides functionality to:
- Create S3 buckets for video storage
- Retrieve video files from S3
- Invoke Bedrock models with video data
- Handle errors and return structured responses
"""

import json
import base64
import logging
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError, BotoCoreError

# Configure logging for CloudWatch integration
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS service clients
s3_client = boto3.client('s3')
# bedrock_runtime_client = boto3.client('bedrock-runtime')  # TODO: Enable when implementing Bedrock integration

def create_s3_bucket(bucket_name: str, region: str) -> Dict[str, Any]:
    """
    Create an S3 bucket with the specified name and region.
    
    Args:
        bucket_name: Unique name for the S3 bucket
        region: AWS region where the bucket should be created
        
    Returns:
        Dictionary containing:
            - success: Boolean indicating if bucket was created successfully
            - message: Status message
            - bucket_name: Name of the bucket (if successful)
            - error: Error details (if failed)
    """
    try:
        # For us-east-1, CreateBucketConfiguration should not be specified
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        
        logger.info(f"Successfully created S3 bucket: {bucket_name} in region: {region}")
        return {
            'success': True,
            'message': f'Bucket {bucket_name} created successfully',
            'bucket_name': bucket_name
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'BucketAlreadyExists':
            logger.warning(f"Bucket {bucket_name} already exists and is owned by another account")
            return {
                'success': False,
                'message': f'Bucket {bucket_name} already exists and is owned by another account',
                'error': error_code
            }
        elif error_code == 'BucketAlreadyOwnedByYou':
            logger.info(f"Bucket {bucket_name} already exists and is owned by you")
            return {
                'success': True,
                'message': f'Bucket {bucket_name} already exists and is owned by you',
                'bucket_name': bucket_name
            }
        else:
            logger.error(f"Error creating bucket {bucket_name}: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to create bucket: {str(e)}',
                'error': error_code
            }
            
    except BotoCoreError as e:
        logger.error(f"BotoCore error creating bucket {bucket_name}: {str(e)}")
        return {
            'success': False,
            'message': f'AWS service error: {str(e)}',
            'error': 'BotoCoreError'
        }
        
    except Exception as e:
        logger.error(f"Unexpected error creating bucket {bucket_name}: {str(e)}")
        return {
            'success': False,
            'message': f'Unexpected error: {str(e)}',
            'error': 'UnexpectedError'
        }


def get_video_from_s3(bucket_name: str, object_key: str) -> bytes:
    """
    Retrieve a video file from S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket containing the video
        object_key: S3 object key (path) to the video file
        
    Returns:
        Video file content as bytes
        
    Raises:
        ClientError: If the video file doesn't exist (NoSuchKey) or access is denied (AccessDenied)
        Exception: For other unexpected errors
    """
    try:
        # Validate that the object exists before retrieving
        logger.info(f"Checking if video file exists: s3://{bucket_name}/{object_key}")
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
        
        # Retrieve the video file
        logger.info(f"Retrieving video file from S3: s3://{bucket_name}/{object_key}")
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        
        # Read the video content as bytes
        video_data = response['Body'].read()
        logger.info(f"Successfully retrieved video file: {len(video_data)} bytes")
        
        return video_data
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'NoSuchKey':
            logger.error(f"Video file not found: s3://{bucket_name}/{object_key}")
            raise ClientError(
                {
                    'Error': {
                        'Code': 'NoSuchKey',
                        'Message': f'Video file not found: {object_key}'
                    }
                },
                'GetObject'
            )
        elif error_code == '404':
            logger.error(f"Video file not found: s3://{bucket_name}/{object_key}")
            raise ClientError(
                {
                    'Error': {
                        'Code': 'NoSuchKey',
                        'Message': f'Video file not found: {object_key}'
                    }
                },
                'GetObject'
            )
        elif error_code == 'AccessDenied':
            logger.error(f"Access denied to video file: s3://{bucket_name}/{object_key}")
            raise ClientError(
                {
                    'Error': {
                        'Code': 'AccessDenied',
                        'Message': f'Access denied to video file: {object_key}'
                    }
                },
                'GetObject'
            )
        else:
            logger.error(f"Error retrieving video from S3: {str(e)}")
            raise
            
    except BotoCoreError as e:
        logger.error(f"BotoCore error retrieving video from S3: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error retrieving video from S3: {str(e)}")
        raise


# TODO: Uncomment and enable when implementing Bedrock integration
# def invoke_bedrock_model(video_data: bytes, model_id: str) -> Dict[str, Any]:
#     """
#     Invoke a Bedrock model with video data for analysis.
#     
#     Args:
#         video_data: Video file content as bytes
#         model_id: Bedrock model identifier (e.g., 'anthropic.claude-3-sonnet-20240229-v1:0')
#         
#     Returns:
#         Dictionary containing:
#             - success: Boolean indicating if invocation was successful
#             - response: Parsed model response (if successful)
#             - message: Status message
#             - error: Error details (if failed)
#     """
#     try:
#         # Prepare video data in base64 format for Bedrock
#         logger.info(f"Encoding video data for Bedrock model: {model_id}")
#         video_base64 = base64.b64encode(video_data).decode('utf-8')
#         
#         # Prepare the request body for Bedrock
#         # Note: The exact format depends on the model being used
#         # This example uses Claude 3 format with vision capabilities
#         request_body = {
#             "anthropic_version": "bedrock-2023-05-31",
#             "max_tokens": 1000,
#             "messages": [
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": "video",
#                             "source": {
#                                 "type": "base64",
#                                 "media_type": "video/mp4",
#                                 "data": video_base64
#                             }
#                         },
#                         {
#                             "type": "text",
#                             "text": "Please analyze this video."
#                         }
#                     ]
#                 }
#             ]
#         }
#         
#         logger.info(f"Invoking Bedrock model: {model_id}")
#         
#         # Invoke the Bedrock model
#         response = bedrock_runtime_client.invoke_model(
#             modelId=model_id,
#             contentType='application/json',
#             accept='application/json',
#             body=json.dumps(request_body)
#         )
#         
#         # Parse the response
#         response_body = json.loads(response['body'].read())
#         logger.info(f"Successfully invoked Bedrock model: {model_id}")
#         
#         return {
#             'success': True,
#             'response': response_body,
#             'message': 'Bedrock model invoked successfully'
#         }
#         
#     except ClientError as e:
#         error_code = e.response['Error']['Code']
#         
#         if error_code == 'ResourceNotFoundException':
#             logger.error(f"Bedrock model not found: {model_id}")
#             return {
#                 'success': False,
#                 'message': f'Bedrock model not found: {model_id}',
#                 'error': 'ModelNotFound'
#             }
#         elif error_code == 'ThrottlingException':
#             logger.error(f"Bedrock API throttling occurred for model: {model_id}")
#             return {
#                 'success': False,
#                 'message': f'Bedrock API request throttled. Please retry later.',
#                 'error': 'ThrottlingException'
#             }
#         elif error_code == 'ValidationException':
#             logger.error(f"Invalid input format for Bedrock model: {model_id}")
#             return {
#                 'success': False,
#                 'message': f'Invalid input format for Bedrock model: {str(e)}',
#                 'error': 'ValidationException'
#             }
#         elif error_code == 'AccessDeniedException':
#             logger.error(f"Access denied to Bedrock model: {model_id}")
#             return {
#                 'success': False,
#                 'message': f'Access denied to Bedrock model: {model_id}',
#                 'error': 'AccessDenied'
#             }
#         else:
#             logger.error(f"Error invoking Bedrock model: {str(e)}")
#             return {
#                 'success': False,
#                 'message': f'Failed to invoke Bedrock model: {str(e)}',
#                 'error': error_code
#             }
#             
#     except BotoCoreError as e:
#         logger.error(f"BotoCore error invoking Bedrock model: {str(e)}")
#         return {
#             'success': False,
#             'message': f'AWS service error: {str(e)}',
#             'error': 'BotoCoreError'
#         }
#         
#     except json.JSONDecodeError as e:
#         logger.error(f"Error parsing Bedrock response: {str(e)}")
#         return {
#             'success': False,
#             'message': f'Error parsing Bedrock response: {str(e)}',
#             'error': 'JSONDecodeError'
#         }
#         
#     except Exception as e:
#         logger.error(f"Unexpected error invoking Bedrock model: {str(e)}")
#         return {
#             'success': False,
#             'message': f'Unexpected error: {str(e)}',
#             'error': 'UnexpectedError'
#         }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function that orchestrates S3 bucket creation
    and video retrieval.
    
    Args:
        event: Lambda event containing:
            - bucket_name: S3 bucket name
            - video_key: S3 object key for video file
            - region: AWS region (optional, defaults to us-east-1)
        context: Lambda context object
        
    Returns:
        Dictionary containing:
            - statusCode: HTTP status code
            - body: JSON string with operation results
    """
    logger.info(f"Lambda handler invoked with event: {json.dumps(event)}")
    
    try:
        # Extract parameters from event
        bucket_name = event.get('bucket_name')
        video_key = event.get('video_key')
        region = event.get('region', 'us-east-1')
        
        # Validate required parameters
        if not bucket_name:
            logger.error("Missing required parameter: bucket_name")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'BadRequest',
                    'message': 'Missing required parameter: bucket_name'
                })
            }
        
        if not video_key:
            logger.error("Missing required parameter: video_key")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'BadRequest',
                    'message': 'Missing required parameter: video_key'
                })
            }
        
        logger.info(f"Processing video: s3://{bucket_name}/{video_key}")
        
        # Step 1: Create S3 bucket (or verify it exists)
        logger.info(f"Step 1: Creating/verifying S3 bucket: {bucket_name}")
        bucket_result = create_s3_bucket(bucket_name, region)
        
        if not bucket_result['success']:
            logger.error(f"Failed to create/verify bucket: {bucket_result['message']}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'bucket_created': False,
                    'video_processed': False,
                    'error': bucket_result.get('error', 'BucketCreationError'),
                    'message': bucket_result['message']
                })
            }
        
        logger.info(f"Bucket ready: {bucket_result['message']}")
        
        # Step 2: Retrieve video file from S3
        logger.info(f"Step 2: Retrieving video from S3: {video_key}")
        try:
            video_data = get_video_from_s3(bucket_name, video_key)
            logger.info(f"Successfully retrieved video: {len(video_data)} bytes")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Failed to retrieve video: {error_message}")
            
            status_code = 404 if error_code == 'NoSuchKey' else 403 if error_code == 'AccessDenied' else 500
            
            return {
                'statusCode': status_code,
                'body': json.dumps({
                    'bucket_created': bucket_result['success'],
                    'video_processed': False,
                    'error': error_code,
                    'message': error_message
                })
            }
        except Exception as e:
            logger.error(f"Unexpected error retrieving video: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'bucket_created': bucket_result['success'],
                    'video_processed': False,
                    'error': 'VideoRetrievalError',
                    'message': f'Failed to retrieve video: {str(e)}'
                })
            }
        
        # Step 3: Log that video was processed (Bedrock integration to be implemented later)
        logger.info(f"Video processed successfully: s3://{bucket_name}/{video_key} ({len(video_data)} bytes)")
        
        # Step 4: Build and return successful response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'bucket_created': bucket_result['success'],
                'video_processed': True,
                'video_size_bytes': len(video_data),
                'message': 'Video processed successfully'
            })
        }
        
    except KeyError as e:
        logger.error(f"Missing required event parameter: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'BadRequest',
                'message': f'Missing required parameter: {str(e)}'
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'InternalServerError',
                'message': f'An unexpected error occurred: {str(e)}'
            })
        }
