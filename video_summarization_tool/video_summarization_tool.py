"""
Main VideoSummarizationTool interface for AWS Bedrock Agents.

This module provides the main entry point for transcribing video files
and returning structured transcription data with word-level timestamps.
"""

from typing import Any, Dict

from .audio_extractor import extract_audio, validate_video_format, cleanup_temp_files
from .transcription_service import TranscriptionService
from .output_formatter import format_response


def transcribe_video(video_path: str) -> Dict[str, Any]:
    """
    Transcribe a video file and return transcript with timestamps.
    
    This function orchestrates the complete video transcription workflow:
    1. Validates the video format
    2. Extracts audio from the video file
    3. Transcribes the audio using Deepgram API
    4. Formats the response with word-level and utterance-level timestamps
    5. Cleans up temporary files
    
    Args:
        video_path: Path to the video file. Supported formats: MP4, AVI, MOV, MKV
        
    Returns:
        Dictionary containing:
        - transcript (str): Full text transcript of the video's audio
        - words (List[Dict]): List of word objects with timestamps
            - text (str): The word text
            - start (float): Start time in seconds
            - end (float): End time in seconds
            - confidence (float): Confidence score (0.0-1.0)
        - utterances (List[Dict]): List of utterance objects with timestamps
            - text (str): Full utterance text
            - start (float): Start time in seconds
            - end (float): End time in seconds
            - confidence (float): Average confidence score
            - words (List[Dict]): Words in this utterance
        - metadata (Dict): Transcription metadata
            - duration (float): Audio duration in seconds
            - language (str): Detected language code
            - model (str): Model used for transcription (nova-3)
            - confidence (float): Overall confidence score
        
    Raises:
        FileNotFoundError: If video file doesn't exist at the provided path
        ValueError: If video format is unsupported. Supported formats: MP4, AVI, MOV, MKV
        EnvironmentError: If DEEPGRAM_API_KEY environment variable is not set
        RuntimeError: If audio extraction fails (e.g., FFmpeg error)
        ApiError: If Deepgram API returns an error
        ConnectionError: If network connectivity issues occur
        
    Example:
        >>> result = transcribe_video("path/to/video.mp4")
        >>> print(result['transcript'])
        >>> for word in result['words']:
        ...     print(f"{word['text']} ({word['start']}-{word['end']})")
    """
    audio_path = None
    
    try:
        # Step 1: Validate video format
        validate_video_format(video_path)
        
        # Step 2: Extract audio from video
        audio_path = extract_audio(video_path)
        
        # Step 3: Initialize transcription service and transcribe audio
        transcription_service = TranscriptionService()
        deepgram_response = transcription_service.transcribe_audio(audio_path)
        
        # Step 4: Format the response
        formatted_result = format_response(deepgram_response)
        
        return formatted_result
        
    finally:
        # Step 5: Ensure cleanup happens even if errors occur
        if audio_path:
            cleanup_temp_files(audio_path)
