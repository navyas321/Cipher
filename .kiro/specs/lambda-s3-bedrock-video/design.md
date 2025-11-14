# Design Document

## Overview

This design implements an agentic orchestration system using Amazon Bedrock Agents within a Python-based AWS Lambda function. The system processes video files from S3, transcribes them using Deepgram, and generates role-specific summaries using Amazon Bedrock. The architecture employs two Bedrock Agents: an Orchestrator Agent that manages the workflow, and a Role Determination Agent that analyzes user prompts to extract role information. Bedrock Agents provide built-in capabilities for action groups, knowledge bases, and prompt orchestration.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      Lambda Handler                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐     │
│  │     Bedrock Orchestrator Agent                        │     │
│  │     - Agent ID: orchestrator-agent                    │     │
│  │     - Foundation Model: Claude 3 Sonnet               │     │
│  │     - Action Groups: video-processing-actions         │     │
│  └────────┬─────────────────────────────────────────────┘     │
│           │                                                     │
│           │ Invokes via InvokeAgent API                        │
│           │                                                     │
│           ├──────────────┬──────────────┬──────────────┐      │
│           ▼              ▼              ▼              ▼      │
│    ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│    │  Bedrock   │  │   S3     │  │ Deepgram │  │ Bedrock  │ │
│    │   Role     │  │Retrieval │  │Transcribe│  │ Summary  │ │
│    │Determine   │  │  Lambda  │  │  Lambda  │  │  Lambda  │ │
│    │   Agent    │  │ Function │  │ Function │  │ Function │ │
│    └────────────┘  └──────────┘  └──────────┘  └──────────┘ │
│         │               │              │              │       │
└─────────┼───────────────┼──────────────┼──────────────┼───────┘
          │               │              │              │
          ▼               ▼              ▼              ▼
    ┌──────────┐    ┌────────┐    ┌──────────┐  ┌────────┐
    │ Bedrock  │    │   S3   │    │ Deepgram│  │Bedrock │
    │  Agent   │    │ Bucket │    │   API   │  │  API   │
    │  Runtime │    └────────┘    └──────────┘  └────────┘
    └──────────┘
```

The architecture consists of:
- **Bedrock Orchestrator Agent**: A Bedrock Agent that coordinates the entire workflow using action groups
- **Role Determination Agent**: A separate Bedrock Agent specialized in extracting role information from prompts
- **Action Group Lambda Functions**: Lambda functions that implement specific actions (S3 retrieval, Deepgram transcription, summary generation)
- **S3 Integration**: Retrieves video files for processing
- **Deepgram Integration**: Transcribes video audio to text via Lambda action
- **Bedrock Runtime**: Executes agent invocations and manages conversation flow
- **IAM Permissions**: Cross-service access control for agents and Lambda functions

## Components and Interfaces

### 1. Bedrock Orchestrator Agent

**Purpose**: Coordinate the entire video processing workflow using Bedrock Agents

**Configuration**:
```python
{
    "agent_name": "VideoProcessingOrchestrator",
    "agent_id": "orchestrator-agent-id",
    "foundation_model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "instruction": "You are an orchestrator agent that processes videos...",
    "action_groups": [
        {
            "name": "video-processing-actions",
            "description": "Actions for video processing workflow",
            "lambda_arn": "arn:aws:lambda:region:account:function:video-actions"
        }
    ]
}
```

**Responsibilities**:
- Invoke Role Determination Agent via Bedrock Agent-to-Agent communication
- Coordinate video retrieval from S3 via action group
- Manage Deepgram transcription via action group
- Coordinate summary generation via action group
- Handle errors at each workflow stage
- Return structured response with role-specific summary

**Action Group Functions**:
1. `retrieve_video_from_s3` - Gets video file from S3
2. `transcribe_video` - Sends video to Deepgram
3. `invoke_role_agent` - Calls Role Determination Agent

**Note**: Summary generation is handled directly by the Orchestrator Agent's foundation model, not via an action group function.

**Invocation**:
```python
response = bedrock_agent_runtime.invoke_agent(
    agentId='orchestrator-agent-id',
    agentAliasId='TSTALIASID',
    sessionId='session-123',
    inputText=user_prompt
)
```

### 2. Bedrock Role Determination Agent

**Purpose**: Analyze user prompts to extract role information using Bedrock Agents

**Configuration**:
```python
{
    "agent_name": "RoleDeterminationAgent",
    "agent_id": "role-agent-id",
    "foundation_model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "instruction": """You are a role determination agent. Analyze user prompts to identify 
    the target role perspective for video summaries. Extract the role name and relevant 
    context. Return results in JSON format with fields: role, context, confidence.""",
    "action_groups": []  # No action groups needed - pure LLM reasoning
}
```

**Responsibilities**:
- Parse user prompt to identify role-related keywords
- Analyze prompt using Bedrock Agent's foundation model
- Return structured JSON with identified role and relevant details
- Provide default role if determination fails

**Output Structure**:
```python
{
    "role": str,              # Identified role (e.g., "manager", "engineer", "executive")
    "context": str,           # Additional context about the role
    "confidence": float,      # Confidence score (0-1)
    "fallback": bool          # True if default role was used
}
```

**Invocation from Orchestrator**:
```python
# Orchestrator agent calls this via agent-to-agent invocation
response = bedrock_agent_runtime.invoke_agent(
    agentId='role-agent-id',
    agentAliasId='TSTALIASID',
    sessionId='role-session-123',
    inputText=f"Extract role from: {user_prompt}"
)
```

### 3. Video Retrieval Component

**Purpose**: Fetch video files from S3 for processing

**Interface**:
```python
def get_video_from_s3(bucket_name: str, object_key: str) -> bytes
```

**Responsibilities**:
- Retrieve video file from S3 using boto3
- Validate file existence
- Handle S3 access errors
- Return video file content as bytes

### 4. Deepgram Transcription Component

**Purpose**: Transcribe video audio to text using Deepgram API via the video_summarization_tool module

**Interface**:
```python
from video_summarization_tool import transcribe_video

def transcribe_video_file(video_path: str) -> dict
```

**Existing Implementation**:
The `video_summarization_tool` module provides:
- Audio extraction from video using FFmpeg
- Deepgram Nova-3 model integration
- Word-level timestamps with confidence scores
- Utterance segmentation
- Keyword-based time range finding

**Module Structure**:
- `audio_extractor.py`: Extracts audio from video files
- `transcription_service.py`: Interfaces with Deepgram API
- `output_formatter.py`: Formats transcription results
- `video_summarization_tool.py`: Main entry point

**Responsibilities**:
- Extract audio from video file using FFmpeg
- Send audio to Deepgram API (Nova-3 model)
- Parse Deepgram response with word-level timestamps
- Return structured transcription result with metadata
- Handle API errors and rate limiting

**Deepgram Configuration**:
- Model: nova-3 (latest general-purpose model)
- Features: punctuation, paragraphs, utterances, word-level timestamps
- Language: auto-detect
- Smart formatting enabled

**Output Structure**:
```python
{
    "transcript": str,              # Full text transcript
    "words": List[Dict],            # Word-level data with timestamps
    "utterances": List[Dict],       # Utterance-level segments
    "metadata": {
        "duration": float,
        "language": str,
        "model": str,
        "confidence": float
    }
}
```

### 5. Bedrock Summary Generation Component

**Purpose**: Generate role-specific summaries using Bedrock

**Interface**:
```python
def generate_role_summary(transcription: str, role_info: dict, model_id: str) -> str
```

**Responsibilities**:
- Construct prompt with transcription and role context
- Invoke Bedrock model (e.g., Claude 3)
- Parse model response to extract summary
- Handle Bedrock errors and throttling
- Return role-specific summary text

**Prompt Template**:
```
You are analyzing a video transcription for a {role}.

Transcription:
{transcription_text}

Please provide a concise summary of this video specifically tailored for a {role}, 
focusing on information most relevant to their responsibilities and interests.
```

### 6. Lambda Handler (Main Entry Point)

**Purpose**: Main entry point for Lambda execution that invokes Bedrock Orchestrator Agent

**Interface**:
```python
def lambda_handler(event: dict, context: object) -> dict
```

**Responsibilities**:
- Extract parameters from event (user_prompt, bucket_name, video_key)
- Initialize Bedrock Agent Runtime client
- Invoke Orchestrator Agent via InvokeAgent API
- Stream and parse agent response
- Handle top-level errors
- Return final response with status code and body

**Implementation Flow**:
1. Parse incoming event
2. Create session ID for agent invocation
3. Call `bedrock_agent_runtime.invoke_agent()` with Orchestrator Agent ID
4. Stream response chunks from agent
5. Parse final output from agent
6. Return structured response

### 7. Action Group Lambda Function

**Purpose**: Implements action group functions called by Bedrock Orchestrator Agent

**Interface**:
```python
def action_handler(event: dict, context: object) -> dict
```

**Supported Actions**:
- `retrieve_video_from_s3`: Gets video file from S3
- `transcribe_video`: Sends video to Deepgram API
- `invoke_role_agent`: Invokes Role Determination Agent

**Action Schema**:
```json
{
    "actionGroupName": "video-processing-actions",
    "apiSchema": {
        "retrieve_video_from_s3": {
            "description": "Retrieve video file from S3 bucket",
            "parameters": {
                "bucket_name": "string",
                "video_key": "string"
            }
        },
        "transcribe_video": {
            "description": "Transcribe video using Deepgram",
            "parameters": {
                "video_path": "string"
            }
        },
        "invoke_role_agent": {
            "description": "Invoke Role Determination Agent to extract role from user prompt",
            "parameters": {
                "user_prompt": "string"
            }
        }
    }
}
```

## Data Models

### Event Structure
```python
{
    "user_prompt": str,           # User's prompt specifying role and context
    "bucket_name": str,           # S3 bucket name
    "video_key": str,             # S3 object key for video file
    "orchestrator_agent_id": str, # Bedrock Orchestrator Agent ID
    "role_agent_id": str,         # Bedrock Role Determination Agent ID
    "region": str                 # AWS region (optional, defaults to us-east-1)
}
```

### Workflow State Structure
```python
{
    "stage": str,                 # Current workflow stage
    "role_info": {
        "role": str,
        "context": str,
        "confidence": float,
        "fallback": bool
    },
    "video_data": bytes,          # Retrieved video file
    "transcription": {
        "text": str,
        "duration": float,
        "language": str
    },
    "summary": str,               # Final role-specific summary
    "errors": list                # Any errors encountered
}
```

### Response Structure
```python
{
    "statusCode": int,            # HTTP status code (200, 400, 500, etc.)
    "body": {
        "role": str,              # Identified role
        "summary": str,           # Role-specific video summary
        "transcription_length": int,  # Character count of transcription
        "processing_time": float, # Total processing time in seconds
        "metadata": {
            "video_key": str,
            "model_used": str,
            "workflow_stages": list
        },
        "message": str            # Status message
    }
}
```

## Error Handling

### S3 Errors
- **NoSuchKey**: Handle missing video file, return 404 error
- **AccessDenied**: Handle insufficient permissions, return 403 error
- **NoSuchBucket**: Handle invalid bucket name, return 404 error

### Deepgram Errors
- **AuthenticationError**: Handle invalid API key, return 401 error
- **RateLimitError**: Implement retry logic with exponential backoff
- **TranscriptionError**: Handle transcription failures, return 500 error
- **UnsupportedFormat**: Handle invalid video formats, return 400 error

### Bedrock Errors
- **ModelNotFound**: Handle invalid model ID, return 400 error
- **ThrottlingException**: Implement retry logic with exponential backoff
- **ValidationException**: Handle invalid input format, return 400 error
- **ServiceQuotaExceededException**: Handle quota limits, return 429 error

### Agent-Specific Errors
- **RoleDeterminationFailure**: Use default role if extraction fails
- **OrchestrationError**: Handle workflow coordination failures

### General Error Strategy
- Use try-except blocks for each service call
- Log errors with CloudWatch integration
- Return structured error responses with step information
- Include error codes, messages, and failed step in response body
- Implement retry logic for transient failures (3 attempts max)
- Fail fast for non-recoverable errors

## Testing Strategy

### Unit Testing
- Mock boto3 clients for S3 and Bedrock
- Mock Deepgram API responses
- Test Orchestrator Agent workflow coordination
- Test Role Determination Agent with various prompts
- Test each component independently
- Verify error handling paths for all services

### Integration Testing
- Test with actual AWS services in development environment
- Test with Deepgram API using test videos
- Validate end-to-end flow from user prompt to summary
- Test with sample video files of various formats

### Key Test Cases
1. **Successful workflow**: User prompt → role extraction → transcription → summary
2. **Role determination**: Various prompt formats and role types
3. **Video file not found**: S3 NoSuchKey error handling
4. **Deepgram transcription failure**: API error handling
5. **Bedrock model invocation failure**: Throttling and validation errors
6. **Invalid event structure**: Missing required fields
7. **Role cannot be determined**: Default role fallback
8. **Large video files**: Timeout and memory handling
9. **Multiple roles in prompt**: Disambiguation logic
10. **Empty transcription**: Handling videos with no speech

## Implementation Notes

### AWS SDK Configuration
- Use boto3 for S3 and Bedrock interactions
- Configure clients with appropriate regions
- Implement proper credential handling via IAM roles

### Deepgram SDK Configuration
- Use Deepgram Python SDK (deepgram-sdk)
- Store API key in AWS Secrets Manager or environment variables
- Configure timeout settings for large video files
- Use prerecorded transcription endpoint

### IAM Permissions Required

**Main Lambda Handler**:
```json
{
    "Bedrock": [
        "bedrock:InvokeAgent",
        "bedrock:GetAgent",
        "bedrock:ListAgents"
    ],
    "CloudWatch": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
    ]
}
```

**Action Group Lambda Function**:
```json
{
    "S3": ["s3:GetObject"],
    "Bedrock": [
        "bedrock:InvokeModel",
        "bedrock:InvokeAgent"
    ],
    "CloudWatch": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
    ],
    "SecretsManager": ["secretsmanager:GetSecretValue"]
}
```

**Bedrock Agent Execution Role**:
```json
{
    "Lambda": ["lambda:InvokeFunction"],
    "Bedrock": [
        "bedrock:InvokeModel",
        "bedrock:InvokeAgent"
    ]
}
```

### Bedrock Model Considerations
- Use Claude 3.5 Sonnet for both role determination and summary generation
- Text-only input (transcription + role context)
- JSON mode for structured role extraction
- Prompt engineering for consistent output format
- Token limits: Claude 3.5 Sonnet supports 200K context window
- Consider chunking for extremely long transcriptions (>150K tokens)

### Deepgram Configuration
- Model: `nova-2` (latest general-purpose model)
- Language: Auto-detect or specify (e.g., `en-US`)
- Features: Punctuation, paragraphs, utterances
- Smart formatting enabled
- Diarization optional (for multi-speaker videos)

### Bedrock Agent Design Pattern
- **Orchestrator Agent**: Uses action groups to coordinate workflow steps
- **Role Determination Agent**: Single-purpose agent with focused instruction prompt
- Both agents leverage Bedrock's managed agent infrastructure
- Agents use Claude 3 foundation models (Sonnet for orchestration, Haiku for role determination)
- Agents are stateless within a session but maintain conversation context
- Action groups provide the interface between agents and external services
- Agent-to-agent communication via InvokeAgent API calls
- Clear separation of concerns: orchestration vs. role analysis

### Bedrock Agent Configuration
**Orchestrator Agent**:
- Foundation Model: Claude 3.5 Sonnet (best reasoning for complex workflows)
- Action Groups: video-processing-actions
- Instruction: Detailed workflow coordination prompt
- Session management: Unique session ID per invocation

**Role Determination Agent**:
- Foundation Model: Claude 3.5 Sonnet (consistent model across agents)
- Action Groups: None (pure LLM reasoning)
- Instruction: Focused role extraction prompt with JSON output format
- Session management: Separate session per role determination

### Performance Considerations
- Lambda timeout: Set to 5-10 minutes for large videos
- Memory: Allocate 2-4 GB for video processing
- Deepgram streaming vs prerecorded: Use prerecorded for simplicity
- Consider async processing for very large files
- Cache role determination results if same prompt used multiple times

### Environment Variables

**Main Lambda Handler**:
```python
ORCHESTRATOR_AGENT_ID: str     # Bedrock Orchestrator Agent ID
ROLE_AGENT_ID: str             # Bedrock Role Determination Agent ID
LOG_LEVEL: str                 # DEBUG, INFO, WARNING, ERROR
```

**Action Group Lambda Function**:
```python
DEEPGRAM_API_KEY: str          # Deepgram API key (from Secrets Manager or env)
DEFAULT_ROLE: str              # Fallback role if determination fails (e.g., "general")
BEDROCK_MODEL_ID: str          # Default: anthropic.claude-3-5-sonnet-20240620-v1:0
LOG_LEVEL: str                 # DEBUG, INFO, WARNING, ERROR
```
