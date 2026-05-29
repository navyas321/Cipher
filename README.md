# Cipher — Agentic Video Summarization on AWS Bedrock

Cipher turns a video sitting in S3 into a **role-specific summary**. You give it a video and a prompt like *"summarize this for a project manager"*; it transcribes the audio with Deepgram, figures out the target role, and uses Amazon Bedrock (Claude 3.5 Sonnet) to generate a summary tailored to that role.

Under the hood Cipher is two things you can use independently:

1. **`video_summarization_tool`** — a small, standalone Python library that extracts audio from a video and transcribes it with word- and utterance-level timestamps via Deepgram's Nova-3 model. Usable on its own, no AWS required.
2. **A Bedrock Agent deployment** — Lambda functions, two Bedrock Agents (an Orchestrator and a Role-Determination agent), action groups, and IAM/CloudFormation scaffolding that wire the library into a full serverless workflow.

---

## Table of Contents

- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick start — the transcription library](#quick-start--the-transcription-library)
- [Deploying the full Bedrock workflow](#deploying-the-full-bedrock-workflow)
- [Configuration](#configuration)
- [Library API reference](#library-api-reference)
- [Output structure](#output-structure)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Architecture

```
                ┌──────────────────────────────────────────────┐
  user_prompt   │            Lambda Handler (entry point)        │
  + video_key   │                                                │
 ───────────────▶   invoke_agent ──▶ Bedrock Orchestrator Agent  │
                │                     (Claude 3.5 Sonnet)         │
                │                          │                      │
                │      action group calls  │                      │
                │        ┌─────────────┬────┴────────┬──────────┐ │
                │        ▼             ▼             ▼          ▼ │
                │  retrieve_video  transcribe_   invoke_role  (LLM│
                │   _from_s3        video         _agent      summ│
                │        │             │             │       arize)│
                └────────┼─────────────┼─────────────┼────────────┘
                         ▼             ▼             ▼
                     ┌───────┐   ┌──────────┐  ┌──────────────┐
                     │  S3   │   │ Deepgram │  │ Role-Determ. │
                     │bucket │   │   API    │  │ Bedrock Agent│
                     └───────┘   └──────────┘  └──────────────┘
```

- **Orchestrator Agent** coordinates the workflow via an action group: pull the video from S3, transcribe it, ask the Role-Determination Agent who the summary is for, then summarize with its own foundation model.
- **Role-Determination Agent** is a pure-reasoning agent that reads the user prompt and returns `{role, context, confidence, fallback}` as JSON.
- **Transcription** is delegated to the `video_summarization_tool` library (FFmpeg audio extraction + Deepgram Nova-3).

The full design — components, data models, error handling, and IAM policies — lives in [`.kiro/specs/lambda-s3-bedrock-video/design.md`](.kiro/specs/lambda-s3-bedrock-video/design.md).

## Repository layout

| Path | What it is |
|---|---|
| `video_summarization_tool/` | Standalone transcription library (`transcribe_video`, formatters, audio extractor) |
| `lambda_handler.py` | Main Lambda entry point — invokes the Orchestrator Agent |
| `orchestrator_lambda.py` | Orchestrator-side Lambda logic |
| `action_group_lambda.py` | Implements action-group functions (S3 fetch, transcribe, invoke role agent) |
| `action_group_schema.json` | OpenAPI-style schema for the action group |
| `bedrock_agent_setup.py` | Creates the two Bedrock Agents, IAM roles, and aliases |
| `configure_orchestrator_agent.py` | Attaches the action-group Lambda to the Orchestrator Agent |
| `deploy_lambdas.py` | Packages and deploys the Lambda functions |
| `verify_bedrock_setup.py` | Verifies agents, roles, and aliases are correctly provisioned |
| `bedrock-agents-cfn.yaml` | CloudFormation template for the agent infrastructure |
| `role_guidelines.csv` | Reference guidance for role-specific summarization |
| `example.py`, `quick_test.py`, `show_transcript.py` | Library usage examples / helpers |
| `test_*.py` | Unit and workflow tests |
| [`QUICKSTART.md`](QUICKSTART.md) | Step-by-step Bedrock infrastructure setup |
| [`DEPLOY.md`](DEPLOY.md) | Condensed end-to-end deployment steps |
| [`BEDROCK_SETUP_README.md`](BEDROCK_SETUP_README.md) | Detailed Bedrock agent setup notes |

## Prerequisites

- **Python** 3.9+
- **FFmpeg** 4.0+ on your PATH (used to extract audio from video)
- **Deepgram API key** — sign up at [deepgram.com](https://console.deepgram.com/signup)
- **For the Bedrock workflow only:** an AWS account with Bedrock enabled, access to Claude 3.5 Sonnet, the AWS CLI configured (`aws configure`), and IAM permissions to create roles, Lambdas, and Bedrock agents.

Install FFmpeg:

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install ffmpeg
# macOS
brew install ffmpeg
# Windows: download from https://ffmpeg.org/download.html and add to PATH

ffmpeg -version   # verify
```

## Quick start — the transcription library

If you just want video-to-text with timestamps, you only need the library (no AWS):

```bash
pip install -r requirements.txt          # deepgram-sdk, python-dotenv
export DEEPGRAM_API_KEY=your_api_key_here   # Windows: $env:DEEPGRAM_API_KEY="..."
```

```python
from video_summarization_tool import transcribe_video

result = transcribe_video("path/to/video.mp4")   # mp4, avi, mov, mkv

print(result["transcript"])
for word in result["words"]:
    print(f"{word['text']}  {word['start']:.3f}s–{word['end']:.3f}s")

print("Duration:", result["metadata"]["duration"], "s")
```

Run the bundled demo:

```bash
python example.py
```

## Deploying the full Bedrock workflow

This provisions AWS resources and **will incur AWS charges**. See [`QUICKSTART.md`](QUICKSTART.md) for the annotated version; the short path:

```bash
# 1. Install AWS deps and configure credentials
pip install -r setup_requirements.txt    # boto3, botocore
aws configure
aws sts get-caller-identity               # sanity check

# 2. Create the two Bedrock Agents, IAM roles, and aliases
python bedrock_agent_setup.py             # writes bedrock_agent_config.json
python verify_bedrock_setup.py            # confirm everything provisioned

# 3. Deploy the Lambda functions
python deploy_lambdas.py

# 4. Attach the action-group Lambda to the Orchestrator Agent
python configure_orchestrator_agent.py \
  arn:aws:lambda:REGION:ACCOUNT:function:video-processing-action-group

# 5. Test end to end (upload a video, then run the workflow)
aws s3 cp test_video.mp4 s3://your-bucket/
python test_workflow.py your-bucket test_video.mp4 "Summarize this for a project manager"
```

Prefer infrastructure-as-code? Deploy `bedrock-agents-cfn.yaml` via CloudFormation instead of `bedrock_agent_setup.py`.

To tear everything down, follow the **Cleanup** section in [`DEPLOY.md`](DEPLOY.md).

## Configuration

Copy `.env.example` to `.env` and fill it in:

```bash
cp .env.example .env
```

| Variable | Used by | Notes |
|---|---|---|
| `DEEPGRAM_API_KEY` | Library + action Lambda | **Required.** Your Deepgram key. |
| `ORCHESTRATOR_AGENT_ID` | Lambda handler | From `bedrock_agent_config.json` after setup. |
| `ROLE_AGENT_ID` | Lambda handler | From `bedrock_agent_config.json` after setup. |
| `BEDROCK_MODEL_ID` | Action Lambda | Default `anthropic.claude-3-5-sonnet-20240620-v1:0`. |
| `DEFAULT_ROLE` | Action Lambda | Fallback role if determination fails (e.g. `general`). |
| `AWS_REGION` | All AWS calls | Default `us-east-1`. |
| `LOG_LEVEL` | All | `DEBUG` / `INFO` / `WARNING` / `ERROR`. |

> **Never commit `.env` or API keys.** `.env` is already covered by `.gitignore`.

## Library API reference

### `transcribe_video(video_path: str) -> dict`

Validates the format, extracts audio with FFmpeg, transcribes via Deepgram Nova-3, formats the result, and cleans up temp files. Supported formats: **MP4, AVI, MOV, MKV**.

**Raises:** `FileNotFoundError` (missing file), `ValueError` (unsupported format), `EnvironmentError` (`DEEPGRAM_API_KEY` unset), `RuntimeError` (FFmpeg failure), `ApiError` (Deepgram error), `ConnectionError` (network/IO).

### `find_time_ranges_by_keywords(words: list, keywords: list) -> list`

```python
from video_summarization_tool.output_formatter import find_time_ranges_by_keywords

ranges = find_time_ranges_by_keywords(result["words"], ["important", "summary"])
for r in ranges:
    print(f"{r['start']:.3f}s: {r['matched_text']}  (matched {r['keywords']})")
```

Case-insensitive substring match over the word list; each hit returns `start`, `end`, a few words of surrounding `matched_text`, and the matched `keywords`. Handy for jumping to or clipping relevant segments with FFmpeg.

## Output structure

```python
{
    "transcript": str,        # full text
    "words": [                # word-level timestamps
        {"text": str, "start": float, "end": float, "confidence": float},
        ...
    ],
    "utterances": [           # grouped segments, each with its own "words" list
        {"text": str, "start": float, "end": float, "confidence": float, "words": [...]},
        ...
    ],
    "metadata": {"duration": float, "language": str, "model": str, "confidence": float}
}
```

Times are in seconds (3-decimal precision); confidence is `0.0–1.0`.

## Testing

```bash
# Library-level tests (no AWS)
python -m pytest test_transcription_service.py test_video.py

# Action-group / workflow tests (require AWS + a deployed stack)
python -m pytest test_action_lambda.py test_workflow.py test_full_workflow_simulation.py
```

The `test_*.py` files at the repo root cover the transcription service, action Lambda, S3 action, async paths, and an end-to-end workflow simulation.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `RuntimeError: ... FFmpeg not found` | Install FFmpeg and ensure it's on your PATH (`ffmpeg -version`). |
| `EnvironmentError: DEEPGRAM_API_KEY ... not set` | Export the key or set it in `.env`. |
| `ValueError: Unsupported format` | Convert first: `ffmpeg -i in.wmv -c copy out.mp4`. |
| `Model not found` during setup | Request Claude 3.5 Sonnet access in the Bedrock console; verify with `aws bedrock list-foundation-models`. |
| `Access Denied` creating agents | Grant `bedrock:CreateAgent`, `iam:CreateRole`, etc. (see [`QUICKSTART.md`](QUICKSTART.md)). |
| Verification says "Agent not found" | AWS propagation lag — wait ~60s and re-run `verify_bedrock_setup.py`. |

## License

Provided as-is for use with the Deepgram API and AWS Bedrock. See repository for details.
