import sys
import os
import io
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from local_video_processor import load_dotenv, handle_online_video_url, transcribe_media

def main():
    log_file = "transcribe_test_log.txt"
    print(f"Running transcription diagnostic test. Results will be saved to {log_file}...")
    
    with open(log_file, "w", encoding="utf-8") as f:
        def log_to_file(msg):
            print(msg)
            f.write(msg + "\n")
            f.flush()
            
        log_to_file("=== TRANSCRIPTION DIAGNOSTIC RUN ===")
        log_to_file(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load environment keys
        import config
        openrouter_key = config.OPENROUTER_API_KEY
        gemini_key = config.GEMINI_API_KEY
        groq_key = config.GROQ_API_KEY
        
        log_to_file(f"GEMINI_API_KEY exists: {bool(gemini_key)}")
        log_to_file(f"OPENROUTER_API_KEY exists: {bool(openrouter_key)}")
        log_to_file(f"GROQ_API_KEY exists: {bool(groq_key)}")
        
        test_url = "https://youtube.com/shorts/-_-_2_H2YSA?si=XPsaaceACIUWSTtG"
        log_to_file(f"Testing URL download...")
        
        try:
            buffer = handle_online_video_url(test_url, log_func=log_to_file)
            if not buffer:
                log_to_file("🔴 FAILED: Download returned None.")
                return
                
            buffer.seek(0, 2)
            size = buffer.tell()
            buffer.seek(0)
            log_to_file(f"Audio buffer verified. Size: {size / (1024 * 1024):.2f} MB")
            log_to_file(f"MIME type: {getattr(buffer, 'mime_type', 'N/A')}")
            log_to_file(f"Display name: {getattr(buffer, 'display_name', 'N/A')}")
            
        except Exception as e:
            log_to_file(f"🔴 DOWNLOAD EXCEPTION: {e}")
            return
            
        # Test Transcription
        log_to_file("\nTesting transcription...")
        try:
            transcription = transcribe_media(buffer, openrouter_key, gemini_key, groq_key, log_func=log_to_file)
            log_to_file(f"\n🟢 SUCCESS! Transcription returned. Length: {len(transcription)} chars")
            log_to_file(f"Transcription preview: {transcription[:200]}")
        except Exception as e:
            log_to_file(f"🔴 TRANSCRIPTION EXCEPTION: {e}")
            import traceback
            log_to_file(traceback.format_exc())

if __name__ == "__main__":
    main()
