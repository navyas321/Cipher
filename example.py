#!/usr/bin/env python3
"""
Example usage script for the Video Summarization Tool.

This script demonstrates how to use the video summarization tool to:
1. Set up environment variables
2. Transcribe a video file
3. Access word-level timestamps
4. Access utterance-level timestamps
5. Find time ranges by keywords
"""

import os
from video_summarization_tool import transcribe_video
from video_summarization_tool.output_formatter import find_time_ranges_by_keywords


def main():
    """Main example function demonstrating tool usage."""
    
    # ========================================
    # 1. API Key Configuration
    # ========================================
    # API key is hardcoded in the TranscriptionService
    
    # ========================================
    # 2. Basic Transcription Call
    # ========================================
    print("=" * 60)
    print("Video Summarization Tool - Example Usage")
    print("=" * 60)
    
    # Specify the path to your video file
    # Supported formats: MP4, AVI, MOV, MKV
    video_path = "path/to/your/video.mp4"
    
    # Check if example video exists
    if not os.path.exists(video_path):
        print(f"\nNOTE: Example video not found at: {video_path}")
        print("Please update the video_path variable with a valid video file path.")
        print("\nFor demonstration purposes, here's what the output would look like:")
        print_example_output()
        return
    
    try:
        print(f"\nTranscribing video: {video_path}")
        print("This may take a moment...\n")
        
        # Call the main transcription function
        result = transcribe_video(video_path)
        
        # ========================================
        # 3. Access Full Transcript
        # ========================================
        print("\n" + "=" * 60)
        print("FULL TRANSCRIPT")
        print("=" * 60)
        print(result['transcript'])
        
        # ========================================
        # 4. Access Metadata
        # ========================================
        print("\n" + "=" * 60)
        print("METADATA")
        print("=" * 60)
        metadata = result['metadata']
        print(f"Duration: {metadata['duration']} seconds")
        print(f"Language: {metadata['language']}")
        print(f"Model: {metadata['model']}")
        print(f"Confidence: {metadata['confidence']:.2%}")
        
        # ========================================
        # 5. Access Word-Level Timestamps
        # ========================================
        print("\n" + "=" * 60)
        print("WORD-LEVEL TIMESTAMPS (First 10 words)")
        print("=" * 60)
        words = result['words']
        for i, word in enumerate(words[:10]):
            print(f"{word['text']:15} | "
                  f"Start: {word['start']:7.3f}s | "
                  f"End: {word['end']:7.3f}s | "
                  f"Confidence: {word['confidence']:.2%}")
        
        if len(words) > 10:
            print(f"... and {len(words) - 10} more words")
        
        # ========================================
        # 6. Access Utterance-Level Timestamps
        # ========================================
        print("\n" + "=" * 60)
        print("UTTERANCE-LEVEL TIMESTAMPS")
        print("=" * 60)
        utterances = result['utterances']
        for i, utterance in enumerate(utterances[:5]):
            print(f"\nUtterance {i + 1}:")
            print(f"  Time: {utterance['start']:.3f}s - {utterance['end']:.3f}s")
            print(f"  Text: {utterance['text']}")
            print(f"  Confidence: {utterance['confidence']:.2%}")
            print(f"  Words: {len(utterance['words'])} words")
        
        if len(utterances) > 5:
            print(f"\n... and {len(utterances) - 5} more utterances")
        
        # ========================================
        # 7. Find Time Ranges by Keywords
        # ========================================
        print("\n" + "=" * 60)
        print("KEYWORD-BASED TIME RANGE FINDER")
        print("=" * 60)
        
        # Define keywords to search for
        keywords = ["important", "summary", "conclusion", "key", "main"]
        print(f"Searching for keywords: {', '.join(keywords)}\n")
        
        # Find time ranges containing these keywords
        time_ranges = find_time_ranges_by_keywords(words, keywords)
        
        if time_ranges:
            print(f"Found {len(time_ranges)} matches:\n")
            for i, time_range in enumerate(time_ranges[:5]):
                print(f"Match {i + 1}:")
                print(f"  Time: {time_range['start']:.3f}s - {time_range['end']:.3f}s")
                print(f"  Keywords found: {', '.join(time_range['keywords'])}")
                print(f"  Context: {time_range['matched_text']}")
                print()
            
            if len(time_ranges) > 5:
                print(f"... and {len(time_ranges) - 5} more matches")
        else:
            print("No matches found for the specified keywords.")
        
        # ========================================
        # 8. Use Case: Extract Video Segments
        # ========================================
        print("\n" + "=" * 60)
        print("USE CASE: Extract Video Segments")
        print("=" * 60)
        print("\nYou can use the time ranges to extract specific video segments.")
        print("For example, with FFmpeg:\n")
        
        if time_ranges:
            first_range = time_ranges[0]
            print(f"ffmpeg -i {video_path} \\")
            print(f"  -ss {first_range['start']} \\")
            print(f"  -to {first_range['end']} \\")
            print(f"  -c copy output_segment.mp4")
        
        print("\n" + "=" * 60)
        print("Example completed successfully!")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("Please check that the video file exists at the specified path.")
    
    except ValueError as e:
        print(f"\nERROR: {e}")
        print("Please use a supported video format: MP4, AVI, MOV, or MKV.")
    
    except EnvironmentError as e:
        print(f"\nERROR: {e}")
    
    except Exception as e:
        print(f"\nERROR: An unexpected error occurred: {e}")
        print("Please check your video file and API key configuration.")


def print_example_output():
    """Print example output structure for demonstration."""
    print("\n" + "=" * 60)
    print("EXAMPLE OUTPUT STRUCTURE")
    print("=" * 60)
    print("""
result = {
    'transcript': 'Full text transcript of the video audio...',
    
    'words': [
        {
            'text': 'Hello',
            'start': 0.123,
            'end': 0.456,
            'confidence': 0.98
        },
        {
            'text': 'world',
            'start': 0.456,
            'end': 0.789,
            'confidence': 0.95
        },
        # ... more words
    ],
    
    'utterances': [
        {
            'text': 'Hello world, this is an example.',
            'start': 0.123,
            'end': 2.456,
            'confidence': 0.96,
            'words': [...]  # Words in this utterance
        },
        # ... more utterances
    ],
    
    'metadata': {
        'duration': 120.5,
        'language': 'en',
        'model': 'nova-3',
        'confidence': 0.94
    }
}

# Find time ranges by keywords
time_ranges = find_time_ranges_by_keywords(result['words'], ['important', 'key'])
# Returns: [
#     {
#         'start': 45.123,
#         'end': 45.456,
#         'matched_text': 'this is an important point to remember',
#         'keywords': ['important']
#     },
#     # ... more matches
# ]
""")


if __name__ == "__main__":
    main()
