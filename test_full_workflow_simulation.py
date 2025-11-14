"""
Simulate the full workflow by calling Lambda actions directly.
This bypasses the Bedrock Agent orchestration to test the components.
"""

import json
import boto3

lambda_client = boto3.client('lambda', region_name='us-west-2')

print("="*60)
print("SIMULATING FULL VIDEO PROCESSING WORKFLOW")
print("="*60)

user_prompt = "summarize this video so that all the relevant information is gathered as a software engineer"
bucket_name = "my-video-lambda-bucket"
video_key = "videos/videoplayback.mp4"

print(f"\nUser Prompt: {user_prompt}")
print(f"Video: s3://{bucket_name}/{video_key}")
print("\n" + "="*60)

# Step 1: Determine Role
print("\n[Step 1/4] Determining role from prompt...")
print("-"*60)

role_event = {
    'actionGroup': 'video-processing-actions',
    'apiPath': '/invoke_role_agent',
    'httpMethod': 'POST',
    'parameters': [
        {'name': 'user_prompt', 'value': user_prompt}
    ]
}

try:
    response = lambda_client.invoke(
        FunctionName='video-processing-action-group',
        InvocationType='RequestResponse',
        Payload=json.dumps(role_event)
    )
    
    payload = json.loads(response['Payload'].read())
    response_body = payload['response']['responseBody']['application/json']['body']
    role_result = json.loads(response_body)
    
    if role_result.get('success'):
        print(f"✓ Role Determined: {role_result['role']}")
        print(f"  Context: {role_result['context']}")
        print(f"  Confidence: {role_result['confidence']:.2%}")
        detected_role = role_result['role']
    else:
        print(f"✗ Role determination failed, using default")
        detected_role = "general"
        
except Exception as e:
    print(f"✗ Error in role determination: {str(e)}")
    detected_role = "general"

# Step 2: Retrieve Video
print("\n[Step 2/4] Retrieving video from S3...")
print("-"*60)

retrieve_event = {
    'actionGroup': 'video-processing-actions',
    'apiPath': '/retrieve_video_from_s3',
    'httpMethod': 'POST',
    'parameters': [
        {'name': 'bucket_name', 'value': bucket_name},
        {'name': 'video_key', 'value': video_key}
    ]
}

try:
    response = lambda_client.invoke(
        FunctionName='video-processing-action-group',
        InvocationType='RequestResponse',
        Payload=json.dumps(retrieve_event)
    )
    
    payload = json.loads(response['Payload'].read())
    response_body = payload['response']['responseBody']['application/json']['body']
    retrieve_result = json.loads(response_body)
    
    if retrieve_result.get('success'):
        print(f"✓ Video Retrieved: {retrieve_result['video_size_bytes']:,} bytes ({retrieve_result['video_size_bytes']/1024/1024:.2f} MB)")
        video_retrieved = True
    else:
        print(f"✗ Video retrieval failed: {retrieve_result.get('message')}")
        video_retrieved = False
        
except Exception as e:
    print(f"✗ Error retrieving video: {str(e)}")
    video_retrieved = False

# Step 3: Transcribe Video
print("\n[Step 3/4] Transcribing video...")
print("-"*60)

transcribe_event = {
    'actionGroup': 'video-processing-actions',
    'apiPath': '/transcribe_video',
    'httpMethod': 'POST',
    'parameters': [
        {'name': 'bucket_name', 'value': bucket_name},
        {'name': 'video_key', 'value': video_key}
    ]
}

try:
    response = lambda_client.invoke(
        FunctionName='video-processing-action-group',
        InvocationType='RequestResponse',
        Payload=json.dumps(transcribe_event)
    )
    
    payload = json.loads(response['Payload'].read())
    response_body = payload['response']['responseBody']['application/json']['body']
    transcribe_result = json.loads(response_body)
    
    if transcribe_result.get('success'):
        print(f"✓ Video Transcribed Successfully")
        print(f"  Duration: {transcribe_result['duration']} seconds")
        print(f"  Word Count: {transcribe_result['word_count']}")
        print(f"  Language: {transcribe_result['language']}")
        print(f"  Confidence: {transcribe_result['confidence']:.2%}")
        print(f"\n  Transcript Preview (first 300 chars):")
        print(f"  {transcribe_result['transcript'][:300]}...")
        transcript = transcribe_result['transcript']
        transcription_success = True
    else:
        print(f"✗ Transcription failed: {transcribe_result.get('message')}")
        print(f"  Error: {transcribe_result.get('error')}")
        transcript = None
        transcription_success = False
        
except Exception as e:
    print(f"✗ Error transcribing video: {str(e)}")
    transcript = None
    transcription_success = False

# Step 4: Generate Summary (simulated - would be done by Orchestrator Agent)
print("\n[Step 4/4] Generating role-specific summary...")
print("-"*60)

if transcription_success and transcript:
    print(f"✓ Would generate summary for role: {detected_role}")
    print(f"  The Orchestrator Agent would use Claude 3.5 Sonnet to:")
    print(f"  1. Analyze the transcript ({len(transcript)} characters)")
    print(f"  2. Extract information relevant to a {detected_role}")
    print(f"  3. Format it as a professional summary")
    print(f"\n  Note: This step requires the Bedrock Agent to be invoked,")
    print(f"  which needs additional IAM permissions in your AWS account.")
else:
    print(f"✗ Cannot generate summary - transcription failed")
    print(f"  Issue: Deepgram SDK dependencies not properly installed in Lambda")
    print(f"  Solution: Deploy Lambda with a layer containing compiled dependencies")

# Final Summary
print("\n" + "="*60)
print("WORKFLOW SIMULATION COMPLETE")
print("="*60)

print(f"\n✓ Components Working:")
print(f"  - Role Determination: {'✓' if role_result.get('success') else '✗'}")
print(f"  - S3 Video Retrieval: {'✓' if video_retrieved else '✗'}")
print(f"  - Video Transcription: {'✗ (needs Deepgram API key + dependencies)'}")
print(f"  - Summary Generation: {'⏸ (blocked by transcription)'}")

print(f"\n📋 Next Steps to Complete:")
print(f"  1. Add Deepgram API key to Lambda environment")
print(f"  2. Deploy Lambda with proper Python dependencies layer")
print(f"  3. Add bedrock:InvokeAgent permission to your IAM role")
print(f"  4. Then run: python test_direct.py")

print("\n" + "="*60)
