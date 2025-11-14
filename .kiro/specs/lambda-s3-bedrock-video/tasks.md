# Implementation Plan

- [x] 1. Set up Bedrock Agent infrastructure
  - Create Bedrock Orchestrator Agent with Claude 3.5 Sonnet foundation model (anthropic.claude-3-5-sonnet-20240620-v1:0)
  - Create Bedrock Role Determination Agent with Claude 3.5 Sonnet foundation model
  - Configure agent execution roles with necessary IAM permissions
  - Set up agent aliases for testing and production
  - _Requirements: 1.1, 2.1_

- [x] 2. Implement Action Group Lambda function
  - Create new Lambda function for action group handlers
  - Configure environment variables (DEEPGRAM_API_KEY, DEFAULT_ROLE)
  - Implement action handler routing logic to handle different action requests
  - Parse action group event structure from Bedrock Agent
  - Return responses in Bedrock Agent action group format
  - _Requirements: 1.3, 1.4, 1.5_

- [x] 2.1 Implement retrieve_video_from_s3 action
  - Use existing get_video_from_s3 function from lambda_handler.py
  - Add action schema definition for Bedrock Agent
  - Handle S3 errors (NoSuchKey, AccessDenied) and return structured responses
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 2.2 Implement transcribe_video action
  - Integrate video_summarization_tool module
  - Save video file temporarily for transcription
  - Call transcribe_video() function with video path
  - Parse and return transcription result with word-level timestamps
  - Clean up temporary video file after transcription
  - Handle Deepgram API errors and rate limiting
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 2.3 Implement invoke_role_agent action
  - Initialize Bedrock Agent Runtime client
  - Call InvokeAgent API with Role Determination Agent ID
  - Pass user prompt as inputText to role agent
  - Stream and parse role agent response chunks
  - Extract role and context from agent response (JSON format)
  - Return structured role information with confidence score
  - Handle cases where role cannot be determined (use default role from environment)
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2.4 Return summary generation parameters to Orchestrator Agent
  - Return transcription text and role information to Orchestrator Agent
  - Let Orchestrator Agent handle summary generation using its foundation model
  - Orchestrator Agent will use its Claude 3.5 Sonnet model to generate role-specific summary
  - No need for separate InvokeModel call - Bedrock Agent handles this internally
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 3. Configure Bedrock Orchestrator Agent
  - Define agent instruction prompt for workflow coordination and summary generation
  - Include instructions for generating role-specific summaries in agent prompt
  - Create action group schema with three actions (retrieve_video, transcribe_video, invoke_role_agent)
  - Link action group to Action Group Lambda function
  - Configure agent to invoke Role Determination Agent via agent-to-agent communication
  - Configure agent to generate summaries using its foundation model (no separate action needed)
  - Test agent-to-agent communication
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 5.1, 5.2, 5.3_

- [x] 4. Configure Bedrock Role Determination Agent
  - Define agent instruction prompt for role extraction
  - Configure to return JSON-formatted role information
  - Set up to work without action groups (pure LLM reasoning)
  - Test with various user prompt formats
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 5. Implement main Lambda handler
  - Create new lambda_handler function that invokes Bedrock Orchestrator Agent
  - Extract parameters from event (user_prompt, bucket_name, video_key)
  - Initialize Bedrock Agent Runtime client using boto3
  - Generate unique session ID for agent invocation
  - Call InvokeAgent API with Orchestrator Agent ID and session ID
  - Stream response chunks from agent using EventStream
  - Parse agent response to extract final summary
  - Build structured response with role, summary, and metadata
  - Handle top-level errors and return appropriate status codes
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 6. Deploy and configure Lambda functions
  - Package video_summarization_tool module with Action Group Lambda
  - Include FFmpeg layer or binary for audio extraction
  - Set Lambda timeout to 5-10 minutes for large videos
  - Allocate 2-4 GB memory for video processing
  - Configure environment variables (DEEPGRAM_API_KEY, DEFAULT_ROLE)
  - Test Lambda function locally before deploying
  - _Requirements: 4.1, 4.2, 6.4_

- [ ]* 9. Create integration tests
  - Test end-to-end workflow with sample video and user prompt
  - Test role determination with various prompt formats
  - Test error handling for missing video files
  - Test error handling for Deepgram API failures
  - Test error handling for Bedrock throttling
  - Test with large video files to verify timeout settings
  - _Requirements: 1.6, 2.4, 3.3, 4.5, 5.4_

- [ ]* 10. Add monitoring and logging
  - Add CloudWatch metrics for agent invocations
  - Add custom metrics for transcription duration
  - Add custom metrics for summary generation time
  - Set up CloudWatch alarms for error rates
  - Add structured logging for debugging workflow steps
  - _Requirements: 6.4_
