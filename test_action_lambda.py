"""
Test the action group Lambda directly.
"""

import json
import boto3

lambda_client = boto3.client('lambda', region_name='us-west-2')

# Test transcribe action
event = {
    'actionGroup': 'video-processing-actions',
    'apiPath': '/transcribe_video',
    'httpMethod': 'POST',
    'parameters': [
        {'name': 'bucket_name', 'value': 'my-video-lambda-bucket'},
        {'name': 'video_key', 'value': 'videos/videoplayback.mp4'}
    ]
}

print("Testing Action Group Lambda - Transcribe Video")
print("="*60)
print(f"Event: {json.dumps(event, indent=2)}")
print("="*60)

try:
    response = lambda_client.invoke(
        FunctionName='video-processing-action-group',
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    payload = json.loads(response['Payload'].read())
    print(f"\nLambda Status: {response['StatusCode']}")
    print(f"\nResponse:")
    print(json.dumps(payload, indent=2))
    
    # Parse the action response
    if 'response' in payload:
        response_body = payload['response']['responseBody']['application/json']['body']
        result = json.loads(response_body)
        
        if result.get('success'):
            print("\n" + "="*60)
            print("✓ TRANSCRIPTION SUCCESSFUL")
            print("="*60)
            print(f"\nTranscript Preview (first 500 chars):")
            print(result['transcript'][:500] + "...")
            print(f"\nWord Count: {result['word_count']}")
            print(f"Duration: {result['duration']} seconds")
            print(f"Language: {result['language']}")
            print(f"Confidence: {result['confidence']:.2%}")
        else:
            print("\n" + "="*60)
            print("✗ TRANSCRIPTION FAILED")
            print("="*60)
            print(f"Error: {result.get('error')}")
            print(f"Message: {result.get('message')}")
    
except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
