"""
Test Bedrock Agent directly without Lambda.
"""

import json
import uuid
import boto3

# Initialize client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-west-2')

# Agent IDs from config
ORCHESTRATOR_AGENT_ID = "OSU2VB3BLW"
ORCHESTRATOR_ALIAS_ID = "TSTALIASID"

# Your S3 path
bucket_name = "my-video-lambda-bucket"
video_key = "videoplayback.mp4"
user_prompt = "Summarize this video for a project manager"

# Generate session ID
session_id = f"test-{uuid.uuid4()}"

# Construct input
agent_input = f"""Process this video and provide a role-specific summary.

User Request: {user_prompt}

Video Location:
- Bucket: {bucket_name}
- Key: {video_key}

Please:
1. Determine the target role from my request
2. Retrieve and transcribe the video
3. Generate a summary tailored for that role"""

print(f"Invoking Orchestrator Agent: {ORCHESTRATOR_AGENT_ID}")
print(f"Session ID: {session_id}")
print(f"\nInput:\n{agent_input}\n")
print("="*60)

try:
    # Invoke agent
    response = bedrock_agent_runtime.invoke_agent(
        agentId=ORCHESTRATOR_AGENT_ID,
        agentAliasId=ORCHESTRATOR_ALIAS_ID,
        sessionId=session_id,
        inputText=agent_input
    )
    
    # Stream response
    print("\nAgent Response:")
    print("="*60)
    
    event_stream = response['completion']
    full_response = ""
    
    for event in event_stream:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                chunk_text = chunk['bytes'].decode('utf-8')
                full_response += chunk_text
                print(chunk_text, end='', flush=True)
    
    print("\n" + "="*60)
    print(f"\n✓ Complete! Total response: {len(full_response)} characters")
    
except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
