#!/usr/bin/env python3
"""Test script for transcribing videoplayback.mp4"""

import os
from video_summarization_tool import transcribe_video


def main():
    print("=" * 60)
    print("Video Transcription Test")
    print("=" * 60)
    
    video_path = "videoplayback.mp4"
    
    if not os.path.exists(video_path):
        print(f"ERROR: Video file not found: {video_path}")
        return
    
    file_size = os.path.getsize(video_path) / (1024 * 1024)
    print(f"Video file: {video_path} ({file_size:.2f} MB)")
    print("Transcribing... (this may take a moment)\n")
    
    try:
        result = transcribe_video(video_path)
        
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        
        metadata = result['metadata']
        print(f"Duration: {metadata['duration']:.2f} seconds")
        print(f"Language: {metadata['language']}")
        print(f"Model: {metadata['model']}")
        print(f"Confidence: {metadata['confidence']:.2%}")
        print(f"Total words: {len(result['words'])}")
        print(f"Total utterances: {len(result['utterances'])}")
        
        print("\n" + "=" * 60)
        print("FIRST 5 UTTERANCES")
        print("=" * 60)
        for i, utterance in enumerate(result['utterances'][:5]):
            print(f"\n[{utterance['start']:.2f}s - {utterance['end']:.2f}s]")
            print(f"{utterance['text']}")
        
        print("\n" + "=" * 60)
        print("✓ Transcription completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
