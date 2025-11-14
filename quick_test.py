import boto3
import json
import time
import botocore.config

lambda_client = boto3.client('lambda', region_name='us-west-2', config=botocore.config.Config(read_timeout=180))

transcribe_event = {
    'actionGroup': 'video-processing-actions',
    'apiPath': '/transcribe_video',
    'httpMethod': 'POST',
    'parameters': [
        {'name': 'bucket_name', 'value': 'my-video-lambda-bucket'},
        {'name': 'video_key', 'value': 'videos/videoplayback.mp4'}
    ]
}

print('Transcribing video (1-2 minutes)...')
start = time.time()

response = lambda_client.invoke(
    FunctionName='video-processing-action-group',
    InvocationType='RequestResponse',
    Payload=json.dumps(transcribe_event)
)

elapsed = time.time() - start
print(f'Completed in {elapsed:.1f}s')

payload = json.loads(response['Payload'].read())
response_body = payload['response']['responseBody']['application/json']['body']
result = json.loads(response_body)

if result.get('success'):
    print(f"\n✓ SUCCESS!")
    print(f"Transcript: {len(result['transcript'])} chars")
    print(f"\nPreview:\n{result['transcript'][:500]}...")
else:
    print(f"\n✗ Failed: {result.get('message')}")
