"""
Test S3 retrieval action.
"""

import json
import boto3

lambda_client = boto3.client('lambda', region_name='us-west-2')

# Test retrieve video action
event = {
    'actionGroup': 'video-processing-actions',
    'apiPath': '/retrieve_video_from_s3',
    'httpMethod': 'POST',
    'parameters': [
        {'name': 'bucket_name', 'value': 'my-video-lambda-bucket'},
        {'name': 'video_key', 'value': 'videos/videoplayback.mp4'}
    ]
}

print("Testing Action Group Lambda - Retrieve Video from S3")
print("="*60)
print(f"Bucket: my-video-lambda-bucket")
print(f"Key: videos/videoplayback.mp4")
print("="*60)

try:
    response = lambda_client.invoke(
        FunctionName='video-processing-action-group',
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    payload = json.loads(response['Payload'].read())
    print(f"\nLambda Status: {response['StatusCode']}")
    
    # Parse the action response
    if 'response' in payload:
        response_body = payload['response']['responseBody']['application/json']['body']
        result = json.loads(response_body)
        
        if result.get('success'):
            print("\n" + "="*60)
            print("✓ VIDEO RETRIEVAL SUCCESSFUL")
            print("="*60)
            print(f"\nVideo Size: {result['video_size_bytes']:,} bytes ({result['video_size_bytes']/1024/1024:.2f} MB)")
            print(f"Bucket: {result['bucket_name']}")
            print(f"Key: {result['video_key']}")
            print(f"Message: {result['message']}")
        else:
            print("\n" + "="*60)
            print("✗ VIDEO RETRIEVAL FAILED")
            print("="*60)
            print(f"Error: {result.get('error')}")
            print(f"Message: {result.get('message')}")
    
except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
