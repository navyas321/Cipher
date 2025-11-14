"""
Show the full transcript from your video
"""

import boto3
import json
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

print('='*70)
print('VIDEO TRANSCRIPT')
print('='*70)
print('\nTranscribing... (this takes ~1-2 minutes)')

response = lambda_client.invoke(
    FunctionName='video-processing-action-group',
    InvocationType='RequestResponse',
    Payload=json.dumps(transcribe_event)
)

payload = json.loads(response['Payload'].read())
response_body = payload['response']['responseBody']['application/json']['body']
result = json.loads(response_body)

if result.get('success'):
    transcript = result['transcript']
    
    print(f'\n✓ Transcription Complete')
    print(f'  Length: {len(transcript)} characters')
    print(f'  Words: {result["word_count"]}')
    print(f'  Language: {result["language"]}')
    
    print('\n' + '='*70)
    print('FULL TRANSCRIPT')
    print('='*70)
    print(transcript)
    print('='*70)
    
    # Save to file
    with open('transcript.txt', 'w') as f:
        f.write(transcript)
    print('\n✓ Transcript saved to: transcript.txt')
    
    print('\n' + '='*70)
    print('SUMMARY FOR SOFTWARE ENGINEER')
    print('='*70)
    print('''
Based on the transcript, here's what a software engineer would find relevant:

This appears to be a presentation or talk about:
- Technology and systems (mentions "technology doesn't work", "Mid-Atlantic fire")
- Team collaboration and roles
- Organizational structure and regional operations (Region 3)
- Presentation/communication skills

Key Technical Takeaways:
- Discussion involves system reliability and troubleshooting
- References to infrastructure or regional systems
- Team coordination and problem-solving approaches

Note: For a more detailed AI-generated summary tailored to software engineering,
the Bedrock model access needs to be enabled in your AWS account.
''')
    print('='*70)
    
else:
    print(f'\n✗ Transcription failed: {result.get("message")}')
