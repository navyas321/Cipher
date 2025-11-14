"""
Video Summarization Tool for AWS Bedrock Agents

This module provides video-to-text transcription capabilities using Deepgram's
speech-to-text API. It extracts audio from video files, transcribes the audio
with word-level timestamps, and returns structured data for video summarization.
"""

from .video_summarization_tool import transcribe_video

__all__ = ['transcribe_video']
__version__ = '1.0.0'
