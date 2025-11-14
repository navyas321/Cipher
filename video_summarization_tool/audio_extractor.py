"""
Audio extraction module for video files.

This module provides functionality to extract audio tracks from video files
using FFmpeg and manage temporary audio files.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


# Supported video formats
SUPPORTED_FORMATS = {'.mp4', '.avi', '.mov', '.mkv'}


def validate_video_format(video_path: str) -> bool:
    """
    Validate if video format is supported.
    
    Args:
        video_path: Path to video file
        
    Returns:
        True if format is supported
        
    Raises:
        ValueError: If format is unsupported
    """
    file_extension = Path(video_path).suffix.lower()
    
    if file_extension not in SUPPORTED_FORMATS:
        supported_list = ', '.join(sorted(SUPPORTED_FORMATS))
        raise ValueError(
            f"Unsupported format: {file_extension}. "
            f"Supported formats: {supported_list}"
        )
    
    return True


def cleanup_temp_files(audio_path: str) -> None:
    """
    Remove temporary audio files.
    
    Args:
        audio_path: Path to temporary audio file
    """
    try:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        # Log but don't raise - cleanup failures shouldn't break the flow
        print(f"Warning: Failed to cleanup temporary file {audio_path}: {e}")


def extract_audio(
    video_path: str,
    output_format: str = "wav"
) -> str:
    """
    Extract audio from video file.
    
    Args:
        video_path: Path to input video
        output_format: Audio format (default: wav)
        
    Returns:
        Path to extracted audio file
        
    Raises:
        FileNotFoundError: If video file doesn't exist
        ValueError: If video format is unsupported
        RuntimeError: If FFmpeg extraction fails
    """
    # Check if video file exists
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Validate video format
    validate_video_format(video_path)
    
    # Create temporary file for audio output
    temp_fd, temp_audio_path = tempfile.mkstemp(suffix=f'.{output_format}')
    os.close(temp_fd)  # Close the file descriptor, we just need the path
    
    try:
        # Build FFmpeg command
        # -i: input file
        # -vn: disable video recording
        # -acodec pcm_s16le: audio codec for WAV
        # -ar 16000: sample rate 16kHz (optimal for speech recognition)
        # -ac 1: mono audio
        # -y: overwrite output file without asking
        ffmpeg_command = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit little-endian
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            temp_audio_path
        ]
        
        # Execute FFmpeg command
        result = subprocess.run(
            ffmpeg_command,
            capture_output=True,
            text=True,
            check=False
        )
        
        # Check if FFmpeg succeeded
        if result.returncode != 0:
            # Clean up the temp file on failure
            cleanup_temp_files(temp_audio_path)
            raise RuntimeError(
                f"Audio extraction failed: FFmpeg returned error code {result.returncode}. "
                f"Error: {result.stderr}"
            )
        
        # Verify the output file was created and has content
        if not os.path.exists(temp_audio_path) or os.path.getsize(temp_audio_path) == 0:
            cleanup_temp_files(temp_audio_path)
            raise RuntimeError(
                "Audio extraction failed: Output file was not created or is empty"
            )
        
        return temp_audio_path
        
    except (subprocess.SubprocessError, OSError) as e:
        # Clean up on any error
        cleanup_temp_files(temp_audio_path)
        raise RuntimeError(f"Audio extraction failed: {str(e)}")
