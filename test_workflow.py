"""
Test the complete video processing workflow.
"""

import json
import logging
import sys

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

lambda_client = boto3.client('lambda')


def test_workflow(bucket_name: str, video_key: str, user_prompt: str) -> None:
    """
    Test the complete workflow by invoking orchestrator Lambda.
    
    Args:
        bucket_name: S3 bucket containing video
        video_key: S3 key for video file
        user_prompt: User prompt with role information
    """
    logger.info("Testing video processing workflow...")
    logger.info(f"Bucket: {bucket_name}")
    logger.info(f"Video: {video_key}")
    logger.info(f"Prompt: {user_prompt}")
    
    # Prepare event
    event = {
        'bucket_name': bucket_name,
        'video_key': video_key,
        'user_prompt': user_prompt
    }
    
    try:
        # Invoke orchestrator Lambda
        logger.info("\nInvoking orchestrator Lambda...")
        response = lambda_client.invoke(
            FunctionName='video-processing-orchestrator',
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        # Parse response
        payload = json.loads(response['Payload'].read())
        logger.info(f"\nLambda Response Status: {response['StatusCode']}")
        
        # Parse body
        body = json.loads(payload['body'])
        
        if body.get('success'):
            print("\n" + "="*60)
            print("✓ WORKFLOW TEST SUCCESSFUL")
            print("="*60)
            print(f"\nSummary:")
            print(body['summary'])
            print(f"\nSession ID: {body.get('session_id')}")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("✗ WORKFLOW TEST FAILED")
            print("="*60)
            print(f"Error: {body.get('error')}")
            print(f"Message: {body.get('message')}")
            print("="*60)
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python test_workflow.py <bucket_name> <video_key> <user_prompt>")
        print('Example: python test_workflow.py my-bucket video.mp4 "Summarize for a project manager"')
        sys.exit(1)
    
    bucket_name = sys.argv[1]
    video_key = sys.argv[2]
    user_prompt = sys.argv[3]
    
    test_workflow(bucket_name, video_key, user_prompt)
