"""
Final test with your prompt: "summarize this video so that all the relevant information is gathered as a software engineer"
"""

import json
import boto3
import time
import botocore.config

lambda_client = boto3.client('lambda', region_name='us-west-2', config=botocore.config.Config(read_timeout=180))

user_prompt = "summarize this video so that all the relevant information is gathered as a software engineer"
bucket_name = "my-video-lambda-bucket"
video_key = "videos/videoplayback.mp4"

print("="*70)
print("FINAL WORKFLOW TEST")
print("="*70)
print(f"\nPrompt: {user_prompt}")
print(f"Video: s3://{bucket_name}/{video_key}")
print("\n" + "="*70)

# Step 1: Transcribe
print("\n[1/2] Transcribing video (this takes ~1-2 minutes)...")
print("-"*70)

transcribe_event = {
    'actionGroup': 'video-processing-actions',
    'apiPath': '/transcribe_video',
    'httpMethod': 'POST',
    'parameters': [
        {'name': 'bucket_name', 'value': bucket_name},
        {'name': 'video_key', 'value': video_key}
    ]
}

start_time = time.time()

try:
    response = lambda_client.invoke(
        FunctionName='video-processing-action-group',
        InvocationType='RequestResponse',
        Payload=json.dumps(transcribe_event)
    )
    
    payload = json.loads(response['Payload'].read())
    response_body = payload['response']['responseBody']['application/json']['body']
    transcribe_result = json.loads(response_body)
    
    elapsed = time.time() - start_time
    
    if transcribe_result.get('success'):
        print(f"✓ Transcription Complete ({elapsed:.1f}s)")
        print(f"  Transcript length: {len(transcribe_result['transcript'])} characters")
        print(f"  Word count: {transcribe_result['word_count']}")
        print(f"\n  Preview:")
        print(f"  {transcribe_result['transcript'][:400]}...")
        transcript = transcribe_result['transcript']
    else:
        print(f"✗ Transcription Failed: {transcribe_result.get('message')}")
        transcript = None
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
    transcript = None

# Step 2: Generate Summary
if transcript:
    print("\n[2/2] Generating software engineer-focused summary...")
    print("-"*70)
    
    # Use Claude directly to generate summary
    bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-west-2')
    
    prompt = f"""You are analyzing a video transcript for a software engineer. 

User Request: {user_prompt}

Video Transcript:
{transcript}

Please provide a comprehensive summary that focuses on:
- Technical concepts and implementations
- Code examples or algorithms mentioned
- Best practices and patterns
- Tools, frameworks, or technologies discussed
- Key takeaways for software engineers

Format your response as a clear, structured summary."""
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 2000,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            })
        )
        
        result = json.loads(response['body'].read())
        summary = result['content'][0]['text']
        
        print("✓ Summary Generated")
        print("\n" + "="*70)
        print("SOFTWARE ENGINEER-FOCUSED SUMMARY")
        print("="*70)
        print(summary)
        print("="*70)
        
    except Exception as e:
        print(f"✗ Summary generation failed: {str(e)}")
        print(f"  Note: Your IAM role may need bedrock:InvokeModel permission")
else:
    print("\n✗ Cannot generate summary - transcription failed")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
