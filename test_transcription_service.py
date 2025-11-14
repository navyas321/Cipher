#!/usr/bin/env python3
"""
Test script for TranscriptionService
"""

import os
from video_summarization_tool.transcription_service import TranscriptionService

# Set API key for tests
os.environ['DEEPGRAM_API_KEY'] = 'd36a45d3c8b0eb25dd95985f452e737df70485c3'

def test_initialization():
    """Test TranscriptionService initialization"""
    print("=" * 60)
    print("Testing TranscriptionService Initialization")
    print("=" * 60)
    
    # Test 1: Check if API key is set
    api_key = os.getenv('DEEPGRAM_API_KEY')
    if api_key:
        print('✓ DEEPGRAM_API_KEY environment variable is set')
        print(f'  API key length: {len(api_key)} characters')
    else:
        print('✗ DEEPGRAM_API_KEY not found')
        return False
    
    # Test 2: Initialize the service
    try:
        service = TranscriptionService()
        print('✓ TranscriptionService initialized successfully')
        print(f'✓ DeepgramClient created: {type(service.client).__name__}')
        return True
    except Exception as e:
        print(f'✗ Failed to initialize: {e}')
        return False

def test_error_handling():
    """Test error handling when API key is missing"""
    print("\n" + "=" * 60)
    print("Testing Error Handling (Missing API Key)")
    print("=" * 60)
    
    # Temporarily remove API key
    original_key = os.getenv('DEEPGRAM_API_KEY')
    if 'DEEPGRAM_API_KEY' in os.environ:
        del os.environ['DEEPGRAM_API_KEY']
    
    try:
        service = TranscriptionService()
        print('✗ Should have raised EnvironmentError')
        success = False
    except EnvironmentError as e:
        print(f'✓ Correctly raised EnvironmentError: {e}')
        success = True
    except Exception as e:
        print(f'✗ Raised wrong exception type: {type(e).__name__}: {e}')
        success = False
    finally:
        # Restore API key
        if original_key:
            os.environ['DEEPGRAM_API_KEY'] = original_key
    
    return success

def test_transcribe_audio_method():
    """Test that transcribe_audio method exists and has correct signature"""
    print("\n" + "=" * 60)
    print("Testing transcribe_audio Method")
    print("=" * 60)
    
    try:
        service = TranscriptionService()
        
        # Check method exists
        if hasattr(service, 'transcribe_audio'):
            print('✓ transcribe_audio method exists')
        else:
            print('✗ transcribe_audio method not found')
            return False
        
        # Check method signature
        import inspect
        sig = inspect.signature(service.transcribe_audio)
        params = list(sig.parameters.keys())
        
        if 'audio_path' in params:
            print('✓ transcribe_audio accepts audio_path parameter')
        else:
            print(f'✗ Expected audio_path parameter, found: {params}')
            return False
        
        print('✓ Method signature is correct')
        return True
        
    except Exception as e:
        print(f'✗ Error testing method: {e}')
        return False

if __name__ == '__main__':
    print("\n🧪 TranscriptionService Test Suite\n")
    
    results = []
    
    # Run tests
    results.append(("Initialization", test_initialization()))
    results.append(("Error Handling", test_error_handling()))
    results.append(("Method Signature", test_transcribe_audio_method()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
