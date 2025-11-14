"""
Test transcription asynchronously
"""

import json
import boto3
import time

lambda_client = boto3.client('lambda', region_name='us-west-2')

bucket_name = "my-video-lambda-bucket"
video_key = "videos/videoplayback.mp4"

transcribe_event = {
    'actionGroup': 'video-processing-actions',
    'apiPath': '/transcribe_video',
    'httpMethod': 'POST',
    'parameters': [
        {'name': 'bucket_name', 'value': bucket_name},
        {'name': 'video_key', 'value': video_key}
    ]
}

print("Starting async transcription...")
print("This will take 1-2 minutes. The Lambda will process in the background.")
print("\nYou can check CloudWatch Logs for progress:")
print("  aws logs tail /aws/lambda/video-processing-action-group --follow")

response = lambda_client.invoke(
    FunctionName='video-processing-action-group',
    InvocationType='Event',  # Async
    Payload=json.dumps(transcribe_event)
)

print(f"\n✓ Transcription job started (Status: {response['StatusCode']})")
print("\nThe transcription is running in the background.")
print("Check the Lambda logs in AWS Console to see the result.")
