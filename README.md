# Video Summarization Tool for AWS Bedrock Agents

A Python module that provides video-to-text transcription capabilities using Deepgram's speech-to-text API. This tool extracts audio from video files, transcribes the audio with word-level timestamps, and returns structured data that can be used by AWS Bedrock Agents for video summarization and content analysis.

## Features

- 🎥 **Multi-format Support**: Process MP4, AVI, MOV, and MKV video files
- 🎯 **Word-Level Timestamps**: Get precise start and end times for every word
- 💬 **Utterance Segmentation**: Automatically group words into meaningful segments
- 🔍 **Keyword Search**: Find specific content and extract time ranges
- 🤖 **Bedrock Agent Ready**: Simple interface designed for AWS Bedrock Agent integration
- 🔒 **Secure**: Environment-based API key management

## Table of Contents

- [Installation](#installation)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Bedrock Agent Setup](#bedrock-agent-setup)
- [Usage](#usage)
- [Output Structure](#output-structure)
- [API Reference](#api-reference)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [License](#license)

## Installation

### 1. Install System Dependencies

#### FFmpeg (Required)

FFmpeg is required for extracting audio from video files.

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

**Verify installation:**
```bash
ffmpeg -version
```

### 2. Install Python Package

**Python 3.8 or higher is required.**

```bash
# Clone or download this repository
cd video-summarization-tool

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Required Python Packages

The following packages will be installed:

- `deepgram-sdk>=5.0.0` - Deepgram API client for speech-to-text
- `python-dotenv>=1.0.0` - Environment variable management

## Prerequisites

- **Python**: Version 3.8 or higher
- **FFmpeg**: Version 4.0 or higher
- **Deepgram API Key**: Sign up at [deepgram.com](https://deepgram.com) to get your API key

## Configuration

### Environment Variables

The tool requires a Deepgram API key to function. Set the `DEEPGRAM_API_KEY` environment variable using one of the following methods:

#### Option 1: Export in Shell (Recommended for Development)

```bash
export DEEPGRAM_API_KEY=your_api_key_here
```

#### Option 2: Use a .env File (Recommended for Production)

Create a `.env` file in your project root:

```bash
# .env
DEEPGRAM_API_KEY=your_api_key_here
```

Then load it in your Python code:

```python
from dotenv import load_dotenv
load_dotenv()
```

#### Option 3: Set Programmatically (Not Recommended)

```python
import os
os.environ['DEEPGRAM_API_KEY'] = 'your_api_key_here'
```

⚠️ **Security Note**: Never commit API keys to version control. Use `.env` files and add them to `.gitignore`.

## Bedrock Agent Setup

This project includes infrastructure setup for AWS Bedrock Agents that orchestrate the video processing workflow. The setup creates two specialized agents:

- **Orchestrator Agent**: Manages the complete workflow from video retrieval to summary generation
- **Role Determination Agent**: Analyzes user prompts to extract role-specific context

### Quick Setup

```bash
# Install setup dependencies
pip install -r setup_requirements.txt

# Run the setup script
python bedrock_agent_setup.py

# Verify the setup
python verify_bedrock_setup.py
```

For detailed instructions, see [BEDROCK_SETUP_README.md](BEDROCK_SETUP_README.md).

### Getting a Deepgram API Key

1. Sign up for a free account at [console.deepgram.com](https://console.deepgram.com/signup)
2. Navigate to the API Keys section
3. Create a new API key
4. Copy the key and set it as an environment variable

## Usage

### Basic Usage

```python
from video_summarization_tool import transcribe_video

# Transcribe a video file
result = transcribe_video("path/to/video.mp4")

# Access the full transcript
print(result['transcript'])

# Access word-level timestamps
for word in result['words']:
    print(f"{word['text']} ({word['start']:.3f}s - {word['end']:.3f}s)")

# Access metadata
print(f"Duration: {result['metadata']['duration']} seconds")
print(f"Language: {result['metadata']['language']}")
print(f"Confidence: {result['metadata']['confidence']:.2%}")
```

### Advanced Usage: Find Content by Keywords

```python
from video_summarization_tool import transcribe_video
from video_summarization_tool.output_formatter import find_time_ranges_by_keywords

# Transcribe video
result = transcribe_video("path/to/video.mp4")

# Find time ranges containing specific keywords
keywords = ["important", "summary", "conclusion"]
time_ranges = find_time_ranges_by_keywords(result['words'], keywords)

# Print matching segments
for time_range in time_ranges:
    print(f"Found at {time_range['start']:.3f}s - {time_range['end']:.3f}s")
    print(f"Keywords: {', '.join(time_range['keywords'])}")
    print(f"Context: {time_range['matched_text']}\n")
```

### Extract Video Segments Based on Transcription

```python
import subprocess
from video_summarization_tool import transcribe_video
from video_summarization_tool.output_formatter import find_time_ranges_by_keywords

# Transcribe and find important segments
result = transcribe_video("input.mp4")
time_ranges = find_time_ranges_by_keywords(result['words'], ["key point", "important"])

# Extract the first matching segment using FFmpeg
if time_ranges:
    segment = time_ranges[0]
    subprocess.run([
        "ffmpeg",
        "-i", "input.mp4",
        "-ss", str(segment['start']),
        "-to", str(segment['end']),
        "-c", "copy",
        "output_segment.mp4"
    ])
```

### Use with AWS Bedrock Agents

```python
# bedrock_agent_tool.py
from video_summarization_tool import transcribe_video

def video_analysis_tool(video_path: str) -> dict:
    """
    Bedrock Agent tool for video analysis.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Transcription result with timestamps
    """
    try:
        result = transcribe_video(video_path)
        return {
            "success": True,
            "transcript": result['transcript'],
            "duration": result['metadata']['duration'],
            "word_count": len(result['words']),
            "utterance_count": len(result['utterances'])
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

## Output Structure

The `transcribe_video()` function returns a dictionary with the following structure:

```python
{
    "transcript": str,              # Full text transcript
    "words": List[Dict],            # Word-level data
    "utterances": List[Dict],       # Utterance-level data
    "metadata": Dict                # Transcription metadata
}
```

### Word Object

Each word in the `words` list contains:

```python
{
    "text": str,           # The word text
    "start": float,        # Start time in seconds (3 decimal precision)
    "end": float,          # End time in seconds (3 decimal precision)
    "confidence": float    # Confidence score (0.0-1.0)
}
```

**Example:**
```python
{
    "text": "Hello",
    "start": 0.123,
    "end": 0.456,
    "confidence": 0.98
}
```

### Utterance Object

Each utterance in the `utterances` list contains:

```python
{
    "text": str,           # Full utterance text
    "start": float,        # Start time in seconds
    "end": float,          # End time in seconds
    "confidence": float,   # Average confidence score
    "words": List[Dict]    # Words in this utterance
}
```

**Example:**
```python
{
    "text": "Hello world, this is an example.",
    "start": 0.123,
    "end": 2.456,
    "confidence": 0.96,
    "words": [...]  # List of word objects
}
```

### Metadata Object

The `metadata` dictionary contains:

```python
{
    "duration": float,     # Audio duration in seconds
    "language": str,       # Detected language code (e.g., "en")
    "model": str,          # Model used (e.g., "nova-3")
    "confidence": float    # Overall confidence score (0.0-1.0)
}
```

**Example:**
```python
{
    "duration": 120.5,
    "language": "en",
    "model": "nova-3",
    "confidence": 0.94
}
```

### Time Range Object

The `find_time_ranges_by_keywords()` function returns a list of time range objects:

```python
{
    "start": float,        # Start time in seconds
    "end": float,          # End time in seconds
    "matched_text": str,   # Text containing the keyword
    "keywords": List[str]  # Keywords found in this range
}
```

**Example:**
```python
{
    "start": 45.123,
    "end": 45.456,
    "matched_text": "this is an important point to remember",
    "keywords": ["important"]
}
```

## API Reference

### Main Function

#### `transcribe_video(video_path: str) -> Dict[str, Any]`

Transcribe a video file and return transcript with timestamps.

**Parameters:**
- `video_path` (str): Path to the video file. Supported formats: MP4, AVI, MOV, MKV

**Returns:**
- `Dict[str, Any]`: Dictionary containing transcript, words, utterances, and metadata

**Raises:**
- `FileNotFoundError`: If video file doesn't exist at the provided path
- `ValueError`: If video format is unsupported
- `EnvironmentError`: If DEEPGRAM_API_KEY environment variable is not set
- `RuntimeError`: If audio extraction fails (e.g., FFmpeg error)
- `ApiError`: If Deepgram API returns an error
- `ConnectionError`: If network connectivity issues occur

### Utility Functions

#### `find_time_ranges_by_keywords(words: List[Dict], keywords: List[str]) -> List[Dict]`

Find time ranges in the transcript containing specific keywords.

**Parameters:**
- `words` (List[Dict]): List of word objects with timestamps from transcription result
- `keywords` (List[str]): List of keywords to search for (case-insensitive)

**Returns:**
- `List[Dict]`: List of time range objects with matched content

**Example:**
```python
from video_summarization_tool.output_formatter import find_time_ranges_by_keywords

time_ranges = find_time_ranges_by_keywords(
    result['words'],
    ["important", "key", "summary"]
)
```

## Error Handling

The tool provides detailed error messages for common issues:

### FileNotFoundError
```python
# Raised when video file doesn't exist
try:
    result = transcribe_video("nonexistent.mp4")
except FileNotFoundError as e:
    print(f"Video file not found: {e}")
```

### ValueError
```python
# Raised when video format is unsupported
try:
    result = transcribe_video("video.wmv")
except ValueError as e:
    print(f"Unsupported format: {e}")
    # Message includes list of supported formats
```

### EnvironmentError
```python
# Raised when DEEPGRAM_API_KEY is not set
try:
    result = transcribe_video("video.mp4")
except EnvironmentError as e:
    print(f"Configuration error: {e}")
    # Message includes instructions for setting the API key
```

### RuntimeError
```python
# Raised when FFmpeg fails
try:
    result = transcribe_video("corrupted.mp4")
except RuntimeError as e:
    print(f"Audio extraction failed: {e}")
```

### ApiError
```python
# Raised when Deepgram API returns an error
from deepgram.errors import ApiError

try:
    result = transcribe_video("video.mp4")
except ApiError as e:
    print(f"Deepgram API error: {e}")
```

### ConnectionError
```python
# Raised when network issues occur
try:
    result = transcribe_video("video.mp4")
except ConnectionError as e:
    print(f"Network error: {e}")
```

## Examples

### Example 1: Basic Transcription

```python
from video_summarization_tool import transcribe_video

result = transcribe_video("meeting.mp4")
print(result['transcript'])
```

### Example 2: Word-Level Analysis

```python
from video_summarization_tool import transcribe_video

result = transcribe_video("lecture.mp4")

# Find all words with low confidence
low_confidence_words = [
    word for word in result['words']
    if word['confidence'] < 0.8
]

print(f"Found {len(low_confidence_words)} words with low confidence")
```

### Example 3: Utterance-Based Segmentation

```python
from video_summarization_tool import transcribe_video

result = transcribe_video("interview.mp4")

# Print each utterance with timing
for i, utterance in enumerate(result['utterances'], 1):
    duration = utterance['end'] - utterance['start']
    print(f"Segment {i} ({duration:.1f}s): {utterance['text']}")
```

### Example 4: Create Video Chapters

```python
from video_summarization_tool import transcribe_video
from video_summarization_tool.output_formatter import find_time_ranges_by_keywords

result = transcribe_video("tutorial.mp4")

# Find chapter markers based on keywords
chapter_keywords = ["introduction", "step", "conclusion"]
chapters = find_time_ranges_by_keywords(result['words'], chapter_keywords)

# Generate YouTube-style chapter timestamps
print("Video Chapters:")
for i, chapter in enumerate(chapters, 1):
    minutes = int(chapter['start'] // 60)
    seconds = int(chapter['start'] % 60)
    print(f"{minutes:02d}:{seconds:02d} - Chapter {i}: {chapter['matched_text']}")
```

### Example 5: Complete Example Script

See `example.py` for a comprehensive demonstration of all features.

```bash
# Run the example script
python example.py
```

## Supported Video Formats

- **MP4** (.mp4) - MPEG-4 Part 14
- **AVI** (.avi) - Audio Video Interleave
- **MOV** (.mov) - QuickTime File Format
- **MKV** (.mkv) - Matroska Multimedia Container

## Transcription Model

This tool uses Deepgram's **Nova-3** model, which provides:
- High accuracy for general-purpose transcription
- Support for multiple languages
- Automatic punctuation and formatting
- Word-level confidence scores

## Performance Considerations

- **Processing Time**: Typically 10-30% of the video duration
- **File Size**: Large video files may take longer to process
- **Network**: Requires stable internet connection for API calls
- **Temporary Files**: Audio files are temporarily stored and automatically cleaned up

## Troubleshooting

### FFmpeg Not Found

**Error:** `RuntimeError: Audio extraction failed: FFmpeg not found`

**Solution:** Install FFmpeg using the instructions in the [Installation](#installation) section.

### API Key Not Set

**Error:** `EnvironmentError: DEEPGRAM_API_KEY environment variable not set`

**Solution:** Set the environment variable as described in [Configuration](#configuration).

### Unsupported Format

**Error:** `ValueError: Unsupported format: .wmv. Supported formats: .mp4, .avi, .mov, .mkv`

**Solution:** Convert your video to a supported format using FFmpeg:
```bash
ffmpeg -i input.wmv -c:v copy -c:a copy output.mp4
```

### Network Errors

**Error:** `ConnectionError: Failed to connect to Deepgram API`

**Solution:** Check your internet connection and verify that you can reach api.deepgram.com.

## License

This project is provided as-is for use with AWS Bedrock Agents and Deepgram API.

## Support

For issues related to:
- **This tool**: Open an issue in the repository
- **Deepgram API**: Visit [deepgram.com/support](https://deepgram.com/support)
- **AWS Bedrock**: Visit [AWS Support](https://aws.amazon.com/support/)

## Contributing

Contributions are welcome! Please ensure that:
- Code follows PEP 8 style guidelines
- All functions include docstrings
- Error handling is comprehensive
- Tests are included for new features

## Changelog

### Version 1.0.0
- Initial release
- Support for MP4, AVI, MOV, MKV formats
- Word-level and utterance-level timestamps
- Keyword-based time range finder
- AWS Bedrock Agent integration ready
