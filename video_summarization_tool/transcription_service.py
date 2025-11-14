"""
Transcription service module for audio-to-text conversion.

This module provides functionality to transcribe audio files using Deepgram's
speech-to-text API with word-level timestamps and utterance segmentation.
"""

import os
from typing import Any, Dict

from deepgram import DeepgramClient
from deepgram.core.api_error import ApiError


class TranscriptionService:
    """
    Service for transcribing audio files using Deepgram API.
    
    This service handles initialization of the Deepgram client, API communication,
    and error handling for transcription operations.
    """
    
    def __init__(self):
        """
        Initialize Deepgram client with API key and extended timeout.
        """
        api_key = "d36a45d3c8b0eb25dd95985f452e737df70485c3"
        # Initialize with extended timeout for large files (5 minutes)
        self.client = DeepgramClient(api_key=api_key, timeout=300.0)
    
    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Deepgram API.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Raw Deepgram API response as a dictionary
            
        Raises:
            ApiError: If Deepgram API returns an error
            ConnectionError: If network issues occur
        """
        try:
            # Read audio file as bytes
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Call Deepgram API with configured parameters
            response = self.client.listen.v1.media.transcribe_file(
                request=audio_data,
                model="nova-3",
                punctuate=True,
                smart_format=True,
                utterances=True
            )
            
            # Convert Pydantic model to dictionary
            # Try model_dump() for Pydantic v2, fall back to dict() for v1
            try:
                response_dict = response.model_dump()
            except AttributeError:
                response_dict = response.dict()
            
            # Return raw response as dictionary
            return response_dict
            
        except ApiError as e:
            # Re-raise with context about the API error
            status = e.status_code if e.status_code else "unknown"
            body = e.body if e.body else "No error details provided"
            raise ApiError(
                status_code=e.status_code,
                headers=e.headers,
                body=f"Deepgram API error (status {status}): {body}"
            )
        
        except (OSError, IOError) as e:
            # Network connectivity or file I/O issues
            raise ConnectionError(
                f"Failed to connect to Deepgram API or read audio file: {str(e)}. "
                "Please check your network connection and try again."
            )
        
        except Exception as e:
            # Catch any other unexpected errors
            raise ConnectionError(
                f"Unexpected error during transcription: {str(e)}. "
                "Please verify your network connection and API key, then try again."
            )
