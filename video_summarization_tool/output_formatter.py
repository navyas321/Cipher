"""
Output formatter module for structuring Deepgram transcription responses.

This module provides functionality to parse and format Deepgram API responses
into structured data with word-level and utterance-level timestamps.
"""

from typing import Any, Dict, List


def extract_words_with_timestamps(deepgram_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract word-level timestamps from Deepgram response.
    
    Args:
        deepgram_response: Raw Deepgram API response
        
    Returns:
        List of word objects containing:
        - text: The word text
        - start: Start time in seconds (float with 3 decimal precision)
        - end: End time in seconds (float with 3 decimal precision)
        - confidence: Confidence score (0.0-1.0)
    """
    words = []
    
    try:
        # Navigate to the words array in the response
        channels = deepgram_response.get('results', {}).get('channels', [])
        if not channels:
            return words
        
        alternatives = channels[0].get('alternatives', [])
        if not alternatives:
            return words
        
        raw_words = alternatives[0].get('words', [])
        
        # Extract and format each word
        for word in raw_words:
            words.append({
                'text': word.get('word', ''),
                'start': round(float(word.get('start', 0.0)), 3),
                'end': round(float(word.get('end', 0.0)), 3),
                'confidence': float(word.get('confidence', 0.0))
            })
    
    except (KeyError, IndexError, TypeError, ValueError) as e:
        # Return empty list if response structure is unexpected
        print(f"Warning: Failed to extract words from response: {e}")
        return []
    
    return words


def extract_utterances_with_timestamps(deepgram_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract utterance-level timestamps from Deepgram response.
    
    Utterances are meaningful segments that group words together,
    typically representing complete thoughts or speaker turns.
    
    Args:
        deepgram_response: Raw Deepgram API response
        
    Returns:
        List of utterance objects containing:
        - text: Full utterance text
        - start: Start time in seconds (float with 3 decimal precision)
        - end: End time in seconds (float with 3 decimal precision)
        - confidence: Average confidence score (0.0-1.0)
        - words: List of word objects in this utterance
    """
    utterances = []
    
    try:
        # Navigate to the utterances array in the response
        raw_utterances = deepgram_response.get('results', {}).get('utterances', [])
        
        # Extract and format each utterance
        for utterance in raw_utterances:
            # Extract words for this utterance
            utterance_words = []
            for word in utterance.get('words', []):
                utterance_words.append({
                    'text': word.get('word', ''),
                    'start': round(float(word.get('start', 0.0)), 3),
                    'end': round(float(word.get('end', 0.0)), 3),
                    'confidence': float(word.get('confidence', 0.0))
                })
            
            utterances.append({
                'text': utterance.get('transcript', ''),
                'start': round(float(utterance.get('start', 0.0)), 3),
                'end': round(float(utterance.get('end', 0.0)), 3),
                'confidence': float(utterance.get('confidence', 0.0)),
                'words': utterance_words
            })
    
    except (KeyError, IndexError, TypeError, ValueError) as e:
        # Return empty list if response structure is unexpected
        print(f"Warning: Failed to extract utterances from response: {e}")
        return []
    
    return utterances


def find_time_ranges_by_keywords(
    words: List[Dict[str, Any]], 
    keywords: List[str]
) -> List[Dict[str, Any]]:
    """
    Find time ranges containing specific keywords.
    
    This function searches through the words list to find occurrences of
    specified keywords and returns the time ranges where they appear.
    
    Args:
        words: List of word objects with timestamps
        keywords: List of keywords to search for (case-insensitive)
        
    Returns:
        List of time range objects containing:
        - start: Start time in seconds
        - end: End time in seconds
        - matched_text: Text containing the keyword
        - keywords: List of keywords found in this range
    """
    time_ranges = []
    
    if not words or not keywords:
        return time_ranges
    
    # Normalize keywords to lowercase for case-insensitive matching
    normalized_keywords = [kw.lower() for kw in keywords]
    
    # Search through words for keyword matches
    for i, word in enumerate(words):
        word_text = word.get('text', '').lower()
        
        # Check if this word matches any keyword
        matched_keywords = [kw for kw in normalized_keywords if kw in word_text]
        
        if matched_keywords:
            # Found a match - create a time range
            # Include context: current word and surrounding words
            context_start = max(0, i - 2)
            context_end = min(len(words), i + 3)
            
            context_words = words[context_start:context_end]
            matched_text = ' '.join([w.get('text', '') for w in context_words])
            
            time_ranges.append({
                'start': round(float(word.get('start', 0.0)), 3),
                'end': round(float(word.get('end', 0.0)), 3),
                'matched_text': matched_text,
                'keywords': matched_keywords
            })
    
    return time_ranges


def format_response(deepgram_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format Deepgram response into structured output for Bedrock Agent consumption.
    
    This function extracts all relevant information from the Deepgram API response
    and structures it into a consistent format with transcript, words, utterances,
    and metadata.
    
    Args:
        deepgram_response: Raw Deepgram API response
        
    Returns:
        Formatted dictionary containing:
        - transcript: Full text transcript
        - words: List of word objects with timestamps
        - utterances: List of utterance objects with timestamps
        - metadata: Dictionary with duration, language, model, and confidence
    """
    # Extract full transcript
    transcript = ""
    try:
        channels = deepgram_response.get('results', {}).get('channels', [])
        if channels:
            alternatives = channels[0].get('alternatives', [])
            if alternatives:
                transcript = alternatives[0].get('transcript', '')
    except (KeyError, IndexError, TypeError):
        transcript = ""
    
    # Extract words and utterances using helper functions
    words = extract_words_with_timestamps(deepgram_response)
    utterances = extract_utterances_with_timestamps(deepgram_response)
    
    # Build metadata dictionary
    metadata = {}
    try:
        # Extract duration
        duration = deepgram_response.get('metadata', {}).get('duration', 0.0)
        metadata['duration'] = round(float(duration), 3)
        
        # Extract detected language
        channels = deepgram_response.get('results', {}).get('channels', [])
        if channels:
            alternatives = channels[0].get('alternatives', [])
            if alternatives:
                metadata['language'] = alternatives[0].get('detected_language', 'unknown')
                metadata['confidence'] = float(alternatives[0].get('confidence', 0.0))
        
        # Add model information
        metadata['model'] = deepgram_response.get('metadata', {}).get('model_info', {}).get('name', 'nova-3')
        
    except (KeyError, IndexError, TypeError, ValueError):
        # Set default metadata if extraction fails
        metadata = {
            'duration': 0.0,
            'language': 'unknown',
            'model': 'nova-3',
            'confidence': 0.0
        }
    
    # Return structured dictionary
    return {
        'transcript': transcript,
        'words': words,
        'utterances': utterances,
        'metadata': metadata
    }
